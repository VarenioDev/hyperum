"""Synthetic fixtures only. No database or graph connections are made."""
import os
os.environ['HYPERUM_DB_URL'] = 'postgresql+psycopg://test:test@localhost:1/test'
os.environ['HYPERUM_NEO4J_URI'] = 'bolt://localhost:1'

import copy
import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID
from contextlib import contextmanager
from datetime import datetime, timezone

from backend.services import assignment_generation as gen
from backend.services import assignments_service as base
from backend.models.assignments import GenerateRequest, AssignmentTaskForStudent


def task(number, skill='a', difficulty=0.5):
    return dict(task_id=str(UUID(int=number)), code=f'T{number}', text='**Test** $x^2$',
                answer='42', type='short', options=None, primary_skill=skill,
                primary_skill_name=skill.upper(), all_skills=[skill], difficulty=difficulty)


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.session.execute.return_value.fetchone.return_value = ('Class', 'test_tenant')
        self.students = [dict(id='one', full_name='Anna'), dict(id='two', full_name='Boris'),
                         dict(id='other', full_name='Vera')]
        self.candidates = [task(1), task(2), task(3, 'b')]
        self.mocks = {}
        for name, value in [('get_group_students', self.students), ('get_topic_skills', ['a', 'b', 'c']),
                            ('get_candidate_tasks', self.candidates), ('get_weak_prerequisites', set())]:
            mock = patch.object(base, name, return_value=value)
            self.mocks[name] = mock.start()
            self.addCleanup(mock.stop)
        mock = patch.object(base, 'get_student_mastery', side_effect=lambda _, sid: {
            'one': {'a': 0.2}, 'two': {'a': 0.8}, 'other': {'a': 0.99}}[sid])
        self.mastery = mock.start()
        self.addCleanup(mock.stop)

    def generate(self, **kwargs):
        return gen.generate_for_group(self.session, 'group', 'topic', 2,
                                      teacher_id='teacher', **kwargs)

    def replace(self, **kwargs):
        params = dict(group_id='group', teacher_id='teacher', topic='topic',
                      student_ids=['one', 'two'], personalize=False,
                      task_id=task(1)['task_id'], exclude_task_ids=[])
        params.update(kwargs)
        return gen.regenerate_task(self.session, **params)

    def test_common_averages_only_selected_and_copies_order(self):
        with patch.object(base, 'select_tasks_for_student', wraps=base.select_tasks_for_student) as selector:
            result = self.generate(student_ids=['one', 'two'], personalize=False)
        self.assertEqual(selector.call_args.args[0], {'a': 0.5, 'b': 0.5})
        self.assertEqual([c.args[1] for c in self.mastery.call_args_list], ['one', 'two'])
        first, second = result['students']
        self.assertEqual(first['tasks'], second['tasks'])
        self.assertIsNot(first['tasks'][0], second['tasks'][0])
        self.assertEqual(result['usage_stats'], dict(total_tasks_used=4, unique_tasks_used=2, max_usage=2))

    def test_personal_generation_preserves_individual_mastery(self):
        with patch.object(base, 'select_tasks_for_student', wraps=base.select_tasks_for_student) as selector:
            result = self.generate(student_ids=['one', 'two'])
        self.assertEqual(sorted(c.args[0]['a'] for c in selector.call_args_list), [0.2, 0.8])
        self.assertEqual(len(result['students']), 2)

    def test_empty_duplicate_and_foreign_selection_rejected(self):
        for ids in [[], ['one', 'one'], ['outsider']]:
            with self.subTest(ids=ids), self.assertRaises(gen.GenerationError):
                self.generate(student_ids=ids)

    def test_foreign_group_rejected_before_loading_students(self):
        self.session.execute.return_value.fetchone.return_value = None
        with self.assertRaises(gen.GenerationError) as caught:
            self.generate()
        self.assertEqual(caught.exception.status_code, 404)
        self.mocks['get_group_students'].assert_not_called()

    def test_insufficient_pool_fails_instead_of_silent_short_test(self):
        self.mocks['get_candidate_tasks'].return_value = [task(1)]
        with self.assertRaises(gen.GenerationError):
            self.generate()

    def test_replacement_prefers_original_skill(self):
        self.candidates[1]['difficulty'] = 0.9
        result = self.replace()
        self.assertEqual(result['task']['task_id'], task(2)['task_id'])
        self.assertEqual(result['match'], 'same_skill')
        self.assertEqual(result['task']['mastery'], 0.5)

    def test_replacement_prefers_nearest_neighbor_and_excludes_previous(self):
        self.mocks['get_candidate_tasks'].return_value = [task(1), task(2), task(3, 'b', 0.8), task(4, 'c', 0.5)]
        with patch.object(gen, 'skill_distances', return_value={'a': 0, 'b': 1, 'c': 2}):
            result = self.replace(exclude_task_ids=[task(2)['task_id']])
        self.assertEqual(result['task']['task_id'], task(3)['task_id'])
        self.assertEqual(result['match'], 'neighboring_skill')

    def test_replacement_does_not_repeat_or_leave_topic(self):
        with patch.object(gen, 'skill_distances', return_value={'a': 0}):
            with self.assertRaises(gen.GenerationError) as caught:
                self.replace(exclude_task_ids=[task(2)['task_id']])
        self.assertEqual(caught.exception.status_code, 404)

    def test_personal_replace_requires_one_student_and_respects_blocking(self):
        with self.assertRaises(gen.GenerationError):
            self.replace(personalize=True)
        self.mocks['get_weak_prerequisites'].return_value = {'a', 'b'}
        with self.assertRaises(gen.GenerationError):
            self.replace(personalize=True, student_ids=['one'])

    def test_graph_distance_is_undirected_and_graph_failure_is_conservative(self):
        with patch.object(base, 'neo4j_session') as connection:
            connection.return_value.__enter__.return_value.run.return_value = [
                {'source': 'b', 'target': 'a'}, {'source': 'b', 'target': 'c'}]
            self.assertEqual(gen.skill_distances('a', ['a', 'b', 'c']), {'a': 0, 'b': 1, 'c': 2})
            connection.side_effect = RuntimeError('offline')
            self.assertEqual(gen.skill_distances('a', ['a', 'b']), {'a': 0})

    def test_save_checks_common_order_duplicate_and_foreign_tasks(self):
        valid = dict(topic='topic', personalize=False, students=[
            dict(student_id='one', tasks=[task(1), task(2)]),
            dict(student_id='two', tasks=[task(1), task(2)])])
        self.assertEqual(gen.validate_saved_test(self.session, valid, 'group', 'teacher')[1], 'test_tenant')
        for tasks in [[task(2), task(1)], [task(1), task(1)], [task(1), task(99)], []]:
            invalid = copy.deepcopy(valid)
            invalid['students'][1]['tasks'] = tasks
            with self.subTest(tasks=tasks), self.assertRaises(gen.GenerationError):
                gen.validate_saved_test(self.session, invalid, 'group', 'teacher')

    def test_invalid_save_does_not_write_anything(self):
        with self.assertRaises(gen.GenerationError):
            base.save_assignment(self.session, dict(topic='topic', students=[]), 'teacher', 'Test', 'group')
        self.assertFalse(any('INSERT' in str(call.args[0]) for call in self.session.execute.call_args_list))

    def test_save_uses_owned_group_tenant_and_preserves_common_positions(self):
        generated = dict(topic='topic', personalize=False, n_tasks=2, students=[
            dict(student_id=sid, tasks=[task(2), task(1)]) for sid in ['one', 'two']])
        base.save_assignment(self.session, generated, 'teacher', 'Test', 'group')
        inserts = [call for call in self.session.execute.call_args_list if 'INSERT' in str(call.args[0])]
        self.assertEqual(inserts[0].args[1]['t'], 'test_tenant')
        task_rows = [call.args[1] for call in inserts if 'INSERT INTO assignment_tasks' in str(call.args[0])]
        self.assertEqual([(r['sid'], r['tid'], r['pos']) for r in task_rows], [
            ('one', task(2)['task_id'], 1), ('one', task(1)['task_id'], 2),
            ('two', task(2)['task_id'], 1), ('two', task(1)['task_id'], 2)])

    def test_send_keeps_selected_recipients(self):
        self.session.execute.return_value.fetchone.side_effect = [('teacher', 'draft', 'group'), ('Class', 'tenant')]
        self.session.execute.return_value.fetchall.return_value = [('one',), ('two',)]
        self.session.execute.return_value.scalar.return_value = 2
        self.assertEqual(base.send_assignment(self.session, 'assignment', 'teacher'), {'students_count': 2})
        self.assertTrue(any('UPDATE assignments' in str(call.args[0]) for call in self.session.execute.call_args_list))

    def test_send_rechecks_recipients_before_update(self):
        self.session.execute.return_value.fetchone.side_effect = [('teacher', 'draft', 'group'), ('Class', 'tenant')]
        self.session.execute.return_value.fetchall.return_value = [('outsider',)]
        with self.assertRaises(gen.GenerationError):
            base.send_assignment(self.session, 'assignment', 'teacher')
        self.assertFalse(any('UPDATE' in str(call.args[0]) for call in self.session.execute.call_args_list))

    def test_schema_compatibility_and_answer_separation(self):
        request = GenerateRequest(group_id=UUID(int=1), topic='topic')
        self.assertTrue(request.personalize)
        self.assertIsNone(request.student_ids)
        self.assertNotIn('answer', AssignmentTaskForStudent.model_fields)
        self.assertNotIn('primary_skill_name', AssignmentTaskForStudent.model_fields)


class AssignmentAPITests(unittest.TestCase):
    """Real ASGI routing and response validation, mocked storage only."""
    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        # Import routing without creating a real database engine/driver.
        with patch('sqlalchemy.create_engine', return_value=MagicMock()):
            from backend.api import assignments
        from backend.models.users import UserResponse
        self.api = assignments
        app = FastAPI()
        app.include_router(assignments.router, prefix='/api/v1')
        user = UserResponse(id=UUID(int=10), tenant_id='test', role='owner',
                            full_name='Test Teacher', created_at=datetime.now(timezone.utc))
        app.dependency_overrides[assignments.require_teacher] = lambda: user
        self.client = TestClient(app)
        @contextmanager
        def fake_session(_):
            yield MagicMock()
        mock = patch.object(assignments, 'tenant_session', fake_session)
        mock.start()
        self.addCleanup(mock.stop)
        self.payload = dict(group_id=str(UUID(int=20)), topic='Topic', n_tasks=1,
                            student_ids=[str(UUID(int=30))], personalize=False)

    def test_generate_serializes_full_teacher_card(self):
        result = dict(class_name='Class', topic='Topic', n_tasks=1, personalize=False,
                      students=[dict(student_id=self.payload['student_ids'][0], full_name='Test',
                                     tasks=[task(1)])])
        with patch.object(base, 'generate_for_group', return_value=result):
            response = self.client.post('/api/v1/assignments/generate', json=self.payload)
        self.assertEqual(response.status_code, 200, response.text)
        card = response.json()['students'][0]['tasks'][0]
        self.assertEqual(card['skill_id'], 'a')
        self.assertEqual(card['primary_skill_name'], 'A')
        self.assertEqual(card['answer'], '42')

    def test_replace_route_and_no_alternative_status(self):
        payload = {**self.payload, 'task_id': task(1)['task_id'], 'exclude_task_ids': []}
        with patch.object(gen, 'regenerate_task', return_value=dict(task=task(2), match='same_skill')):
            response = self.client.post('/api/v1/assignments/regenerate-task', json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['task']['task_id'], task(2)['task_id'])
        with patch.object(gen, 'regenerate_task', side_effect=gen.GenerationError('No alternatives', 404)):
            response = self.client.post('/api/v1/assignments/regenerate-task', json=payload)
        self.assertEqual(response.status_code, 404)

    def test_empty_recipients_rejected_before_service(self):
        with patch.object(base, 'generate_for_group') as service:
            response = self.client.post('/api/v1/assignments/generate', json={**self.payload, 'student_ids': []})
        self.assertEqual(response.status_code, 422)
        service.assert_not_called()


if __name__ == '__main__':
    unittest.main()
