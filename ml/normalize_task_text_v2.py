"""Normalize a CSV through DeepSeek; never connects to or writes a database.

python -m ml.normalize_task_text_v2 tasks/16taskege.csv --sample
python -m ml.normalize_task_text_v2 tasks/16taskege.csv --workers 4
python -m ml.normalize_task_text_v2 tasks/16taskege.csv --offline
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, ValidationError
import requests

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "ml/prompts/normalize_task_text.txt"
SAMPLE_CODES = ["task_753", "task_754", "task_770", "task_783", "task_813",
                "task_821", "task_831", "task_837", "task_936", "task_953"]


class NormalizedTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: StrictStr
    normalized_text: StrictStr = Field(min_length=1)
    needs_review: StrictBool
    warnings: list[StrictStr]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if not {"code", "text", "answer", "type"}.issubset(fields):
            raise ValueError("CSV must contain code, text, answer, type")
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("Malformed CSV row")
    codes = [row["code"] for row in rows]
    if len(set(codes)) != len(codes) or any(not code.strip() for code in codes):
        raise ValueError("Empty or duplicate task code")
    return fields, rows


def number_values(value: str) -> set[str]:
    # Ignore multiplicity: the input repeats formulas. Grouped numbers also
    # occur as '42 038' and '1 0 12'; these remain warnings, not proof of damage.
    return {str(int(n)) for n in re.findall(r"\d+", value)}


def check_content(original: str, normalized: str) -> list[str]:
    warnings = []
    before, after = number_values(original), number_values(normalized)
    if after - before:
        warnings.append("New numeric tokens: " + ", ".join(sorted(after - before)))
    if before - after:
        warnings.append("Missing numeric tokens (may be duplicated/grouped source): "
                        + ", ".join(sorted(before - after)))
    if len(normalized) < len(original) * 0.15:
        warnings.append("Output is unusually short")
    if re.search(r"[\ue000-\uf8ff\u200b\ufffd]", normalized):
        warnings.append("Invisible/private-use/replacement characters remain")
    if "```" in normalized:
        warnings.append("Unexpected code fence; inspect before importing")
    if re.search(r"<\s*(?:script|iframe|img|div|span)\b", normalized, re.I):
        warnings.append("Unexpected HTML")
    if re.search(r"(?im)^\s*(?:ответ|решение|подсказка)\s*:", normalized) and not re.search(
            r"(?im)(?:ответ|решение|подсказка)\s*:", original):
        warnings.append("Model added an answer/solution/hint section")
    before_functions = set(re.findall(r"\b([A-Z])\s*\(", original))
    after_functions = set(re.findall(r"\b([A-Z])\s*\(", normalized))
    if before_functions != after_functions:
        warnings.append("Function names changed")
    return warnings


def canonicalize_math(text: str) -> str:
    """Only normalize Unicode minus signs inside explicit math; idempotent."""
    return re.sub(r"\$\$[\s\S]*?\$\$|(?<!\$)\$[^$\n]+\$(?!\$)",
                  lambda match: match.group().replace("−", "-").replace("–", "-"), text)


def cache_key(row: dict[str, str], prompt: str, model: str) -> str:
    model_row = {key: row.get(key, "") for key in ("code", "text", "answer", "type")}
    value = json.dumps({"row": model_row, "prompt": prompt, "model": model},
                       ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(value.encode()).hexdigest()


def call_deepseek(row: dict[str, str], prompt: str, model: str, key: str) -> dict:
    # Do not send the expected answer: the model edits the statement, not solves it.
    feedback = ""
    for attempt in range(3):
        try:
            response = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "temperature": 0,
                      "response_format": {"type": "json_object"},
                      "max_tokens": 4096,
                      "messages": [{"role": "system", "content": prompt},
                                   {"role": "user", "content": json.dumps(
                                       {"code": row["code"], "text": row["text"]},
                                       ensure_ascii=False) + feedback}]},
                timeout=(15, 180),
            )
            if response.status_code in (401, 403, 400, 402):
                raise ValueError(f"DeepSeek HTTP {response.status_code}; check credentials/model/balance")
            response.raise_for_status()
            body = response.json()
            choice = body["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ValueError("Incomplete DeepSeek response")
            parsed = NormalizedTask.model_validate_json(choice["message"]["content"])
            if parsed.code != row["code"]:
                raise ValueError("DeepSeek returned a different task code")
            return {"candidate": parsed.model_dump(), "usage": body.get("usage", {})}
        except (requests.RequestException, KeyError, json.JSONDecodeError, ValidationError) as exc:
            if attempt == 2:
                # Do not print HTTP response bodies or credentials.
                raise RuntimeError(f"DeepSeek request failed: {type(exc).__name__}") from None
            if isinstance(exc, ValidationError):
                feedback = ('\nPrevious response was invalid. Return ALL four JSON fields: '
                            'code, normalized_text, needs_review (boolean), warnings (array of strings). '
                            'Do not omit needs_review or warnings even if there are no concerns.')
            time.sleep(2 ** attempt)
    raise RuntimeError("DeepSeek request failed")


def process(row: dict[str, str], prompt: str, args, key: str, cache: Path) -> dict:
    fingerprint = cache_key(row, prompt, args.model)
    cached_file = cache / f"{fingerprint}.json"
    record = {"code": row["code"], "original_text": row["text"],
              "source_hash": fingerprint, "model": args.model}
    try:
        if cached_file.exists():
            result = json.loads(cached_file.read_text(encoding="utf-8"))
            parsed = NormalizedTask.model_validate(result["candidate"])
            if parsed.code != row["code"]:
                raise ValueError("Cache code mismatch")
        elif args.offline:
            raise ValueError("No cached response (offline mode)")
        else:
            result = call_deepseek(row, prompt, args.model, key)
            temp = cached_file.with_suffix(".tmp")
            temp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(cached_file)
            parsed = NormalizedTask.model_validate(result["candidate"])
        record.update(result["candidate"])
        record["normalized_text"] = canonicalize_math(parsed.normalized_text)
        record["usage"] = result.get("usage", {})
        record["checks"] = check_content(row["text"], record["normalized_text"])
    except Exception as exc:
        record.update(normalized_text=row["text"], needs_review=True,
                      warnings=[], checks=[], error=str(exc))
    return record


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def export_csvs(output: Path, fields: list[str], rows: list[dict[str, str]], records: list[dict]) -> None:
    by_code = {record["code"]: record for record in records}
    candidates, checked = [], []
    for row in rows:
        record = by_code[row["code"]]
        candidate = {**row, "text": record["normalized_text"]}
        candidates.append(candidate)
        safe = not (record.get("error") or record["needs_review"] or record["warnings"]
                    or record["checks"] or record.get("render_errors"))
        record["status"] = "checks_passed" if safe else "needs_review"
        checked.append(candidate if safe else dict(row))
    write_csv(output / "candidates.csv", fields, candidates)
    # Unreviewed candidates never silently enter the checked export.
    write_csv(output / "checked.csv", fields, checked)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--codes", nargs="+")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=2, choices=range(1, 9))
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--offline", action="store_true", help="Use cached results only; no API calls")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if not args.offline and not key:
        parser.error("DEEPSEEK_API_KEY is not configured")
    source = args.csv.resolve()
    fields, rows = read_csv(source)
    codes = set(args.codes or (SAMPLE_CODES if args.sample else []))
    if codes:
        missing = codes - {row["code"] for row in rows}
        if missing:
            parser.error(f"Unknown codes: {sorted(missing)}")
        rows = [row for row in rows if row["code"] in codes]
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be positive")
        rows = rows[:args.limit]
    output = (args.output_dir or ROOT / "data/task_normalization" /
              (source.stem + ("-sample" if args.sample else ""))).resolve()
    if source.parent == output:
        parser.error("Output must use a separate directory from the source CSV")
    output.mkdir(parents=True, exist_ok=True)
    cache = ROOT / "data/task_normalization/cache"
    cache.mkdir(parents=True, exist_ok=True)
    prompt = PROMPT.read_text(encoding="utf-8")
    write_csv(output / "original.csv", fields, rows)
    records = {}
    report = output / "report.json"
    metadata = {"source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "model": args.model,
                "semantic_verification": "Required: syntactic checks do not prove equivalence"}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(process, row, prompt, args, key, cache) for row in rows]
        for future in as_completed(futures):
            record = future.result()
            records[record["code"]] = record
            ordered = [records[row["code"]] for row in rows if row["code"] in records]
            report.write_text(json.dumps({**metadata, "tasks": ordered}, ensure_ascii=False, indent=2),
                              encoding="utf-8")
            print(f"[{len(records)}/{len(rows)}] {record['code']}: "
                  f"{'ERROR ' + record['error'] if record.get('error') else 'received'}", flush=True)
    ordered = [records[row["code"]] for row in rows]
    subprocess.run(["node", str(ROOT / "pwa/scripts/preview-normalized-tasks.mjs"), str(report)],
                   check=True, cwd=ROOT)
    ordered = json.loads(report.read_text(encoding="utf-8"))["tasks"]
    export_csvs(output, fields, rows, ordered)
    report.write_text(json.dumps({**metadata, "tasks": ordered}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Checks passed: {sum(r['status'] == 'checks_passed' for r in ordered)}/{len(ordered)}", flush=True)
    print(f"Artifacts: {output}", flush=True)
    if any(record.get("error") for record in ordered):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
