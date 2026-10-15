"""
Роутер /assignments — назначения (сгенерированные тесты).
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.dependencies import get_current_user, require_teacher
from backend.db.postgres import tenant_session
from backend.models.assignments import (
    GenerateRequest, GeneratedTest, GeneratedStudentTest, GeneratedTask,
    SaveAssignmentRequest, AssignmentListItem, MyAssignmentBrief,
    SendResponse, AssignmentTaskForStudent,
    RegenerateTaskRequest, RegeneratedTask,
)
from backend.models.users import UserResponse
from backend.services import assignments_service as svc
from backend.services import assignment_generation as generation


router = APIRouter(prefix="/assignments", tags=["assignments"])


def generated_task(task: dict) -> GeneratedTask:
    return GeneratedTask(**{**task, "skill_id": task.get("primary_skill") or task.get("skill_id")})


# ─── Генерация (учитель) ─────────────────────────────────────

@router.post("/generate", response_model=GeneratedTest)
async def generate_test(
    payload: GenerateRequest,
    user: UserResponse = Depends(require_teacher),
):
    try:
        with tenant_session(user.tenant_id) as session:
            result = svc.generate_for_group(
                session, group_id=str(payload.group_id), topic=payload.topic,
                n_tasks=payload.n_tasks, teacher_id=str(user.id),
                student_ids=[str(s) for s in payload.student_ids] if payload.student_ids is not None else None,
                personalize=payload.personalize,
            )
    except generation.GenerationError as exc:
        raise HTTPException(exc.status_code, detail=str(exc)) from exc

    # Преобразуем в модели
    students = []
    for s in result["students"]:
        tasks = [generated_task(t) for t in s["tasks"]]
        students.append(GeneratedStudentTest(
            student_id=s["student_id"],
            full_name=s["full_name"],
            tasks=tasks,
            blocked_skills=s.get("blocked_skills", []),
        ))

    return GeneratedTest(
        class_name=result["class_name"],
        topic=result["topic"],
        n_tasks=result["n_tasks"],
        personalize=result["personalize"],
        students=students,
        usage_stats=result.get("usage_stats"),
    )


@router.post("/regenerate-task", response_model=RegeneratedTask)
async def regenerate_task(
    payload: RegenerateTaskRequest,
    user: UserResponse = Depends(require_teacher),
):
    try:
        with tenant_session(user.tenant_id) as session:
            result = generation.regenerate_task(
                session, group_id=str(payload.group_id), teacher_id=str(user.id),
                topic=payload.topic, student_ids=[str(s) for s in payload.student_ids],
                personalize=payload.personalize, task_id=str(payload.task_id),
                exclude_task_ids=[str(t) for t in payload.exclude_task_ids],
            )
    except generation.GenerationError as exc:
        raise HTTPException(exc.status_code, detail=str(exc)) from exc
    return RegeneratedTask(task=generated_task(result["task"]), match=result["match"])


@router.post("/save", response_model=dict)
async def save_generated(
    payload: SaveAssignmentRequest,
    user: UserResponse = Depends(require_teacher),
):
    generated = {
        "class_name": "",  # больше не используется для поиска
        "topic": payload.topic,
        "personalize": payload.personalize,
        "n_tasks": max(len(s.tasks) for s in payload.students),
        "students": [
            {
                "student_id": str(s.student_id),
                "full_name": s.full_name,
                "tasks": [
                    {
                        "task_id": str(t.task_id),
                        "code": t.code,
                        "text": t.text,
                        "skill_id": t.skill_id,
                        "difficulty": t.difficulty,
                    }
                    for t in s.tasks
                ],
                "blocked_skills": s.blocked_skills,
            }
            for s in payload.students
        ],
    }

    with tenant_session(user.tenant_id) as session:
        try:
            assignment_id = svc.save_assignment(
                session, generated,
                created_by=str(user.id),
                title=payload.title,
                group_id=str(payload.group_id),
            )
        except generation.GenerationError as e:
            raise HTTPException(
                status_code=e.status_code,
                detail=str(e),
            )

    return {"assignment_id": assignment_id, "status": "draft"}


@router.post("/{assignment_id}/send", response_model=SendResponse)
async def send_assignment(
    assignment_id: UUID,
    user: UserResponse = Depends(require_teacher),
):
    """
    Отправить черновик ученикам.
    """
    with tenant_session(user.tenant_id) as session:
        try:
            result = svc.send_assignment(session, str(assignment_id), str(user.id))
        except generation.GenerationError as exc:
            raise HTTPException(exc.status_code, detail=str(exc)) from exc

    if "error" in result:
        code = result["error"]
        if code == "not_found":
            raise HTTPException(404, detail="Назначение не найдено")
        if code == "forbidden":
            raise HTTPException(403, detail="Это не ваше назначение")
        raise HTTPException(400, detail=f"Нельзя отправить: {code}")

    return SendResponse(
        assignment_id=assignment_id,
        status="sent",
        students_count=result["students_count"],
        message=f"Отправлено {result['students_count']} ученикам",
    )


# ─── Списки (учитель) ────────────────────────────────────────

@router.get("", response_model=list[AssignmentListItem])
async def list_my_assignments(
    user: UserResponse = Depends(require_teacher),
):
    """Список назначений текущего учителя."""
    with tenant_session(user.tenant_id) as session:
        rows = svc.list_assignments_for_teacher(session, str(user.id))
    return [AssignmentListItem(**r) for r in rows]


# ─── Ученик ──────────────────────────────────────────────────

@router.get("/my", response_model=list[MyAssignmentBrief])
async def my_assignments(
    user: UserResponse = Depends(get_current_user),
):
    """
    Активные тесты текущего ученика.
    Только с role=student.
    """
    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Только для учеников",
        )

    with tenant_session(user.tenant_id) as session:
        rows = svc.list_assignments_for_student(session, str(user.id))

    return [MyAssignmentBrief(**r) for r in rows]


@router.get("/{assignment_id}/tasks",
            response_model=list[AssignmentTaskForStudent])
async def assignment_tasks(
    assignment_id: UUID,
    user: UserResponse = Depends(get_current_user),
):
    """
    Задания конкретного теста (без правильных ответов).
    """
    with tenant_session(user.tenant_id) as session:
        tasks = svc.get_assignment_tasks(
            session, str(assignment_id), str(user.id)
        )

    if tasks is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Назначение не найдено или не для вас",
        )

    return [AssignmentTaskForStudent(**t) for t in tasks]
