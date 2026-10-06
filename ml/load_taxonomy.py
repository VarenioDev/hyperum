"""
Загрузка таксономии из YAML в Neo4j.
Идемпотентно: MERGE вместо CREATE, можно запускать многократно.
"""
import os
import yaml
from pathlib import Path
from neo4j import GraphDatabase

NEO4J_URI  = os.getenv("HYPERUM_NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("HYPERUM_NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("HYPERUM_NEO4J_PASSWORD", "hyperum_dev")

TAXONOMY_PATH = Path(__file__).parent.parent / "taxonomy" / "informatics_10_11.yaml"


def load_yaml():
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_constraints(tx):
    tx.run("CREATE CONSTRAINT skill_id IF NOT EXISTS FOR (s:Skill) REQUIRE s.id IS UNIQUE")
    tx.run("CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE")
    tx.run("CREATE CONSTRAINT module_id IF NOT EXISTS FOR (m:Module) REQUIRE m.id IS UNIQUE")


def load_module(tx, module):
    tx.run(
        "MERGE (m:Module {id: $id}) SET m.name = $name",
        id=module["id"], name=module["name"]
    )
    for topic in module.get("topics", []):
        tx.run(
            """
            MATCH (m:Module {id: $mid})
            MERGE (t:Topic {id: $id})
            SET t.name = $name
            MERGE (m)-[:CONTAINS]->(t)
            """,
            mid=module["id"], id=topic["id"], name=topic["name"]
        )
        for skill in topic.get("skills", []):
            tx.run(
                """
                MATCH (t:Topic {id: $tid})
                MERGE (s:Skill {id: $id})
                SET s.name = $name, s.difficulty = $diff
                MERGE (t)-[:CONTAINS]->(s)
                """,
                tid=topic["id"],
                id=skill["id"],
                name=skill["name"],
                diff=skill.get("difficulty", 0.5)
            )


def load_prerequisites(tx, module):
    """Второй проход: рёбра prerequisite между навыками."""
    for topic in module.get("topics", []):
        for skill in topic.get("skills", []):
            for prereq_id in skill.get("prerequisites", []):
                tx.run(
                    """
                    MATCH (target:Skill {id: $target})
                    MATCH (pre:Skill {id: $pre})
                    MERGE (pre)-[:PREREQUISITE]->(target)
                    """,
                    target=skill["id"], pre=prereq_id
                )


def main():
    taxonomy = load_yaml()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        session.execute_write(ensure_constraints)
        for module in taxonomy:
            session.execute_write(load_module, module)
            session.execute_write(load_prerequisites, module)
            print(f"Loaded: {module['id']} — {module['name']}")

    driver.close()
    print("Done.")


if __name__ == "__main__":
    main()