"""
Схемы графа знаний.
"""
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """Узел графа — навык."""
    id: str
    name: str
    module: str | None = None
    topic: str | None = None
    mastery: float | None = Field(None, ge=0.0, le=1.0, description="Уровень освоения")
    attempts: int | None = None
    status: str = Field("unknown", description="mastered / learning / weak / unknown")


class GraphEdge(BaseModel):
    """Ребро графа — связь между навыками."""
    source: str
    target: str
    relation: str = Field(..., description="prerequisite / contains / related")


class StudentGraph(BaseModel):
    """Граф знаний ученика."""
    student_id: str
    student_name: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class ClassGraph(BaseModel):
    """Граф класса — с агрегированным mastery."""
    class_name: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]