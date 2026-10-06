"""
Синхронизация таблицы skills в PostgreSQL из того же YAML.
Идемпотентно через ON CONFLICT.
"""
import os
import yaml
from pathlib import Path
from sqlalchemy import create_engine, text

DB_URL = os.getenv(
    "HYPERUM_DB_URL",
    "postgresql://hyperum:hyperum_dev@localhost:5432/hyperum"
)
TAXONOMY_PATH = Path(__file__).parent.parent / "taxonomy" / "informatics_10_11.yaml"

engine = create_engine(DB_URL)

UPSERT = text("""
    INSERT INTO skills (id, name, module, topic, difficulty, tenant_id)
    VALUES (:id, :name, :module, :topic, :difficulty, 'global')
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        module = EXCLUDED.module,
        topic = EXCLUDED.topic,
        difficulty = EXCLUDED.difficulty
""")

with open(TAXONOMY_PATH, encoding="utf-8") as f:
    taxonomy = yaml.safe_load(f)

with engine.begin() as conn:
    for module in taxonomy:
        for topic in module.get("topics", []):
            for skill in topic.get("skills", []):
                conn.execute(UPSERT, {
                    "id": skill["id"],
                    "name": skill["name"],
                    "module": module["name"],
                    "topic": topic["name"],
                    "difficulty": skill.get("difficulty", 0.5),
                })
                print(f"  upserted {skill['id']}")

print("Skills synced to PostgreSQL.")