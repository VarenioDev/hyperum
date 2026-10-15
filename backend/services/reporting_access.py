"""Ownership checks shared by teacher reports and graph endpoints."""
from sqlalchemy import text


class ReportNotFound(ValueError):
    pass


def owned_class(session, group_id, teacher_id):
    row = session.execute(text("""
        SELECT id, name FROM groups
        WHERE id=:gid AND owner_id=:teacher
          AND tenant_id=current_setting('app.current_tenant', true)
    """), {'gid': str(group_id), 'teacher': str(teacher_id)}).mappings().first()
    if not row:
        raise ReportNotFound('Класс не найден или недоступен')
    return dict(row)


def owned_student(session, student_id, teacher_id):
    row = session.execute(text("""
        SELECT u.id, u.full_name, u.email, u.status,
               (SELECT MAX(r.created_at) FROM responses r WHERE r.student_id=u.id) AS last_activity
        FROM users u
        WHERE u.id=:sid AND u.role='student'
          AND u.tenant_id=current_setting('app.current_tenant', true)
          AND EXISTS (
              SELECT 1 FROM memberships m JOIN groups g ON g.id=m.group_id
              WHERE m.user_id=u.id AND m.role='student' AND m.status!='rejected'
                AND g.owner_id=:teacher AND g.tenant_id=u.tenant_id
          )
    """), {'sid': str(student_id), 'teacher': str(teacher_id)}).mappings().first()
    if not row:
        raise ReportNotFound('Ученик не найден или недоступен')
    return dict(row)


def owned_assignment(session, assignment_id, teacher_id):
    row = session.execute(text("""
        SELECT a.id, a.title, a.topic, a.status, a.group_id, g.name AS class_name,
               a.created_at, a.sent_at, a.tasks_per_student
        FROM assignments a JOIN groups g ON g.id=a.group_id
        WHERE a.id=:aid AND a.created_by=:teacher AND g.owner_id=:teacher
          AND a.tenant_id=current_setting('app.current_tenant', true)
    """), {'aid': str(assignment_id), 'teacher': str(teacher_id)}).mappings().first()
    if not row:
        raise ReportNotFound('Тест не найден или недоступен')
    return dict(row)
