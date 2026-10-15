from contextlib import contextmanager
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.auth.dependencies import require_teacher
from backend.db.postgres import tenant_session
from backend.models.users import UserResponse
from backend.models.teacher import AssignmentSummary, AssignmentMatrix, TaskAttempts, StudentProfile, AttemptPage
from backend.services import teacher_reporting as reports
from backend.services.reporting_access import ReportNotFound, owned_student

router = APIRouter(prefix='/teacher', tags=['teacher'])


@contextmanager
def report_session(user):
    try:
        with tenant_session(user.tenant_id) as session:
            yield session
    except ReportNotFound as exc:
        raise HTTPException(404, detail=str(exc)) from exc


@router.get('/classes/{group_id}/assignments', response_model=list[AssignmentSummary])
def class_assignments(group_id: UUID, user: UserResponse = Depends(require_teacher)):
    with report_session(user) as session:
        return reports.class_activity(session, group_id, user.id)


@router.get('/assignments/{assignment_id}', response_model=AssignmentMatrix)
def assignment_results(assignment_id: UUID, user: UserResponse = Depends(require_teacher)):
    with report_session(user) as session:
        return reports.assignment_matrix(session, assignment_id, user.id)


@router.get('/assignments/{assignment_id}/students/{student_id}/tasks/{task_id}', response_model=TaskAttempts)
def task_results(assignment_id: UUID, student_id: UUID, task_id: UUID,
                 offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
                 user: UserResponse = Depends(require_teacher)):
    with report_session(user) as session:
        return reports.task_attempts(session, assignment_id, student_id, task_id, user.id, limit, offset)


@router.get('/students/{student_id}', response_model=StudentProfile)
def student_profile(student_id: UUID, user: UserResponse = Depends(require_teacher)):
    with report_session(user) as session:
        return reports.student_profile(session, student_id, user.id)


@router.get('/students/{student_id}/responses', response_model=AttemptPage)
def student_responses(student_id: UUID, skill_id: str | None = Query(None, max_length=200),
                      offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
                      user: UserResponse = Depends(require_teacher)):
    with report_session(user) as session:
        owned_student(session, student_id, user.id)
        return reports.attempt_history(session, user.id, student_id, skill_id=skill_id, limit=limit, offset=offset)
