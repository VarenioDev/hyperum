"""
Синхронизация mastery учеников из PostgreSQL в Neo4j.
Создаёт узлы Student и рёбра MASTERY.
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from sqlalchemy import create_engine, text

load_dotenv()

NEO4J_URI = os.getenv("HYPERUM_NEO4J_URI")
NEO4J_USER = os.getenv("HYPERUM_NEO4J_USER")
NEO4J_PASS = os.getenv("HYPERUM_NEO4J_PASSWORD")
DB_URL = os.getenv("HYPERUM_DB_URL")
TENANT = os.getenv("HYPERUM_TENANT_DEFAULT", "school_lyceum")

pg_engine = create_engine(DB_URL)
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


def main():
    # 1. Читаем mastery из PostgreSQL
    with pg_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT sm.student_id, u.full_name,
                   sm.skill_id, sm.mastery, sm.attempts, sm.correct
            FROM student_mastery sm
            JOIN users u ON u.id = sm.student_id
            WHERE sm.tenant_id = :t
        """), {"t": TENANT}).fetchall()

    # 2. Пишем в Neo4j
    with driver.session() as session:
        session.run("""
            CREATE CONSTRAINT student_id IF NOT EXISTS
            FOR (s:Student) REQUIRE s.id IS UNIQUE
        """)

        count = 0
        for student_id, full_name, skill_id, mastery, attempts, correct in rows:
            # Узел Student (только UUID, без PII!)
            session.run("""
                MERGE (st:Student {id: $sid})
                SET st.tenant_id = $tenant
            """, sid=str(student_id), tenant=TENANT)

            # Ребро MASTERY
            session.run("""
                MATCH (st:Student {id: $sid})
                MATCH (sk:Skill {id: $skid})
                MERGE (st)-[m:MASTERY]->(sk)
                SET m.value = $val,
                    m.attempts = $att,
                    m.correct = $cor,
                    m.updated_at = datetime()
            """, sid=str(student_id), skid=skill_id,
                 val=mastery, att=attempts, cor=correct)
            count += 1

    driver.close()
    print(f"Синхронизировано {count} рёбер MASTERY.")


if __name__ == "__main__":
    main()