"""
Бизнес-логика для работы с графом знаний.
Соединяет Neo4j (структура) и PostgreSQL (mastery ученика).
"""
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db.neo4j import neo4j_session
from backend.models.graph import GraphNode, GraphEdge, StudentGraph, ClassGraph


# ─── Статус узла ─────────────────────────────────────────────

def _mastery_status(mastery: float | None) -> str:
    """
    Цветовая категория узла для UI.
    mastered — зелёный, learning — жёлтый,
    weak — красный, unknown — серый.
    """
    if mastery is None:
        return "unknown"
    if mastery >= 0.8:
        return "mastered"
    if mastery >= 0.5:
        return "learning"
    return "weak"


# ─── Neo4j: структура графа ──────────────────────────────────

def _fetch_full_graph() -> tuple[list[dict], list[dict]]:
    """
    Возвращает (nodes, edges) из Neo4j.
    Каждый node: {id, name, module, topic, difficulty}.
    """
    with neo4j_session() as session:
        # Узлы + module + topic через обход иерархии
        nodes_result = session.run("""
            MATCH (m:Module)-[:CONTAINS]->(t:Topic)-[:CONTAINS]->(s:Skill)
            RETURN s.id AS id, s.name AS name,
                   s.difficulty AS difficulty,
                   m.name AS module, t.name AS topic
        """)
        nodes = [dict(r) for r in nodes_result]

        # Рёбра prerequisite
        edges_result = session.run("""
            MATCH (pre:Skill)-[:PREREQUISITE]->(target:Skill)
            RETURN pre.id AS source, target.id AS target
        """)
        edges = [
            {"source": r["source"], "target": r["target"],
             "relation": "prerequisite"}
            for r in edges_result
        ]

    return nodes, edges


def _fetch_skill_with_prereqs(skill_id: str, depth: int = 3) -> tuple[list[dict], list[dict]]:
    """
    Подграф вокруг навыка: сам навык + все его prerequisite до указанной глубины.
    """
    with neo4j_session() as session:
        result = session.run("""
            MATCH path = (target:Skill {id: $sid})<-[:PREREQUISITE*0..$d]-(pre:Skill)
            WITH nodes(path) AS ns
            UNWIND ns AS n
            WITH DISTINCT n
            MATCH (m:Module)-[:CONTAINS]->(t:Topic)-[:CONTAINS]->(n)
            RETURN n.id AS id, n.name AS name,
                   n.difficulty AS difficulty,
                   m.name AS module, t.name AS topic
        """, sid=skill_id, d=depth)
        nodes = [dict(r) for r in result]

        # Рёбра среди этих узлов
        node_ids = [n["id"] for n in nodes]
        edges_result = session.run("""
            MATCH (pre:Skill)-[:PREREQUISITE]->(target:Skill)
            WHERE pre.id IN $ids AND target.id IN $ids
            RETURN pre.id AS source, target.id AS target
        """, ids=node_ids)
        edges = [
            {"source": r["source"], "target": r["target"],
             "relation": "prerequisite"}
            for r in edges_result
        ]

    return nodes, edges


# ─── PostgreSQL: mastery ─────────────────────────────────────

def _fetch_mastery(session: Session, student_id: UUID | str) -> dict[str, float]:
    """Возвращает {skill_id: mastery} для ученика."""
    rows = session.execute(text("""
        SELECT skill_id, mastery
        FROM student_mastery
        WHERE student_id = :sid
    """), {"sid": str(student_id)}).fetchall()
    return {r[0]: float(r[1]) for r in rows}


def _fetch_class_mastery(session: Session, group_id: UUID | str) -> dict[str, float]:
    """Средний mastery класса по каждому навыку."""
    rows = session.execute(text("""
        SELECT sm.skill_id, ROUND(AVG(sm.mastery)::numeric, 3)
        FROM student_mastery sm
        JOIN users u ON u.id = sm.student_id
        JOIN memberships m ON m.user_id = u.id
        WHERE m.group_id = :gid
        GROUP BY sm.skill_id
    """), {"gid": str(group_id)}).fetchall()
    return {r[0]: float(r[1]) for r in rows}


# ─── Публичные функции ───────────────────────────────────────

def get_full_graph(session: Session) -> tuple[list[GraphNode], list[GraphEdge]]:
    """
    Полный предметный граф без mastery.
    Используется для административных целей и отладки.
    """
    nodes_raw, edges_raw = _fetch_full_graph()

    nodes = [
        GraphNode(
            id=n["id"], name=n["name"],
            module=n.get("module"), topic=n.get("topic"),
        )
        for n in nodes_raw
    ]
    edges = [GraphEdge(**e) for e in edges_raw]

    return nodes, edges


def get_student_graph(
    session: Session,
    student_id: UUID | str,
) -> StudentGraph | None:
    """
    Граф ученика с раскраской по mastery.
    Возвращает None, если ученик не найден.
    """
    # ФИО
    user_row = session.execute(text("""
        SELECT id, full_name FROM users
        WHERE id = :sid AND role = 'student'
          AND tenant_id=current_setting('app.current_tenant', true)
    """), {"sid": str(student_id)}).fetchone()

    if user_row is None:
        return None

    # Neo4j: полный граф
    nodes_raw, edges_raw = _fetch_full_graph()

    # PostgreSQL: mastery ученика
    mastery = _fetch_mastery(session, student_id)
    attempts = dict(session.execute(text('SELECT skill_id, attempts FROM student_mastery WHERE student_id=:sid'),
                                   {'sid': str(student_id)}).fetchall())

    # Собираем узлы с mastery
    nodes = []
    for n in nodes_raw:
        m = mastery.get(n["id"]) if attempts.get(n['id'], 0) > 0 else None
        nodes.append(GraphNode(
            id=n["id"], name=n["name"],
            module=n.get("module"), topic=n.get("topic"),
            mastery=m,
            attempts=attempts.get(n['id'], 0),
            status=_mastery_status(m),
        ))

    edges = [GraphEdge(**e) for e in edges_raw]

    return StudentGraph(
        student_id=str(user_row[0]),
        student_name=user_row[1],
        nodes=nodes,
        edges=edges,
    )


def get_class_graph(
    session: Session,
    group_id: UUID | str,
) -> ClassGraph | None:
    """
    Граф класса с агрегированным mastery.
    """
    group_row = session.execute(text("""
        SELECT name FROM groups WHERE id = :gid
    """), {"gid": str(group_id)}).fetchone()

    if group_row is None:
        return None

    nodes_raw, edges_raw = _fetch_full_graph()
    class_mastery = _fetch_class_mastery(session, group_id)

    nodes = []
    for n in nodes_raw:
        m = class_mastery.get(n["id"])
        nodes.append(GraphNode(
            id=n["id"], name=n["name"],
            module=n.get("module"), topic=n.get("topic"),
            mastery=m,
            status=_mastery_status(m),
        ))

    edges = [GraphEdge(**e) for e in edges_raw]

    return ClassGraph(
        class_name=group_row[0],
        nodes=nodes,
        edges=edges,
    )


def get_skill_subgraph(skill_id: str) -> tuple[list[GraphNode], list[GraphEdge]]:
    """
    Подграф вокруг навыка: prerequisite-цепочка.
    """
    nodes_raw, edges_raw = _fetch_skill_with_prereqs(skill_id)

    nodes = [
        GraphNode(
            id=n["id"], name=n["name"],
            module=n.get("module"), topic=n.get("topic"),
        )
        for n in nodes_raw
    ]
    edges = [GraphEdge(**e) for e in edges_raw]

    return nodes, edges
