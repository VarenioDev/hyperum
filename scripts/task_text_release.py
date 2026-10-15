"""Export/update existing task texts; preserve IDs, answers, labels and assignments.

Run inside the backend container. Apply requires an exact original snapshot.
"""
import argparse
import csv
import json
from pathlib import Path

from sqlalchemy import text
from backend.db.postgres import get_session

FIELDS = ["id", "code", "text", "answer", "type"]
SELECT = "SELECT id::text, code, text, COALESCE(answer, '') AS answer, COALESCE(type, '') AS type FROM tasks"


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or any(not set(FIELDS).issubset(row) for row in rows):
        raise ValueError("Snapshot must contain id, code, text, answer, type")
    if len({row['id'] for row in rows}) != len(rows):
        raise ValueError("Duplicate task IDs")
    return rows


def export(path):
    with get_session() as session:
        rows = [dict(row) for row in session.execute(text(SELECT + " WHERE code IS NOT NULL ORDER BY code")).mappings()]
        unlabeled = session.execute(text("SELECT COUNT(*) FROM tasks t WHERE NOT EXISTS (SELECT 1 FROM task_labels l WHERE l.task_id=t.id)")).scalar()
        labels = session.execute(text("SELECT COUNT(*) FROM task_labels")).scalar()
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"exported": len(rows), "unlabeled": unlabeled, "labels": labels}))


def apply(original_path, candidate_path, backup_path):
    originals, candidates = read_rows(original_path), read_rows(candidate_path)
    before = {row['id']: row for row in originals}
    after = {row['id']: row for row in candidates}
    if before.keys() != after.keys():
        raise ValueError("Different task IDs in snapshots")
    for task_id, row in after.items():
        if any(row[key] != before[task_id][key] for key in FIELDS if key != 'text'):
            raise ValueError(f"Immutable task fields changed: {row['code']}")
        if not row['text'].strip():
            raise ValueError(f"Empty candidate text: {row['code']}")
    backup = Path(backup_path)
    if backup.exists():
        raise ValueError("Backup file already exists; use a new release path")
    with get_session() as session:
        current = [dict(row) for row in session.execute(text(SELECT + " WHERE id = ANY(CAST(:ids AS uuid[])) ORDER BY id FOR UPDATE"),
                          {"ids": list(before)}).mappings()]
        if {row['id']: row for row in current} != before:
            raise ValueError("Database changed since export; no updates applied")
        backup.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        changed = 0
        for task_id, row in after.items():
            if row['text'] == before[task_id]['text']:
                continue
            session.execute(text("UPDATE tasks SET text=:text WHERE id=CAST(:id AS uuid)"), row)
            changed += 1
    print(json.dumps({"updated": changed, "total": len(before), "backup": str(backup)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    exp = actions.add_parser("export")
    exp.add_argument("path")
    upd = actions.add_parser("apply")
    upd.add_argument("original")
    upd.add_argument("candidate")
    upd.add_argument("backup")
    args = parser.parse_args()
    if args.action == "export":
        export(args.path)
    else:
        apply(args.original, args.candidate, args.backup)


if __name__ == "__main__":
    main()
