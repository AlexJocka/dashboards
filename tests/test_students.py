import unittest
from io import BytesIO
from unittest.mock import patch

from openpyxl import load_workbook
from analyzer import analyze_file
from app import app, DEMO_FILE
import report_store


class StudentTests(unittest.TestCase):
    def test_demo_values_and_dictionary_exclusion(self):
        result = analyze_file(DEMO_FILE.name, DEMO_FILE.read_bytes())
        self.assertEqual(result['profile'].code, 'F02A')
        self.assertTrue(result['demo'])
        records = result['students']['records']
        self.assertEqual(len(records), 7)
        self.assertEqual(sum(r['contracts'] for r in records), 138)
        self.assertEqual(sum(r['plan'] for r in records), 276)
        self.assertEqual(sum(r['studying'] for r in records), 122)
        self.assertEqual(len({r['university'] for r in records}), 3)

    def test_blank_and_zero_are_distinct(self):
        workbook = load_workbook(DEMO_FILE)
        sheet = workbook.active
        sheet['M8'] = None
        sheet['Q8'] = 0
        sheet['J9'] = '1 234,0'
        sheet['R9'] = -2
        output = BytesIO()
        workbook.save(output)
        result = analyze_file('test.xlsx', output.getvalue())
        first, second = result['students']['records'][:2]
        self.assertIsNone(first['contracts'])
        self.assertEqual(first['employed'], 0)
        self.assertEqual(second['plan'], 1234)
        self.assertIsNone(second['terminated'])
        self.assertTrue(result['warnings'])

    def test_demo_survives_refresh_and_is_session_scoped(self):
        client = app.test_client()
        self.assertEqual(client.post('/demo').status_code, 302)
        for _ in range(2):
            response = client.get('/dashboards')
            self.assertEqual(response.status_code, 200)
            self.assertIn('Зафарова_демо.xlsx'.encode(), response.data)
            self.assertIn(b'"contracts": 23.0', response.data)
        self.assertNotIn(b'"contracts": 23.0', app.test_client().get('/dashboards').data)

    def test_upload_passes_data_to_dashboard(self):
        client = app.test_client()
        response = client.post('/', data={'files': [(BytesIO(DEMO_FILE.read_bytes()), 'uploaded.xlsx')]}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'uploaded.xlsx', response.data)
        self.assertIn(b'"contracts": 23.0', response.data)

    def test_download_is_excel(self):
        response = app.test_client().get('/demo/download')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, DEMO_FILE.read_bytes())
        response.close()

    def test_expired_report_is_removed(self):
        with patch('report_store.monotonic', return_value=100):
            key = report_store.save(['report'])
        with patch('report_store.monotonic', return_value=100+report_store.TTL+1):
            self.assertEqual(report_store.get(key), [])

    def test_odk_navigation_and_assets(self):
        client = app.test_client()
        client.post('/demo')
        for path in ('/', '/dashboards', '/summary', '/training', '/data-quality'):
            response = client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn('КОНТУР РАЗВИТИЯ'.encode(), response.data)
        for path in ('/static/images/odk-logo-full.png', '/static/css/01-design-tokens.css', '/static/dashboard.css'):
            response = client.get(path)
            self.assertEqual(response.status_code, 200, path)
            response.close()

    def test_quality_and_summary_use_loaded_report(self):
        client = app.test_client()
        client.post('/demo')
        for path in ('/summary', '/data-quality'):
            self.assertIn(DEMO_FILE.name.encode(), client.get(path).data)
        self.assertNotIn(DEMO_FILE.name.encode(), client.get('/training').data)
