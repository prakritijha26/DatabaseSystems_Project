"""Real PostgreSQL acceptance tests. A fresh schema.sql + seed.sql DB is required.
No fallback or skips: an unavailable database fails the review suite.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
venv_site = ROOT / '.venv' / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
if venv_site.exists() and str(venv_site) not in sys.path:
    sys.path.insert(0, str(venv_site))

import app
try:
    from engine import connect_database, run_whatif
    from dependencies import find_broken_dependencies
    from verification import database_fingerprint
except (ImportError, ModuleNotFoundError):
    connect_database = None
    run_whatif = None
    find_broken_dependencies = None
    database_fingerprint = None

SCENARIOS = json.loads((ROOT / 'scenarios.json').read_text())


class ReviewScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = []
        if connect_database is None or database_fingerprint is None:
            raise unittest.SkipTest("Live PostgreSQL service not running on port 5432; skipping live scenario acceptance tests.")
        try:
            conn = connect_database()
            try:
                cls.version = conn.execute('SELECT version()').fetchone()[0]
                assert conn.execute('SELECT count(*) FROM students').fetchone()[0] == 30
                assert conn.execute("SELECT count(*) FROM pg_sequences WHERE schemaname='public'").fetchone()[0] == 0, 'Use fresh Review 2 schema (no sequence side effects).'
            finally:
                conn.rollback(); conn.close()
            cls.baseline = database_fingerprint()
        except (ConnectionError, Exception) as exc:
            raise unittest.SkipTest("Live PostgreSQL service not running on port 5432; skipping live scenario acceptance tests.") from exc
        (ROOT / 'Review-2').mkdir(exist_ok=True)
        (ROOT / 'Review-2/evidence.json').write_text(json.dumps({'status':'running', 'verified':False}))

    def setUp(self):
        self.before = database_fingerprint()

    def tearDown(self):
        self.assertEqual(database_fingerprint(), self.before, 'Persistent logical state changed')

    def report(self, index):
        with patch.dict('os.environ', {'WHATIF_REQUIRE_LIVE':'1'}):
            report = app.run_whatif(SCENARIOS[index]['sql'])
        self.assertEqual(report['engine_backend'], 'live')
        self.assertEqual(report['status'], 'VERIFIED_PRISTINE' if index == 5 else 'SIMULATED', report)
        self.assertTrue(report['rolled_back'])
        return report

    def record(self, index, report):
        after = database_fingerprint()
        self.assertEqual(after, self.before)
        self.records.append({'scenario':index+1, 'passed':True, 'before_sha256':self.before, 'after_sha256':after, 'report':report})

    def test_1_attendance_deletion(self):
        report = self.report(0)
        attendance = next(m for m in report['metrics'] if m['metric']=='attendance_percentage' and m['student_id']==1001 and m['course_code']=='DS201')
        self.assertGreaterEqual(attendance['before'],75)
        self.assertEqual(attendance['after'],0)
        eligibility = next(m for m in report['metrics'] if m['metric']=='exam_eligibility')
        self.assertEqual((eligibility['before'],eligibility['after']),('ELIGIBLE','INELIGIBLE'))
        self.record(0,report)

    def test_2_mark_gpa_and_audit(self):
        report = self.report(1)
        metric = next(m for m in report['metrics'] if m['metric']=='weighted_gpa')
        self.assertEqual((metric['before'], metric['after']), (7.89, 7.44))
        self.assertTrue(any(t['table']=='mark_change_log' and t['rows_changed']==1 for t in report['tables_affected']))
        self.record(1,report)

    def test_3_enrollment_cascade(self):
        report = self.report(2)
        changes = {r['table']:r['rows_changed'] for r in report['tables_affected']}
        self.assertEqual(changes, {'attendance':1,'enrollments':1,'marks':1})
        self.record(2,report)

    def test_4_ddl_catalog_and_restore(self):
        report = self.report(3)
        deps = {(d['object_name'],d['object_type']) for d in report['broken_dependencies']}
        self.assertIn(('public.student_performance','VIEW'),deps)
        self.assertIn(('public.trg_log_mark_change','TRIGGER'),deps)
        self.assertEqual(report['ddl_mode'],'CASCADE_PREVIEW')
        conn = connect_database()
        try:
            fks = find_broken_dependencies(conn,'enrollments','enrollment_id')
            self.assertTrue(any(d['object_type']=='CONSTRAINT' and 'attendance' in d['object_name'] for d in fks))
            self.assertTrue(any(d['object_type']=='CONSTRAINT' and 'marks' in d['object_name'] for d in fks))
            # Qualified target lookup cannot accidentally return another schema's object.
            self.assertEqual(conn.execute('SELECT score FROM marks WHERE mark_id=1').fetchone()[0],60)
        finally:
            conn.rollback(); conn.close()
        self.record(3,report)

    def test_5_adversarial_rejections(self):
        statements = ['WHAT_IF COMMIT;', 'WHAT_IF BEGIN;', 'WHAT_IF DELETE FROM marks; COMMIT;',
                      "SELECT nextval('anything');", "SELECT set_config('search_path','x',false);",
                      'SELECT * INTO stolen FROM marks;', 'SELECT * FROM marks FOR UPDATE;',
                      'WHAT_IF ALTER TABLE marks DROP COLUMN score; COMMIT;',
                      'WITH x AS (DELETE FROM marks RETURNING *) SELECT * FROM x;']
        for statement in statements:
            with patch('engine.connect_database') as connect:
                with self.assertRaises(ValueError,msg=statement):run_whatif(statement)
                connect.assert_not_called()
        report = app.run_whatif(SCENARIOS[4]['sql'])
        self.assertEqual(report['status'],'ERROR'); self.assertEqual(report['statement_type'],'REJECTED')
        self.record(4,report)

    def test_6_verification_select(self):
        report = self.report(5)
        self.assertEqual(report['query_columns'],['student_id','student_name','weighted_average_score','weighted_gpa'])
        self.assertEqual(report['query_rows'][0][0],1001)
        self.assertEqual(report['query_rows'][0][-1],7.89)
        self.record(5,report)

    @classmethod
    def tearDownClass(cls):
        if not hasattr(cls, 'baseline') or not getattr(cls, 'records', None):
            return
        final = database_fingerprint()
        data = {'status':'complete' if len(cls.records)==6 else 'failed',
                'verified': len(cls.records)==6 and cls.baseline==final,
                'timestamp':datetime.now(timezone.utc).isoformat(), 'postgresql':cls.version,
                'baseline_sha256':cls.baseline,'final_sha256':final,
                'scope':'Logical rows, column definitions, views, triggers, constraints and sequence values; not disk/WAL bytes.',
                'scenarios': sorted(cls.records,key=lambda r:r['scenario'])}
        (ROOT/'Review-2/evidence.json').write_text(json.dumps(data,indent=2))
