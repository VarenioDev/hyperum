"""Build an import CSV only after syntax and semantic reviews, with an audit log."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from ml.normalize_task_text_v2 import read_csv, write_csv
from ml.verify_task_texts import PROMPT

ROOT = Path(__file__).resolve().parents[1]


def review_hash(task):
    data = {field: task[field] for field in ('code', 'original_text', 'normalized_text')}
    return hashlib.sha256((PROMPT + json.dumps(data, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()


def finalize(report_path, reviews_path, approvals_path):
    report = json.loads(report_path.read_text(encoding='utf-8'))
    reviews = {r['code']: r for r in json.loads(reviews_path.read_text(encoding='utf-8'))}
    approvals = json.loads(approvals_path.read_text(encoding='utf-8')) if approvals_path else {}
    fields, originals = read_csv(report_path.with_name('original.csv'))
    tasks = {r['code']: r for r in report['tasks']}
    if {r['code'] for r in originals} != tasks.keys():
        raise ValueError('Original snapshot and report have different codes')
    for code, approval in approvals.items():
        task = tasks[code]
        expected = hashlib.sha256(task['original_text'].encode()).hexdigest()
        if approval['original_sha256'] != expected or not approval['note'].strip():
            raise ValueError('Invalid manual approval: ' + code)
        if approval.get('normalized_text') is not None:
            task['normalized_text'] = approval['normalized_text']
        candidate_hash = hashlib.sha256(task['normalized_text'].encode()).hexdigest()
        if approval['candidate_sha256'] != candidate_hash:
            raise ValueError('Manual approval does not match candidate: ' + code)
        task['manual_review'] = approval['note']
    final_report = report_path.with_name('verified-report.json')
    final_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    subprocess.run(['node', str(ROOT / 'pwa/scripts/preview-normalized-tasks.mjs'), str(final_report)], check=True)
    report = json.loads(final_report.read_text(encoding='utf-8'))
    output = []
    unresolved = []
    originals_by_code = {row['code']: row for row in originals}
    for task in report['tasks']:
        code = task['code']
        manual = bool(task.get('manual_review'))
        review = reviews.get(code, {})
        semantic_ok = (review.get('hash') == review_hash(task) and review.get('equivalent')
                       and not review.get('issues'))
        content_ok = not (task.get('checks') or task.get('warnings') or task.get('needs_review'))
        safe = not (task.get('error') or task['render_errors']) and (
            manual or (semantic_ok and content_ok))
        if not safe:
            unresolved.append(code)
        task['release_status'] = 'verified' if safe else 'unresolved'
        task['semantic_review'] = review
        output.append({**originals_by_code[code], 'text': task['normalized_text']} if safe else originals_by_code[code])
    final_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if unresolved:
        # Do not publish a partial CSV under the final release filename.
        raise ValueError(f'Unresolved tasks: {unresolved}')
    target = report_path.with_name('verified.csv')
    write_csv(target, fields, output)
    print(f'Verified release: {len(output)} tasks, {target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('reviews', type=Path)
    parser.add_argument('--approvals', type=Path)
    args = parser.parse_args()
    finalize(args.report, args.reviews, args.approvals)
