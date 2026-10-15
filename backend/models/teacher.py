from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel

ResultStatus = Literal['unanswered', 'correct', 'incorrect', 'skipped', 'surrendered']


class ResultCell(BaseModel):
    position: int
    task_id: UUID
    code: str
    status: ResultStatus
    answered_at: datetime | None


class StudentResult(BaseModel):
    student_id: UUID
    task_count: int
    answered_count: int
    correct_count: int
    state: str
    saved_state: str
    has_legacy: bool


class MatrixStudent(StudentResult):
    full_name: str
    cells: list[ResultCell]


class ResultSummary(BaseModel):
    students_count: int
    completed_count: int
    started_count: int
    task_count: int
    answered_count: int
    correct_count: int


class AssignmentInfo(BaseModel):
    id: UUID
    title: str
    topic: str
    status: str
    group_id: UUID
    class_name: str
    created_at: datetime
    sent_at: datetime | None


class AssignmentSummary(AssignmentInfo):
    students: list[StudentResult]
    summary: ResultSummary
    has_legacy: bool


class AssignmentMatrix(BaseModel):
    assignment: AssignmentInfo
    students: list[MatrixStudent]
    summary: ResultSummary
    common_tasks: bool
    has_legacy: bool


class Attempt(BaseModel):
    id: UUID
    answer: str | None
    correct: bool | None
    skipped: bool
    surrendered: bool
    time_sec: int | None
    created_at: datetime


class HistoryAttempt(Attempt):
    task_id: UUID
    assignment_id: UUID | None
    context: Literal['assignment', 'practice', 'legacy']
    code: str
    task_text: str
    expected: str | None
    options: dict | None
    assignment_title: str | None


class AttemptPage(BaseModel):
    items: list[HistoryAttempt]
    has_more: bool


class ReportTask(BaseModel):
    task_id: UUID
    code: str
    text: str
    options: dict | None
    expected: str | None
    position: int
    skill_name: str | None


class TaskAttempts(BaseModel):
    task: ReportTask
    attempts: list[Attempt]
    has_more: bool


class ProfileStudent(BaseModel):
    id: UUID
    full_name: str
    email: str | None
    status: str
    last_activity: datetime | None


class ProfileGroup(BaseModel):
    id: UUID
    name: str
    status: str


class SkillSummary(BaseModel):
    total_skills: int
    mastered: int
    learning: int
    weak: int


class WeakSkill(BaseModel):
    skill_id: str
    name: str
    topic: str | None
    mastery: float
    attempts: int
    correct: int


class StudentProfile(BaseModel):
    student: ProfileStudent
    groups: list[ProfileGroup]
    summary: SkillSummary
    weak_skills: list[WeakSkill]
    assignments: list[AssignmentSummary]
