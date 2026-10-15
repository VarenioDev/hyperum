"""Synthetic fixtures and mocked sessions. Never connects to project databases."""
import os
os.environ['HYPERUM_DB_URL'] = 'postgresql+psycopg://test:test@localhost:1/test'
os.environ['HYPERUM_NEO4J_URI'] = 'bolt://localhost:1'

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID
import unittest
from unittest.mock import MagicMock, patch
from backend.services import teacher_reporting as report, responses_service as responses
from backend.services.reporting_access import ReportNotFound, owned_student, owned_assignment


def uid(n):
    return str(UUID(int=n))


def result_rows():
    stamp = datetime.now(timezone.utc)
    return [dict(student_id=uid(1), full_name='Anna', saved_state='completed',
                 position=i, task_id=uid(10+i), code=f'T{i}', id=uid(100+i) if i<5 else None,
                 correct=i==1, skipped=i==3, surrendered=i==4, created_at=stamp,
                 has_legacy=False) for i in range(1, 6)]


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()

    def test_matrix_states_and_last_attempt_summary(self):
        self.session.execute.return_value.mappings.return_value.all.return_value = result_rows()
        with patch.object(report, 'owned_assignment', return_value={'id': uid(50)}):
            data = report.assignment_matrix(self.session, uid(50), uid(5))
        student = data['students'][0]
        self.assertEqual([c['status'] for c in student['cells']], ['correct','incorrect','skipped','surrendered','unanswered'])
        self.assertEqual(student['answered_count'], 4)
        self.assertEqual(student['correct_count'], 1)
        self.assertEqual(student['state'], 'in_progress')
        self.assertEqual(data['summary']['completed_count'], 0)

    def test_common_test_detected_by_task_ids_and_order(self):
        rows = result_rows()
        other = [{**r, 'student_id': uid(2), 'full_name': 'Boris'} for r in rows]
        self.session.execute.return_value.mappings.return_value.all.return_value = rows + other
        with patch.object(report, 'owned_assignment', return_value={}):
            self.assertTrue(report.assignment_matrix(self.session, uid(50), uid(5))['common_tasks'])
            other[0]['task_id'] = uid(999)
            self.assertFalse(report.assignment_matrix(self.session, uid(50), uid(5))['common_tasks'])

    def test_result_never_uses_saved_completion_as_current_score(self):
        rows = [{**r, 'id': None, 'has_legacy': True} for r in result_rows()]
        self.session.execute.return_value.mappings.return_value.all.return_value = rows
        with patch.object(report, 'owned_assignment', return_value={}):
            data = report.assignment_matrix(self.session, uid(50), uid(5))
        self.assertTrue(data['has_legacy'])
        self.assertEqual(data['summary']['correct_count'], 0)
        self.assertEqual(data['summary']['completed_count'], 0)

    def test_access_denial_stops_report_queries(self):
        with patch.object(report, 'owned_assignment', side_effect=ReportNotFound()):
            with self.assertRaises(ReportNotFound):
                report.assignment_matrix(self.session, uid(50), uid(5))
        self.session.execute.assert_not_called()

    def test_student_and_assignment_access_require_existing_owned_rows(self):
        self.session.execute.return_value.mappings.return_value.first.return_value = None
        for function in [owned_student, owned_assignment]:
            with self.assertRaises(ReportNotFound):
                function(self.session, uid(1), uid(2))

    def test_missing_student_task_not_returned_from_other_test(self):
        self.session.execute.return_value.mappings.return_value.first.return_value = None
        with patch.object(report, 'owned_assignment', return_value={}):
            with self.assertRaises(ReportNotFound):
                report.task_attempts(self.session, uid(50), uid(1), uid(10), uid(5))
        self.assertEqual(self.session.execute.call_count, 1)

    def test_history_pagination_uses_extra_row_and_preserves_context(self):
        rows = [dict(id=uid(i), context='legacy') for i in range(1, 4)]
        self.session.execute.return_value.mappings.return_value.all.return_value = rows
        page = report.attempt_history(self.session, uid(5), uid(1), skill_id='skill', limit=2, offset=2)
        self.assertEqual(len(page['items']), 2)
        self.assertTrue(page['has_more'])
        self.assertEqual(page['items'][0]['context'], 'legacy')
        self.assertEqual(self.session.execute.call_args.args[1]['skill'], 'skill')

    def test_summary_empty_and_all_answered(self):
        self.assertEqual(report.summarize_students([])['task_count'], 0)
        totals = report.student_totals([{'status':'correct'}, {'status':'surrendered'}])
        self.assertEqual(totals, dict(task_count=2, answered_count=2, correct_count=1, state='completed'))


class ResponseContextTests(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.session.execute.return_value.fetchone.return_value = (1,)
        self.session.execute.return_value.scalar.return_value = uid(100)

    def test_new_normal_response_stores_exact_test_and_practice_stays_separate(self):
        for aid in [uid(50), None]:
            self.session.reset_mock()
            with patch.object(responses, 'check_answer', return_value={'correct':True,'expected':'42'}), \
                 patch.object(responses, 'get_task_skills', return_value=[]), \
                 patch.object(responses, '_mark_assignment_completed_if_done') as completion:
                responses.submit_response(self.session, 'tenant', uid(1), uid(10), '42', assignment_id=aid)
            inserts = [call.args[1] for call in self.session.execute.call_args_list if 'INSERT INTO responses' in str(call.args[0])]
            self.assertEqual(inserts[0]['aid'], aid)
            self.assertEqual(inserts[0]['context'], 'assignment' if aid else 'practice')
            self.assertEqual(completion.call_count, 1 if aid else 0)

    def test_unowned_unsent_or_wrong_task_rejected_before_check_or_insert(self):
        self.session.execute.return_value.fetchone.return_value = None
        with patch.object(responses, 'check_answer') as check:
            with self.assertRaises(responses.InvalidAssignmentResponse):
                responses.submit_response(self.session, 'tenant', uid(1), uid(10), '42', assignment_id=uid(50))
        check.assert_not_called()
        self.assertFalse(any('INSERT' in str(c.args[0]) for c in self.session.execute.call_args_list))

    def test_surrender_is_explicit_skip_in_same_assignment(self):
        with patch.object(responses, '_mark_assignment_completed_if_done'):
            result = responses.submit_response(self.session, 'tenant', uid(1), uid(10), '', assignment_id=uid(50), surrendered=True)
        self.assertTrue(result['skipped'])
        inserts = [c.args[1] for c in self.session.execute.call_args_list if 'INSERT INTO responses' in str(c.args[0])]
        self.assertEqual(inserts[0]['aid'], uid(50))
        self.assertTrue(inserts[0]['surr'])

class TeacherAPITests(unittest.TestCase):
    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        with patch('sqlalchemy.create_engine', return_value=MagicMock()):
            from backend.api import teacher
        from backend.models.users import UserResponse
        self.api = teacher
        self.app = FastAPI()
        self.app.include_router(teacher.router, prefix='/api/v1')
        self.user = UserResponse(id=uid(5), tenant_id='test', role='owner', full_name='Test Teacher', created_at=datetime.now(timezone.utc))
        self.app.dependency_overrides[teacher.require_teacher] = lambda: self.user
        self.client = TestClient(self.app)
        @contextmanager
        def fake_session(_):
            yield MagicMock()
        mock = patch.object(teacher, 'tenant_session', fake_session)
        mock.start()
        self.addCleanup(mock.stop)

    def test_teacher_matrix_serialization(self):
        data = dict(assignment=dict(id=uid(50),title='Test',topic='Topic',status='sent',group_id=uid(30),class_name='Class',created_at=datetime.now(timezone.utc),sent_at=None),
                    students=[],summary=report.summarize_students([]),common_tasks=False,has_legacy=False)
        with patch.object(report, 'assignment_matrix', return_value=data):
            response = self.client.get(f'/api/v1/teacher/assignments/{uid(50)}')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['assignment']['title'], 'Test')

    def test_denied_student_returns_404(self):
        with patch.object(report, 'student_profile', side_effect=ReportNotFound('No access')):
            response = self.client.get(f'/api/v1/teacher/students/{uid(1)}')
        self.assertEqual(response.status_code, 404)

    def test_student_role_cannot_read_teacher_reports(self):
        from backend.auth.dependencies import get_current_user
        self.app.dependency_overrides.clear()
        self.app.dependency_overrides[get_current_user] = lambda: self.user.model_copy(update={'role':'student'})
        response = self.client.get(f'/api/v1/teacher/assignments/{uid(50)}')
        self.assertEqual(response.status_code, 403)

    def test_history_requires_access_before_loading(self):
        with patch.object(self.api, 'owned_student', side_effect=ReportNotFound()), patch.object(report, 'attempt_history') as history:
            response = self.client.get(f'/api/v1/teacher/students/{uid(1)}/responses')
        self.assertEqual(response.status_code, 404)
        history.assert_not_called()


if __name__ == '__main__':
    unittest.main()
