"""Transaction boundary and offline-scope checks for explicit APPLY and reset."""
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
venv_site = ROOT / '.venv' / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
if venv_site.exists() and str(venv_site) not in sys.path:
    sys.path.insert(0, str(venv_site))

import app
import mock_engine
try:
    import engine
except ModuleNotFoundError:
    engine = None


@unittest.skipIf(engine is None, 'Install psycopg and sqlglot for transaction tests')
class ApplyEngineTests(unittest.TestCase):
    def transaction(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        events = []
        conn = Mock()
        conn.execute.side_effect = lambda statement, *args, **kwargs: (events.append(str(statement)), Mock(rowcount=1))[1]
        conn.commit.side_effect = lambda: events.append('COMMIT')
        conn.rollback.side_effect = lambda: events.append('ROLLBACK')
        stack.enter_context(patch.object(engine, 'connect_database', return_value=conn))
        counts = stack.enter_context(patch.object(engine, 'get_metrics', side_effect=lambda c: (events.append('COUNTS'), {'marks': 1})[1]))
        academic = stack.enter_context(patch.object(engine, 'get_academic_metrics', side_effect=lambda c: (events.append('ACADEMIC'), {})[1]))
        stack.enter_context(patch.object(engine, 'find_broken_dependencies', return_value=[]))
        return conn, events, counts, academic

    def test_apply_validation_accepts_bounded_dml_and_drop(self):
        for sql in ('APPLY UPDATE marks SET score=45 WHERE enrollment_id=1;',
                    'APPLY DELETE FROM attendance WHERE enrollment_id=1;',
                    'APPLY INSERT INTO marks (mark_id,enrollment_id,score) VALUES (999,1,60);',
                    'APPLY ALTER TABLE marks DROP COLUMN score;'):
            with self.subTest(sql=sql):
                result = engine.validate_statement(sql)
                self.assertTrue(result)

    def test_apply_rejects_escapes_before_connecting(self):
        for sql in ('UPDATE marks SET score=45;', 'APPLY COMMIT;', 'APPLY ROLLBACK;',
                    'APPLY BEGIN;', 'APPLY DELETE FROM marks; COMMIT;',
                    'APPLY WITH x AS (DELETE FROM marks RETURNING *) SELECT * FROM x;',
                    'APPLY ALTER TABLE marks DROP COLUMN score CASCADE;'):
            with self.subTest(sql=sql), patch.object(engine, 'connect_database') as connect:
                with self.assertRaises(ValueError):
                    engine.run_whatif(sql)
                connect.assert_not_called()

    def test_apply_commits_once_after_all_metrics(self):
        conn, events, counts, academic = self.transaction()
        result = engine.run_whatif('APPLY UPDATE marks SET score=45 WHERE enrollment_id=1;')
        self.assertTrue(result['committed'])
        self.assertFalse(result['rolled_back'])
        self.assertEqual(counts.call_count, 2)
        self.assertEqual(academic.call_count, 2)
        self.assertEqual(events[-1], 'COMMIT')
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    def test_apply_metric_failure_rolls_back_without_commit(self):
        conn, _, counts, _ = self.transaction()
        counts.side_effect = [{'marks': 1}, RuntimeError('after metrics failed')]
        with self.assertRaisesRegex(RuntimeError, 'after metrics failed'):
            engine.run_whatif('APPLY UPDATE marks SET score=45;')
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    def test_apply_commit_failure_rolls_back_and_propagates(self):
        conn, _, _, _ = self.transaction()
        conn.commit.side_effect = RuntimeError('commit failed')
        with self.assertRaisesRegex(RuntimeError, 'commit failed'):
            engine.run_whatif('APPLY UPDATE marks SET score=45;')
        conn.commit.assert_called_once()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    def test_whatif_still_always_rolls_back(self):
        conn, _, _, _ = self.transaction()
        result = engine.run_whatif('WHAT_IF UPDATE marks SET score=45;')
        self.assertTrue(result['rolled_back'])
        self.assertFalse(result.get('committed', False))
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()

    def test_apply_ddl_does_not_undo_change_before_commit(self):
        conn, events, _, _ = self.transaction()
        result = engine.run_whatif('APPLY ALTER TABLE marks DROP COLUMN score;')
        self.assertTrue(result['committed'])
        self.assertEqual(result['ddl_mode'], 'RESTRICT')
        self.assertFalse(any('ROLLBACK TO' in sql or 'CASCADE' in sql for sql in events))
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    def test_apply_ddl_dependency_error_never_expands_cascade(self):
        conn, events, _, _ = self.transaction()
        def execute(statement, *args, **kwargs):
            sql = str(statement)
            events.append(sql)
            if 'ALTER TABLE' in sql:
                raise engine.psycopg.errors.DependentObjectsStillExist('dependent view')
            return Mock(rowcount=0)
        conn.execute.side_effect = execute
        with self.assertRaises(engine.psycopg.errors.DependentObjectsStillExist):
            engine.run_whatif('APPLY ALTER TABLE marks DROP COLUMN score;')
        self.assertFalse(any('CASCADE' in sql for sql in events))
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()

    def test_reset_and_reseed_rebuild_schema_and_seed_atomically(self):
        for command in ('RESET;', 'RESEED;'):
            with self.subTest(command=command):
                conn, events, _, _ = self.transaction()
                result = engine.run_whatif(command)
                self.assertTrue(result['committed'])
                executed = '\n'.join(events).upper()
                self.assertIn('CREATE TABLE', executed)
                self.assertIn('INSERT INTO', executed)
                self.assertEqual(events[-1], 'COMMIT')
                conn.commit.assert_called_once()
                conn.rollback.assert_not_called()
                conn.close.assert_called_once()

    def test_reseed_failure_rolls_back_schema_and_seed(self):
        conn, _, _, _ = self.transaction()
        def execute(statement, *args, **kwargs):
            if 'INSERT INTO' in str(statement).upper():
                raise RuntimeError('seed failed')
            return Mock(rowcount=0)
        conn.execute.side_effect = execute
        with self.assertRaisesRegex(RuntimeError, 'seed failed'):
            engine.run_whatif('RESEED;')
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()


class ApplyAdapterTests(unittest.TestCase):
    def test_confirmed_commit_is_success_without_rollback(self):
        report = app.normalize_report('APPLY UPDATE marks SET score=45;',
                                      {'committed': True, 'rolled_back': False}, 1.5)
        self.assertEqual(report['status'], 'COMMITTED')
        self.assertTrue(report['committed'])
        self.assertFalse(report['rolled_back'])
        self.assertNotIn('error_message', report)

    def test_mock_apply_is_explicitly_fixture_scoped(self):
        report = mock_engine.run_whatif('APPLY UPDATE marks SET score=45 WHERE enrollment_id=1;')
        self.assertEqual(report['status'], 'COMMITTED')
        self.assertTrue(report['committed'])
        self.assertEqual(report['commit_scope'], 'mock')
        self.assertFalse(report.get('rolled_back', False))
        self.assertNotIn('BEGIN ISOLATION LEVEL', '\n'.join(report['logs']))
        self.assertNotIn('Issued ROLLBACK', '\n'.join(report['logs']))

    def test_adapter_preserves_mock_commit_scope(self):
        with patch.object(app, 'live_run_whatif', None), patch.dict('os.environ', {'WHATIF_REQUIRE_LIVE': '0'}):
            report = app.run_whatif('APPLY UPDATE marks SET score=45 WHERE enrollment_id=1;')
        self.assertEqual(report['status'], 'COMMITTED')
        self.assertEqual(report['engine_backend'], 'mock')
        self.assertEqual(report['commit_scope'], 'mock')
        self.assertTrue(report['committed'])
        self.assertFalse(report['rolled_back'])


if __name__ == '__main__':
    unittest.main()
