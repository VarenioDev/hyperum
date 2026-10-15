"""Actual PostgreSQL SQL + migrations on PGlite in RAM. No .env or live DB access.

Run after `cd pwa; npm ci`: python -m unittest discover -s tests -p test_teacher_postgres.py -v
"""
import json
from pathlib import Path
import re
import subprocess
import unittest
from unittest.mock import patch
from uuid import UUID
from backend.services import teacher_reporting as reports, responses_service as responses, assignments_service as assignments
from backend.services.reporting_access import owned_student, ReportNotFound


ROOT = Path(__file__).resolve().parents[1]
def uid(n):
    return str(UUID(int=n))


class DatabaseError(Exception):
    pass


class Result:
    def __init__(self, result):
        self.rows = result['rows']
        self.fields = result['fields']
    def mappings(self):
        return self
    def first(self):
        return self.rows[0] if self.rows else None
    def all(self):
        return self.rows
    def fetchall(self):
        return [tuple(r.get(k) for k in self.fields) for r in self.rows]
    def fetchone(self):
        return self.fetchall()[0] if self.rows else None
    def scalar(self):
        return self.fetchone()[0] if self.rows else None


class MemorySession:
    def __init__(self, process):
        self.process = process
    def execute(self, statement, params=None):
        values = []
        names = {}
        def bind(match):
            name = match[1]
            if name not in names:
                names[name] = len(values)+1
                value = (params or {})[name]
                values.append(str(value) if isinstance(value, UUID) else value)
            return '$'+str(names[name])
        sql = re.sub(r'(?<!:):([A-Za-z_]\w*)', bind, str(statement))
        self.process.stdin.write(json.dumps({'sql':sql,'params':values})+'\n')
        self.process.stdin.flush()
        message = self.process.stdout.readline()
        if not message:
            raise RuntimeError('In-memory PostgreSQL process stopped')
        result = json.loads(message)
        if 'error' in result:
            raise DatabaseError(f"{result['code']}: {result['error']}")
        return Result(result)


class PostgresReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.process = subprocess.Popen(['node','scripts/reporting-postgres.mjs'], cwd=ROOT/'pwa',
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8')
        cls.ready = json.loads(cls.process.stdout.readline())
        cls.db = MemorySession(cls.process)
        cls.db.execute('CREATE ROLE report_reader')
        cls.db.execute('GRANT USAGE ON SCHEMA public TO report_reader')
        cls.db.execute('GRANT SELECT ON ALL TABLES IN SCHEMA public TO report_reader')

    @classmethod
    def tearDownClass(cls):
        cls.process.stdin.write('{"close":true}\n')
        cls.process.stdin.flush()
        cls.process.communicate(timeout=15)

    def setUp(self):
        db = self.db
        db.execute('TRUNCATE responses,student_mastery,assignment_tasks,assignment_students,assignments,memberships,groups,users,task_labels,tasks,skills,tenants CASCADE')
        for tenant in ['test','other']:
            db.execute("INSERT INTO tenants(id,name,kind) VALUES (:id,:id,'school')", {'id':tenant})
        db.execute("SELECT set_config('app.current_tenant','test',false)")
        for n, role, tenant in [(1,'owner','test'),(2,'owner','test'),(3,'owner','other'),(11,'student','test'),(12,'student','test'),(13,'student','other')]:
            db.execute('INSERT INTO users(id,tenant_id,role,full_name) VALUES (:id,:tenant,:role,:name)',
                       dict(id=uid(n),tenant=tenant,role=role,name=f'Synthetic {n}'))
        for gid, teacher, student, tenant in [(21,1,11,'test'),(22,2,12,'test'),(23,3,13,'other')]:
            db.execute("INSERT INTO groups(id,tenant_id,owner_id,name) VALUES (:id,:tenant,:owner,:name)", dict(id=uid(gid),tenant=tenant,owner=uid(teacher),name=f'Class {gid}'))
            db.execute("INSERT INTO memberships(group_id,user_id,role) VALUES (:gid,:sid,'student')",dict(gid=uid(gid),sid=uid(student)))
        db.execute("INSERT INTO skills(id,name,topic) VALUES ('skill','Synthetic Skill','Topic')")
        for tid in [31,32]:
            db.execute("INSERT INTO tasks(id,text,answer,code,type) VALUES (:id,'Synthetic **task** $x^2$','42',:code,'text')",dict(id=uid(tid),code=f'T{tid}'))
            db.execute("INSERT INTO task_labels(task_id,skill_id,model,is_primary,difficulty) VALUES (:id,'skill','deepseek',true,0.5)",dict(id=uid(tid)))
        for aid, gid, teacher, student, status in [(41,21,1,11,'sent'),(42,21,1,11,'sent'),(43,21,1,11,'draft'),(44,22,2,12,'sent')]:
            db.execute("INSERT INTO assignments(id,tenant_id,group_id,created_by,topic,title,status,tasks_per_student,sent_at) VALUES (:id,'test',:gid,:owner,'Topic',:title,:status,2,now())",dict(id=uid(aid),gid=uid(gid),owner=uid(teacher),title=f'Test {aid}',status=status))
            db.execute('INSERT INTO assignment_students(assignment_id,student_id) VALUES (:aid,:sid)',dict(aid=uid(aid),sid=uid(student)))
            for position, tid in enumerate([31,32],1):
                db.execute('INSERT INTO assignment_tasks(assignment_id,student_id,task_id,position) VALUES (:aid,:sid,:tid,:pos)',dict(aid=uid(aid),sid=uid(student),tid=uid(tid),pos=position))
        self.sync = patch.object(responses,'sync_mastery_to_neo4j')
        self.sync.start()
        self.addCleanup(self.sync.stop)

    def submit(self, aid=41, tid=31, answer='42', **kwargs):
        return responses.submit_response(self.db,'test',uid(11),uid(tid),answer,
                                         assignment_id=uid(aid) if aid else None, **kwargs)

    def test_migration_preserved_old_answer_without_guessing(self):
        self.assertEqual(self.ready['legacy'],dict(assignment_id=None,context='legacy',answer='42',correct=True))

    def test_same_task_in_two_tests_and_practice_never_cross_counts(self):
        self.submit(41,answer='wrong')
        self.submit(42,answer='42')
        self.submit(None,answer='42')
        a = reports.assignment_matrix(self.db,uid(41),uid(1))
        b = reports.assignment_matrix(self.db,uid(42),uid(1))
        self.assertEqual(a['students'][0]['cells'][0]['status'],'incorrect')
        self.assertEqual(b['students'][0]['cells'][0]['status'],'correct')
        self.assertEqual(a['summary']['answered_count'],1)
        self.assertEqual(b['summary']['answered_count'],1)
        self.assertFalse(a['has_legacy'])
        self.assertEqual(len(reports.attempt_history(self.db,uid(1),uid(11))['items']),3)

    def test_latest_wrong_replaces_previous_correct(self):
        self.submit(answer='42')
        self.submit(answer='wrong')
        matrix=reports.assignment_matrix(self.db,uid(41),uid(1))
        self.assertEqual(matrix['summary']['correct_count'],0)
        self.assertEqual(matrix['summary']['answered_count'],1)
        attempts=reports.task_attempts(self.db,uid(41),uid(11),uid(31),uid(1))
        self.assertEqual([a['correct'] for a in attempts['attempts']],[False,True])

    def test_latest_ties_are_resolved_by_id(self):
        for n, correct in [(101,True),(102,False)]:
            self.db.execute("INSERT INTO responses(id,tenant_id,student_id,task_id,assignment_id,context,answer,correct,created_at) VALUES (:id,'test',:sid,:tid,:aid,'assignment','42',:correct,'2026-01-01')",dict(id=uid(n),sid=uid(11),tid=uid(31),aid=uid(41),correct=correct))
        self.assertEqual(reports.assignment_matrix(self.db,uid(41),uid(1))['summary']['correct_count'],0)

    def test_skip_surrender_completion_and_restore_are_assignment_specific(self):
        self.submit(skipped=True)
        self.submit(tid=32,surrendered=True)
        report=reports.assignment_matrix(self.db,uid(41),uid(1))
        self.assertEqual([c['status'] for c in report['students'][0]['cells']],['skipped','surrendered'])
        self.assertEqual(report['summary']['completed_count'],1)
        restored=assignments.get_assignment_tasks(self.db,uid(41),uid(11))
        self.assertTrue(restored[1]['previous_response']['surrendered'])
        other=assignments.get_assignment_tasks(self.db,uid(42),uid(11))
        self.assertIsNone(other[0]['previous_response'])

    def test_draft_foreign_assignment_and_foreign_student_rejected(self):
        for aid in [43,44]:
            with self.assertRaises(responses.InvalidAssignmentResponse):
                self.submit(aid)
        for sid in [12,13]:
            with self.assertRaises(ReportNotFound):
                owned_student(self.db,uid(sid),uid(1))
        with self.assertRaises(ReportNotFound):
            reports.assignment_matrix(self.db,uid(44),uid(1))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM responses').scalar(),0)

    def test_fk_rejects_assignment_task_not_given_to_student(self):
        with self.assertRaises(DatabaseError):
            self.db.execute("INSERT INTO responses(tenant_id,student_id,task_id,assignment_id,context) VALUES ('test',:sid,:tid,:aid,'assignment')",dict(sid=uid(12),tid=uid(31),aid=uid(41)))
        with self.assertRaises(DatabaseError):
            self.db.execute("INSERT INTO responses(tenant_id,student_id,task_id,assignment_id,context) VALUES ('test',:sid,:tid,:aid,'practice')",dict(sid=uid(11),tid=uid(31),aid=uid(41)))

    def test_class_profile_skill_history_and_existing_group_query(self):
        self.submit(answer='wrong')
        self.submit(tid=32)
        items=reports.class_activity(self.db,uid(21),uid(1))
        a=next(a for a in items if str(a['id'])==uid(41))
        self.assertEqual(a['summary']['correct_count'],1)
        profile=reports.student_profile(self.db,uid(11),uid(1))
        self.assertEqual(profile['summary']['total_skills'],1)
        history=reports.attempt_history(self.db,uid(1),uid(11),skill_id='skill')
        self.assertEqual(len(history['items']),2)
        from backend.services.groups_service import get_group_detail
        group=get_group_detail(self.db,uid(21),uid(1))
        self.assertEqual(group['students'][0]['last_completed_score'],'1/2')

    def test_legacy_is_visible_but_never_restored_as_an_exact_attempt(self):
        self.db.execute("INSERT INTO responses(tenant_id,student_id,task_id,answer,correct) VALUES ('test',:sid,:tid,'42',true)",dict(sid=uid(11),tid=uid(31)))
        self.db.execute("UPDATE assignment_students SET status='completed' WHERE assignment_id=:aid",dict(aid=uid(41)))
        matrix=reports.assignment_matrix(self.db,uid(41),uid(1))
        self.assertTrue(matrix['has_legacy'])
        self.assertEqual(matrix['summary']['correct_count'],0)
        restored=assignments.get_assignment_tasks(self.db,uid(41),uid(11))
        self.assertTrue(restored[0]['has_legacy'])
        self.assertIsNone(restored[0]['previous_response'])
        self.assertEqual(responses.list_my_responses(self.db,uid(11))[0]['context'],'legacy')

    def test_student_history_titles_and_graph_attempts_match_exact_context(self):
        self.submit(answer='wrong')
        self.submit(None)
        history=responses.list_my_responses(self.db,uid(11))
        self.assertEqual(len(history),2)
        self.assertEqual([r['context'] for r in history],['practice','assignment'])
        self.assertIsNone(history[0]['assignment_title'])
        self.assertEqual(history[1]['assignment_title'],'Test 41')
        from backend.services import graph_service
        nodes=[dict(id='skill',name='Synthetic Skill'),dict(id='unknown',name='Unknown')]
        with patch.object(graph_service,'_fetch_full_graph',return_value=(nodes,[])):
            graph=graph_service.get_student_graph(self.db,uid(11))
        self.assertEqual(graph.nodes[0].attempts,2)
        self.assertEqual(graph.nodes[1].status,'unknown')

    def test_real_rls_hides_other_tenant_responses(self):
        self.submit(None)
        self.db.execute("INSERT INTO responses(tenant_id,student_id,task_id,answer,context) VALUES ('other',:sid,:tid,'42','practice')",dict(sid=uid(13),tid=uid(31)))
        self.db.execute('SET ROLE report_reader')
        try:
            rows=self.db.execute('SELECT tenant_id FROM responses').fetchall()
            self.assertEqual(rows,[('test',)])
            with self.assertRaises(ReportNotFound):
                owned_student(self.db,uid(13),uid(1))
        finally:
            self.db.execute('RESET ROLE')


if __name__=='__main__':
    unittest.main()
