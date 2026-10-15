"""Verify task identity/texts and label coverage after a production release."""
import argparse
import csv
import json

from sqlalchemy import text
from backend.db.postgres import get_session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('verified_csv')
    args = parser.parse_args()
    with open(args.verified_csv, encoding='utf-8-sig', newline='') as stream:
        expected = {row['id']: row for row in csv.DictReader(stream)}
    with get_session() as session:
        rows = session.execute(text("""
            SELECT id::text, code, text, COALESCE(answer, '') AS answer,
                   COALESCE(type, '') AS type FROM tasks
            WHERE id = ANY(CAST(:ids AS uuid[]))
        """), {'ids': list(expected)}).mappings()
        actual = {row['id']: dict(row) for row in rows}
        if actual != expected:
            raise ValueError('Production task data differs from the verified CSV')
        missing_labels = session.execute(text("""
            SELECT COUNT(*) FROM tasks t WHERE NOT EXISTS
            (SELECT 1 FROM task_labels l WHERE l.task_id=t.id AND l.model='deepseek' AND l.is_primary)
        """)).scalar()
        totals = session.execute(text("SELECT COUNT(*) FROM tasks")).scalar()
        labels = session.execute(text("SELECT COUNT(*) FROM task_labels")).scalar()
    print(json.dumps({'verified_tasks': len(actual), 'total_tasks': totals,
                      'labels': labels, 'missing_deepseek_primary': missing_labels}))
    if missing_labels:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
