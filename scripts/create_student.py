"""
Создание тестового ученика с паролем.
Использование:
    python -m scripts.create_student <full_name> <email> <password>
"""
import sys
from sqlalchemy import text
from backend.auth.security import hash_password
from backend.db.postgres import get_session


def create(full_name: str, email: str, password: str):
    if len(password) < 6:
        print("Пароль короче 6 символов")
        sys.exit(1)

    hashed = hash_password(password)

    with get_session() as session:
        # Проверяем, есть ли уже такой ученик
        existing = session.execute(text("""
            SELECT id FROM users WHERE full_name = :n AND role = 'student'
            LIMIT 1
        """), {"n": full_name}).fetchone()

        if existing:
            session.execute(text("""
                UPDATE users SET email = :e, password_hash = :h
                WHERE id = :id
            """), {"e": email, "h": hashed, "id": existing[0]})
            print(f"✅ Пароль обновлён для {full_name} ({email})")
            return

        # Создаём нового
        session.execute(text("""
            INSERT INTO users (tenant_id, role, full_name, email, password_hash)
            VALUES ('school_lyceum', 'student', :n, :e, :h)
        """), {"n": full_name, "e": email, "h": hashed})
        print(f"✅ Создан ученик: {full_name} ({email})")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Использование: python -m scripts.create_student <full_name> <email> <password>")
        sys.exit(1)
    create(sys.argv[1], sys.argv[2], sys.argv[3])