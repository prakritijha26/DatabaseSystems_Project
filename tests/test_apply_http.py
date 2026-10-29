"""Permanent writes must not accept cross-origin browser submissions."""
import io
import json
import unittest
from unittest.mock import patch
from wsgiref.util import setup_testing_defaults
import app


@unittest.skipUnless(app.USE_BOTTLE, 'Bottle unavailable')
class OriginTests(unittest.TestCase):
    def test_cross_origin_and_non_json_never_execute(self):
        for origin, content_type, expected in [('https://untrusted.example', 'application/json', '403'),
                                                ('', 'text/plain', '415'),
                                                ('http://127.0.0.1:8000', 'application/json', '200')]:
            env = {}; setup_testing_defaults(env)
            body = json.dumps({'sql': 'RESEED;'}).encode()
            env.update(PATH_INFO='/api/whatif', REQUEST_METHOD='POST', CONTENT_TYPE=content_type,
                       CONTENT_LENGTH=str(len(body)), HTTP_HOST='127.0.0.1:8000', HTTP_ORIGIN=origin)
            env['wsgi.input'] = io.BytesIO(body)
            statuses = []
            with patch.object(app, 'run_whatif', return_value={'status': 'COMMITTED'}) as run:
                list(app.create_bottle_app()(env, lambda status, headers, exc_info=None: statuses.append(status)))
                self.assertTrue(statuses[0].startswith(expected), statuses)
                self.assertEqual(run.call_count, 1 if expected == '200' else 0)
