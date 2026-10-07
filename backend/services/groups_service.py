"""
Бизнес-логика классов и регистрации учеников.
"""
import random
import uuid
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.auth.security import hash_password


def _generate_invite_code(length: int = 6) -> str:
    """6-символьный код из букв и цифр (без похожих символов)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # без 0/O, 1/I
    return "".join(random.choices(alphabet, k=length))


def create_group(
    session: Session,
    tenant_id: str,
    owner_id: str,
    name: str,
    subject: str,
    kind: str,
) -> dict:
    """Создать класс и вернуть его данные."""
    group_id = str(uuid.uuid4())

    for _ in range(10):
        code = _generate_invite_code()
        exists = session.execute(
            text("SELECT 1 FROM groups WHERE invite_code = :c"),
            {"c": code},
        ).fetchone()
        if not exists:
            break
    else:
        raise RuntimeError("Не удалось сгенерировать уникальный код")

    session.execute(text("""
        INSERT INTO groups
            (id, tenant_id, owner_id, name, kind, subject, invite_code)
        VALUES
            (:id, :t, :owner, :name, :kind, :subject, :code)
    """), {
        "id": group_id, "t": tenant_id, "owner": owner_id,
        "name": name, "kind": kind, "subject": subject, "code": code,
    })

    return {
        "id": group_id, "name": name, "subject": subject,
        "kind": kind, "invite_code": code,
    }


def list_teacher_groups(session: Session, owner_id: str) -> list[dict]:
    """Список классов учителя с агрегатами."""
    rows = session.execute(text("""
        SELECT g.id, g.name, g.subject, g.kind, g.invite_code, g.created_at,
               COUNT(DISTINCT CASE WHEN m.status = 'active'
                     THEN m.user_id END) AS students_count,
               COUNT(DISTINCT CASE WHEN m.status = 'pending'
                     THEN m.user_id END) AS pending_count
        FROM groups g
        LEFT JOIN memberships m ON m.group_id = g.id AND m.role = 'student'
        WHERE g.owner_id = :owner
        GROUP BY g.id
        ORDER BY g.created_at DESC
    """), {"owner": owner_id}).fetchall()

    return [
        {
            "id": r[0], "name": r[1], "subject": r[2], "kind": r[3],
            "invite_code": r[4], "created_at": r[5],
            "students_count": r[6], "pending_count": r[7],
        }
        for r in rows
    ]


def get_group_detail(
    session: Session,
    group_id: UUID | str,
    owner_id: str,
) -> dict | None:
    """Детали класса: ученики, mastery, агрегаты."""
    g = session.execute(text("""
        SELECT id, name, subject, kind, invite_code, created_at
        FROM groups
        WHERE id = :gid AND owner_id = :owner
    """), {"gid": str(group_id), "owner": owner_id}).fetchone()

    if g is None:
        return None

    students = session.execute(text("""
        SELECT u.id, u.full_name, u.email, m.status, m.joined_at,
               ROUND(AVG(sm.mastery)::numeric, 2) AS avg_mastery
        FROM memberships m
        JOIN users u ON u.id = m.user_id
        LEFT JOIN student_mastery sm ON sm.student_id = u.id
        WHERE m.group_id = :gid AND m.role = 'student'
          AND m.status != 'rejected'
        GROUP BY u.id, u.full_name, u.email, m.status, m.joined_at
        ORDER BY m.status DESC, u.full_name
    """), {"gid": str(group_id)}).fetchall()

    return {
        "id": g[0], "name": g[1], "subject": g[2], "kind": g[3],
        "invite_code": g[4], "created_at": g[5],
        "students_count": sum(1 for s in students if s[3] == "active"),
        "pending_count": sum(1 for s in students if s[3] == "pending"),
        "students": [
            {
                "id": s[0], "full_name": s[1], "email": s[2],
                "status": s[3], "joined_at": s[4],
                "mastery_avg": float(s[5]) if s[5] is not None else None,
            }
            for s in students
        ],
    }


def get_group_by_code(session: Session, code: str) -> dict | None:
    """Публичная информация по инвайт-коду."""
    row = session.execute(text("""
        SELECT g.name, g.subject, u.full_name AS teacher_name
        FROM groups g
        LEFT JOIN users u ON u.id = g.owner_id
        WHERE g.invite_code = :code
    """), {"code": code.upper()}).fetchone()

    if row is None:
        return None

    return {"name": row[0], "subject": row[1], "teacher_name": row[2] or "Учитель"}


def join_by_code(
    session: Session,
    code: str,
    full_name: str,
    email: str,
    password: str,
) -> dict:
    """Регистрация ученика по коду."""
    group = session.execute(text("""
        SELECT id, name, tenant_id FROM groups WHERE invite_code = :code
    """), {"code": code.upper()}).fetchone()

    if group is None:
        raise ValueError("Код класса не найден")

    group_id, group_name, group_tenant = group

    existing = session.execute(text(
        "SELECT id FROM users WHERE email = :e"
    ), {"e": email}).fetchone()

    if existing:
        raise ValueError("Этот email уже зарегистрирован")

    user_id = str(uuid.uuid4())
    session.execute(text("""
        INSERT INTO users
            (id, tenant_id, role, full_name, email, password_hash, status)
        VALUES
            (:id, :t, 'student', :name, :email, :pwd, 'pending')
    """), {
        "id": user_id, "t": group_tenant, "name": full_name,
        "email": email, "pwd": hash_password(password),
    })

    session.execute(text("""
        INSERT INTO memberships (group_id, user_id, role, status)
        VALUES (:gid, :uid, 'student', 'pending')
    """), {"gid": str(group_id), "uid": user_id})

    return {"status": "pending", "group_name": group_name}


def approve_student(
    session: Session,
    group_id: UUID | str,
    student_id: UUID | str,
    owner_id: str,
) -> bool:
    """Подтвердить ученика."""
    g = session.execute(text("""
        SELECT 1 FROM groups WHERE id = :gid AND owner_id = :owner
    """), {"gid": str(group_id), "owner": owner_id}).fetchone()

    if not g:
        return False

    session.execute(text("""
        UPDATE memberships
        SET status = 'active'
        WHERE group_id = :gid AND user_id = :sid AND role = 'student'
    """), {"gid": str(group_id), "sid": str(student_id)})

    session.execute(text("""
        UPDATE users SET status = 'active'
        WHERE id = :sid AND status = 'pending'
    """), {"sid": str(student_id)})

    return True


def reject_student(
    session: Session,
    group_id: UUID | str,
    student_id: UUID | str,
    owner_id: str,
) -> bool:
    """Отклонить заявку ученика."""
    g = session.execute(text("""
        SELECT 1 FROM groups WHERE id = :gid AND owner_id = :owner
    """), {"gid": str(group_id), "owner": owner_id}).fetchone()

    if not g:
        return False

    session.execute(text("""
        UPDATE memberships
        SET status = 'rejected'
        WHERE group_id = :gid AND user_id = :sid AND role = 'student'
    """), {"gid": str(group_id), "sid": str(student_id)})

    remaining = session.execute(text("""
        SELECT COUNT(*) FROM memberships
        WHERE user_id = :sid AND status = 'active'
    """), {"sid": str(student_id)}).scalar()

    if remaining == 0:
        session.execute(text("""
            UPDATE users SET status = 'blocked' WHERE id = :sid
        """), {"sid": str(student_id)})

    return True


def regenerate_code(session: Session, group_id: UUID | str, owner_id: str) -> str | None:
    """Сгенерировать новый инвайт-код."""
    g = session.execute(text("""
        SELECT 1 FROM groups WHERE id = :gid AND owner_id = :owner
    """), {"gid": str(group_id), "owner": owner_id}).fetchone()

    if not g:
        return None

    for _ in range(10):
        code = _generate_invite_code()
        exists = session.execute(
            text("SELECT 1 FROM groups WHERE invite_code = :c"),
            {"c": code},
        ).fetchone()
        if not exists:
            break

    session.execute(text("""
        UPDATE groups SET invite_code = :c WHERE id = :gid
    """), {"c": code, "gid": str(group_id)})

    return code

def update_student_name(
    session: Session,
    student_id: UUID | str,
    new_name: str,
    owner_id: str,
) -> bool:
    """
    Обновить ФИО ученика. Только если этот ученик есть в классе этого учителя.
    """
    check = session.execute(text("""
        SELECT 1 FROM users u
        JOIN memberships m ON m.user_id = u.id
        JOIN groups g ON g.id = m.group_id
        WHERE u.id = :sid
          AND u.role = 'student'
          AND g.owner_id = :owner
        LIMIT 1
    """), {"sid": str(student_id), "owner": owner_id}).fetchone()

    if not check:
        return False

    session.execute(text("""
        UPDATE users SET full_name = :name WHERE id = :sid
    """), {"name": new_name, "sid": str(student_id)})

    return True

def remove_student_from_group(
    session: Session,
    group_id: UUID | str,
    student_id: UUID | str,
    owner_id: str,
) -> bool:
    """
    Убрать ученика из класса (soft delete — ставим rejected).
    """
    check = session.execute(text("""
        SELECT 1 FROM groups
        WHERE id = :gid AND owner_id = :owner
    """), {"gid": str(group_id), "owner": owner_id}).fetchone()

    if not check:
        return False

    session.execute(text("""
        UPDATE memberships
        SET status = 'rejected'
        WHERE group_id = :gid AND user_id = :sid AND role = 'student'
    """), {"gid": str(group_id), "sid": str(student_id)})

    return True