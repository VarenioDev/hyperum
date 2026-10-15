"""Teacher reports use the latest attempt in its explicit assignment context."""
from sqlalchemy import text
from backend.services.reporting_access import owned_class, owned_student, owned_assignment, ReportNotFound


LATEST = """latest AS (
    SELECT DISTINCT ON (assignment_id, student_id, task_id) * FROM responses
    WHERE assignment_id IS NOT NULL
    ORDER BY assignment_id, student_id, task_id, created_at DESC, id DESC
)"""


def cell_status(response):
    if response.get('id') is None:
        return 'unanswered'
    if response.get('surrendered'):
        return 'surrendered'
    if response.get('skipped'):
        return 'skipped'
    return 'correct' if response.get('correct') else 'incorrect'


def student_totals(cells):
    done = sum(c['status'] != 'unanswered' for c in cells)
    return dict(task_count=len(cells), answered_count=done,
                correct_count=sum(c['status'] == 'correct' for c in cells),
                state='completed' if cells and done == len(cells) else 'in_progress' if done else 'pending')


def summarize_students(students):
    return dict(students_count=len(students), completed_count=sum(s['state'] == 'completed' for s in students),
                started_count=sum(s['answered_count'] > 0 for s in students),
                task_count=sum(s['task_count'] for s in students),
                answered_count=sum(s['answered_count'] for s in students),
                correct_count=sum(s['correct_count'] for s in students))


def assignment_matrix(session, assignment_id, teacher_id):
    assignment = owned_assignment(session, assignment_id, teacher_id)
    rows = session.execute(text(f"""
        WITH {LATEST}
        SELECT ast.student_id, u.full_name, ast.status AS saved_state,
               at.position, t.id AS task_id, t.code,
               r.id, r.correct, r.skipped, r.surrendered, r.created_at,
               EXISTS (SELECT 1 FROM responses old WHERE old.student_id=ast.student_id
                   AND old.context='legacy' AND old.task_id=t.id
                   AND old.created_at>=COALESCE(a.sent_at,a.created_at)) AS has_legacy
        FROM assignment_students ast JOIN users u ON u.id=ast.student_id
        JOIN assignments a ON a.id=ast.assignment_id
        JOIN assignment_tasks at ON at.assignment_id=ast.assignment_id AND at.student_id=ast.student_id
        JOIN tasks t ON t.id=at.task_id
        LEFT JOIN latest r ON r.assignment_id=at.assignment_id
          AND r.student_id=at.student_id AND r.task_id=at.task_id
        WHERE ast.assignment_id=:aid
        ORDER BY u.full_name, ast.student_id, at.position
    """), {'aid': str(assignment_id)}).mappings().all()
    students = {}
    for row in rows:
        sid = str(row['student_id'])
        student = students.setdefault(sid, dict(student_id=sid, full_name=row['full_name'],
                        saved_state=row['saved_state'], has_legacy=False, cells=[]))
        student['has_legacy'] |= row['has_legacy']
        student['cells'].append(dict(position=row['position'], task_id=str(row['task_id']),
                    code=row['code'], status=cell_status(row), answered_at=row['created_at']))
    result = list(students.values())
    for student in result:
        student.update(student_totals(student['cells']))
    signatures = {tuple(c['task_id'] for c in s['cells']) for s in result}
    return dict(assignment=assignment, students=result, summary=summarize_students(result),
                common_tasks=len(signatures) == 1, has_legacy=any(s['has_legacy'] for s in result))


def assignment_summaries(session, teacher_id, *, group_id=None, student_id=None):
    """One query for all assignments; one row per recipient, no task text payload."""
    rows = session.execute(text(f"""
        WITH {LATEST}
        SELECT a.id, a.title, a.topic, a.status, a.group_id, g.name AS class_name,
               a.created_at, a.sent_at, ast.student_id, ast.status AS saved_state,
               COUNT(at.task_id) AS task_count, COUNT(r.id) AS answered_count,
               COUNT(r.id) FILTER (WHERE r.correct IS TRUE AND NOT COALESCE(r.skipped,FALSE)
                 AND NOT COALESCE(r.surrendered,FALSE)) AS correct_count,
               EXISTS (SELECT 1 FROM responses old JOIN assignment_tasks oat
                   ON oat.task_id=old.task_id AND oat.student_id=old.student_id
                   WHERE oat.assignment_id=a.id AND old.student_id=ast.student_id
                     AND old.context='legacy'
                     AND old.created_at>=COALESCE(a.sent_at,a.created_at)) AS has_legacy
        FROM assignments a JOIN groups g ON g.id=a.group_id
        JOIN assignment_students ast ON ast.assignment_id=a.id
        LEFT JOIN assignment_tasks at ON at.assignment_id=a.id AND at.student_id=ast.student_id
        LEFT JOIN latest r ON r.assignment_id=at.assignment_id AND r.student_id=at.student_id AND r.task_id=at.task_id
        WHERE a.created_by=:teacher AND g.owner_id=:teacher
          AND a.tenant_id=current_setting('app.current_tenant', true)
          AND (CAST(:gid AS uuid) IS NULL OR a.group_id=CAST(:gid AS uuid))
          AND (CAST(:sid AS uuid) IS NULL OR ast.student_id=CAST(:sid AS uuid))
        GROUP BY a.id, g.name, ast.student_id, ast.status
        ORDER BY COALESCE(a.sent_at,a.created_at) DESC, a.id, ast.student_id
    """), {'teacher': str(teacher_id), 'gid': str(group_id) if group_id else None,
            'sid': str(student_id) if student_id else None}).mappings().all()
    assignments = {}
    for r in rows:
        aid = str(r['id'])
        entry = assignments.setdefault(aid, {k: r[k] for k in
                   ['id', 'title', 'topic', 'status', 'group_id', 'class_name', 'created_at', 'sent_at']})
        recipients = entry.setdefault('students', [])
        n, done = r['task_count'], r['answered_count']
        recipients.append(dict(student_id=str(r['student_id']), task_count=n, answered_count=done,
                    correct_count=r['correct_count'], saved_state=r['saved_state'], has_legacy=r['has_legacy'],
                    state='completed' if n and done == n else 'in_progress' if done else 'pending'))
    for entry in assignments.values():
        entry['summary'] = summarize_students(entry['students'])
        entry['has_legacy'] = any(s['has_legacy'] for s in entry['students'])
    return list(assignments.values())


def class_activity(session, group_id, teacher_id):
    owned_class(session, group_id, teacher_id)
    return assignment_summaries(session, teacher_id, group_id=group_id)


def attempt_history(session, teacher_id, student_id, *, assignment_id=None, skill_id=None, limit=20, offset=0):
    params = dict(teacher=str(teacher_id), sid=str(student_id),
                  aid=str(assignment_id) if assignment_id else None, skill=skill_id, lim=limit+1, off=offset)
    rows = session.execute(text("""
        SELECT r.id, r.task_id, r.assignment_id, r.context, r.answer, r.correct,
               r.skipped, r.surrendered, r.time_sec, r.created_at,
               t.code, t.text AS task_text, t.answer AS expected, t.options,
               a.title AS assignment_title
        FROM responses r JOIN tasks t ON t.id=r.task_id
        LEFT JOIN assignments a ON a.id=r.assignment_id
        WHERE r.student_id=:sid
          AND (r.assignment_id IS NULL OR a.created_by=:teacher)
          AND (CAST(:aid AS uuid) IS NULL OR r.assignment_id=CAST(:aid AS uuid))
          AND (CAST(:skill AS text) IS NULL OR EXISTS (SELECT 1 FROM task_labels tl
                WHERE tl.task_id=r.task_id AND tl.model='deepseek' AND tl.skill_id=CAST(:skill AS text)))
        ORDER BY r.created_at DESC, r.id DESC LIMIT :lim OFFSET :off
    """), params).mappings().all()
    return dict(items=[dict(r) for r in rows[:limit]], has_more=len(rows)>limit)


def task_attempts(session, assignment_id, student_id, task_id, teacher_id, limit=20, offset=0):
    owned_assignment(session, assignment_id, teacher_id)
    row = session.execute(text("""
        SELECT t.id AS task_id, t.code, t.text, t.options, t.answer AS expected, at.position,
               sk.name AS skill_name
        FROM assignment_tasks at JOIN tasks t ON t.id=at.task_id
        LEFT JOIN task_labels tl ON tl.task_id=t.id AND tl.model='deepseek' AND tl.is_primary
        LEFT JOIN skills sk ON sk.id=tl.skill_id
        WHERE at.assignment_id=:aid AND at.student_id=:sid AND at.task_id=:tid
    """), {'aid': str(assignment_id), 'sid': str(student_id), 'tid': str(task_id)}).mappings().first()
    if not row:
        raise ReportNotFound('Задание не найдено в тесте этого ученика')
    rows = session.execute(text("""
        SELECT id, answer, correct, skipped, surrendered, time_sec, created_at
        FROM responses WHERE assignment_id=:aid AND student_id=:sid AND task_id=:tid
        ORDER BY created_at DESC, id DESC LIMIT :lim OFFSET :off
    """), {'aid': str(assignment_id), 'sid': str(student_id), 'tid': str(task_id),
            'lim': limit+1, 'off': offset}).mappings().all()
    return dict(task=dict(row), attempts=[dict(r) for r in rows[:limit]], has_more=len(rows)>limit)


def student_profile(session, student_id, teacher_id):
    student = owned_student(session, student_id, teacher_id)
    groups = session.execute(text("""
        SELECT g.id, g.name, m.status FROM groups g JOIN memberships m ON m.group_id=g.id
        WHERE m.user_id=:sid AND m.role='student' AND m.status!='rejected' AND g.owner_id=:teacher
        ORDER BY g.name
    """), {'sid': str(student_id), 'teacher': str(teacher_id)}).mappings().all()
    skills = session.execute(text("""
        SELECT sm.skill_id, sk.name, sk.topic, sm.mastery, sm.attempts, sm.correct
        FROM student_mastery sm JOIN skills sk ON sk.id=sm.skill_id
        WHERE sm.student_id=:sid AND sm.attempts>0 ORDER BY sm.mastery, sk.name
    """), {'sid': str(student_id)}).mappings().all()
    summary = dict(total_skills=len(skills), mastered=sum(r['mastery']>=0.8 for r in skills),
                   learning=sum(0.5<=r['mastery']<0.8 for r in skills), weak=sum(r['mastery']<0.5 for r in skills))
    return dict(student=student, groups=[dict(g) for g in groups], summary=summary,
                weak_skills=[dict(r) for r in skills if r['mastery']<0.5][:5],
                assignments=assignment_summaries(session, teacher_id, student_id=student_id))
