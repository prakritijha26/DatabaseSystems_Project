"""Run with python3 -m unittest discover -s tests.
Engine lifecycle tests additionally require psycopg and sqlglot.
"""
import io
import json
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

import app


class AdapterTests(unittest.TestCase):
    def setUp(self):
        mode = patch.dict("os.environ", {"WHATIF_REQUIRE_LIVE": "0"})
        mode.start()
        self.addCleanup(mode.stop)

    def test_updates_use_rowcount_and_do_not_count_read_only_tables(self):
        report = app.normalize_report('WHAT_IF UPDATE marks ...', {
            'before': {'marks': 10, 'students': 5}, 'after': {'marks': 10, 'students': 5},
            'tables_affected': ['marks', 'students'], 'target_table': 'marks',
            'rows_affected': 3, 'operation': 'UPDATE', 'rolled_back': True}, 12.5)
        self.assertEqual(report['tables_affected'], [{'table': 'marks', 'rows_changed': 3, 'action': 'UPDATED'}])
        self.assertEqual(report['execution_time_ms'], 12.5)
        self.assertTrue(report['rolled_back'])

    def test_cascade_and_missing_academic_rows(self):
        report = app.normalize_report('WHAT_IF DELETE ...', {
            'before': {'enrollments': 2, 'attendance': 2}, 'after': {'enrollments': 1, 'attendance': 1},
            'tables_affected': ['enrollments'], 'target_table': 'enrollments',
            'rows_affected': 1, 'operation': 'DELETE', 'rolled_back': True,
            'academic_before': {'performance': [{'student_id': 1001, 'weighted_average_score': Decimal('80.5')}]},
            'academic_after': {'performance': []}}, 0)
        self.assertEqual(sum(t['rows_changed'] for t in report['tables_affected']), 2)
        self.assertEqual(report['metrics'][0]['after'], 'UNAVAILABLE')
        self.assertEqual(report['metrics'][0]['metric'], 'weighted_average_score')
        json.dumps(report)

    def test_connection_failure_falls_back_but_execution_errors_do_not(self):
        with patch.object(app, 'live_run_whatif', side_effect=ConnectionError):
            report = app.run_whatif('WHAT_IF DELETE FROM attendance WHERE student_id = 1042;')
            self.assertEqual(report['engine_backend'], 'mock')
            self.assertFalse(report['rolled_back'])
            self.assertNotIn('Live tables', ' '.join(report['logs']))
        for error in (ValueError('Rejected'), RuntimeError('database failure')):
            with patch.object(app, 'live_run_whatif', side_effect=error), patch.object(app, 'mock_run_whatif') as mock:
                self.assertEqual(app.run_whatif('WHAT_IF COMMIT;')['status'], 'ERROR')
                mock.assert_not_called()

    def test_missing_driver_fallback(self):
        with patch.object(app, 'live_run_whatif', None):
            self.assertEqual(app.run_whatif('WHAT_IF COMMIT;')['status'], 'ERROR')
            self.assertEqual(app.run_whatif('WHAT_IF UPDATE marks SET score=45;')['engine_backend'], 'mock')

    def test_no_rollback_is_never_success(self):
        self.assertEqual(app.normalize_report('sql', {'rolled_back': False}, 0)['status'], 'ERROR')

    @unittest.skipUnless(app.USE_BOTTLE, 'Bottle not installed')
    def test_http_contract_and_invalid_request(self):
        from wsgiref.util import setup_testing_defaults
        application = app.create_bottle_app()
        for data, expected_status in [({'sql': 'WHAT_IF COMMIT;'}, '200'), ({'sql': 42}, '400'), ([], '400')]:
            environ = {}; setup_testing_defaults(environ)
            payload = json.dumps(data).encode()
            environ.update(PATH_INFO='/api/whatif', REQUEST_METHOD='POST', CONTENT_TYPE='application/json', CONTENT_LENGTH=str(len(payload)))
            environ['wsgi.input'] = io.BytesIO(payload)
            statuses = []
            with patch.object(app, 'live_run_whatif', None):
                body = b''.join(application(environ, lambda status, headers, exc_info=None: statuses.append(status)))
            self.assertTrue(statuses[0].startswith(expected_status))
            report = json.loads(body)
            self.assertIn('metrics', report)
            self.assertEqual(report['status'], 'ERROR')


import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
venv_site = ROOT / '.venv' / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
if venv_site.exists() and str(venv_site) not in sys.path:
    sys.path.insert(0, str(venv_site))

try:
    import engine
except ModuleNotFoundError:
    engine = None


@unittest.skipIf(engine is None, 'Install psycopg and sqlglot to test live engine lifecycle')
class EngineTests(unittest.TestCase):
    def test_password_snapshot_and_finally_rollback(self):
        conn = Mock(); conn.execute.return_value.rowcount = 2
        with patch.object(engine.psycopg, 'connect', return_value=conn) as connect, patch.object(engine, 'get_metrics', return_value={'marks': 2}), patch.object(engine, 'get_academic_metrics', return_value={}), patch.dict('os.environ', {'PGPASSWORD': 'test-password'}):
            raw = engine.run_whatif('WHAT_IF UPDATE marks SET score = 45 WHERE enrollment_id = 1;')
        self.assertEqual(connect.call_args.kwargs['password'], 'test-password')
        self.assertEqual(conn.execute.call_args_list[0].args[0], 'BEGIN ISOLATION LEVEL REPEATABLE READ')
        self.assertTrue(raw['rolled_back']); self.assertEqual(raw['target_table'], 'marks')
        conn.rollback.assert_called_once(); conn.close.assert_called_once()

    def test_errors_in_baseline_execution_or_recomputation_always_rollback(self):
        for phase in ('baseline', 'execute', 'after', 'rollback'):
            conn = Mock(); conn.execute.return_value.rowcount = 1
            counts = [RuntimeError('baseline')] if phase == 'baseline' else [{'marks': 2}, RuntimeError('after')] if phase == 'after' else [{'marks': 2}, {'marks': 2}]
            if phase == 'execute':
                def execute(statement):
                    if str(statement).startswith('UPDATE'):
                        raise RuntimeError('execute')
                    return Mock(rowcount=1)
                conn.execute.side_effect = execute
            if phase == 'rollback': conn.rollback.side_effect = RuntimeError('rollback')
            with patch.object(engine.psycopg, 'connect', return_value=conn), patch.object(engine, 'get_metrics', side_effect=counts), patch.object(engine, 'get_academic_metrics', return_value={}):
                with self.assertRaises(RuntimeError): engine.run_whatif('WHAT_IF UPDATE marks SET score = 45;')
            conn.rollback.assert_called_once(); conn.close.assert_called_once()

    def test_validation_precedes_connection(self):
        for sql in ('WHAT_IF COMMIT;', 'WHAT_IF DELETE FROM marks; COMMIT;', 'WHAT_IF ALTER TABLE marks ADD COLUMN bad INT;', 'WHAT_IF DELETE FROM other_table;'):
            with patch.object(engine.psycopg, 'connect') as connect:
                with self.assertRaises(ValueError): engine.run_whatif(sql)
                connect.assert_not_called()

    def test_only_connect_errors_become_connection_errors(self):
        with patch.object(engine.psycopg, 'connect', side_effect=engine.psycopg.OperationalError('offline')):
            with self.assertRaises(ConnectionError): engine.run_whatif('WHAT_IF DELETE FROM marks;')


if __name__ == '__main__':
    unittest.main()
