"""
Схемы назначений (сгенерированных тестов).
"""
from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, Field


class GeneratedTask(BaseModel):
    """Задание в сгенерированном наборе для конкретного ученика."""
    task_id: UUID
    code: str
    text: str
    answer: str | None = None
    type: str | None = None
    options: dict | None = None
    skill_id: str | None = None
    primary_skill_name: str | None = None
    difficulty: float | None = None
    mastery: float | None = None
    score: float | None = None


class GeneratedStudentTest(BaseModel):
    """Персональный набор заданий для одного ученика."""
    student_id: UUID
    full_name: str
    tasks: list[GeneratedTask]
    blocked_skills: list[str] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    group_id: UUID = Field(..., description="ID класса (UUID)")
    topic: str = Field(..., description="Тема (например, «Кодирование»)")
    n_tasks: int = Field(5, ge=1, le=20, description="Число заданий на ученика")
    student_ids: list[UUID] | None = Field(None, min_length=1, max_length=500)
    personalize: bool = True


class RegenerateTaskRequest(BaseModel):
    group_id: UUID
    topic: str = Field(..., min_length=1)
    student_ids: list[UUID] = Field(..., min_length=1, max_length=500)
    personalize: bool = True
    task_id: UUID
    exclude_task_ids: list[UUID] = Field(default_factory=list, max_length=2000)


class RegeneratedTask(BaseModel):
    task: GeneratedTask
    match: Literal['same_skill', 'neighboring_skill']


class GeneratedTest(BaseModel):
    """Результат генерации теста для класса."""
    class_name: str
    topic: str
    n_tasks: int
    personalize: bool = True
    students: list[GeneratedStudentTest]
    usage_stats: dict | None = None


class AssignmentBrief(BaseModel):
    """Краткая информация о сохранённом назначении."""
    id: UUID
    title: str
    topic: str
    status: str
    created_at: datetime
    tasks_per_student: int

    model_config = {"from_attributes": True}


class PreviousResponse(BaseModel):
    answer: str
    correct: bool | None = None
    skipped: bool = False
    surrendered: bool = False
    time_sec: int | None = None
    expected: str | None = None


class AssignmentTaskForStudent(BaseModel):
    position: int
    task_id: UUID
    code: str
    text: str
    type: str
    options: dict | None = None
    previous_response: PreviousResponse | None = None
    has_legacy: bool = False

    model_config = {"from_attributes": True}


class AssignmentForStudent(BaseModel):
    """Тест, назначенный ученику."""
    assignment_id: UUID
    title: str
    topic: str
    deadline: datetime | None = None
    status: str
    tasks: list[AssignmentTaskForStudent]


class SaveAssignmentRequest(BaseModel):
    title: str = Field(..., min_length=2)
    group_id: UUID
    topic: str
    students: list[GeneratedStudentTest] = Field(..., min_length=1, max_length=500)
    personalize: bool = True

class AssignmentListItem(BaseModel):
    """Краткая карточка назначения для списка учителя."""
    id: UUID
    title: str
    topic: str
    status: str
    class_name: str | None = None
    tasks_per_student: int
    students_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class MyAssignmentBrief(BaseModel):
    id: UUID
    title: str
    topic: str
    status: str
    student_status: str = "pending"   # ← новое
    deadline: datetime | None = None
    task_count: int
    completed_count: int = 0
    created_at: datetime


class SendResponse(BaseModel):
    """Ответ на отправку."""
    assignment_id: UUID
    status: str
    students_count: int
    message: str
