"""
Установка пароля пользователю.
Использование:
    python -m scripts.set_password <email> <password>
"""
import sys
from sqlalchemy import text
from backend.auth.security import hash_password
from backend.db.postgres import get_session


def set_password(email: str, password: str):
    if len(password) < 6:
        print("Ошибка: пароль короче 6 символов")
        sys.exit(1)

    hashed = hash_password(password)

    with get_session() as session:
        result = session.execute(
            text("""
                UPDATE users SET password_hash = :h
                WHERE email = :e
                RETURNING id, full_name
            """),
            {"h": hashed, "e": email},
        ).fetchone()

    if result is None:
        print(f"Пользователь {email} не найден")
        sys.exit(1)

    print(f"✅ Пароль установлен для {result[1]} ({email})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python -m scripts.set_password <email> <password>")
        sys.exit(1)
    set_password(sys.argv[1], sys.argv[2])