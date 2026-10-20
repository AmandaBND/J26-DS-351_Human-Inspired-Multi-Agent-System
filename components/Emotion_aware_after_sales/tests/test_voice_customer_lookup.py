import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'src'))
from emotion_aware_after_sales.services import voice_customer_service as module


class CustomerLookupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'test.db'
        source = sqlite3.connect((PROJECT / 'data/amc_service.db').as_uri() + '?mode=ro', uri=True)
        with closing(sqlite3.connect(self.path)) as target:
            source.backup(target)
        source.close()
        self.service = module.VoiceCustomerService(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_lookup_and_parameter_binding(self):
        customers = self.service.list_customers()
        self.assertTrue(customers)
        self.assertEqual(self.service.list_devices("1 OR 1=1"), [])
        self.assertEqual(self.service.contracts("1 OR 1=1", 1), [])
        for customer in customers:
            for device in self.service.list_devices(customer['customer_id']):
                self.assertEqual(device['customer_id'], customer['customer_id'])

    def test_multiple_single_and_no_devices(self):
        counts = [len(self.service.list_devices(c['customer_id'])) for c in self.service.list_customers()]
        self.assertIn(1, counts)
        self.assertTrue(any(n > 1 for n in counts))
        self.assertEqual(self.service.list_devices(-1), [])

    def test_association_is_persistent_and_idempotent(self):
        customer = self.service.list_customers()[0]['customer_id']
        device = self.service.list_devices(customer)[0]['device_id']
        recording = self.service.associate_recording(customer, device, b'call audio')
        self.assertEqual(recording, self.service.associate_recording(customer, device, b'call audio'))
        with closing(sqlite3.connect(self.path)) as conn:
            row = conn.execute('SELECT customer_id,device_id,sha256,file_path FROM call_recordings WHERE recording_id=?', (recording,)).fetchone()
        self.assertEqual(row[:2], (customer, device))
        self.assertEqual(len(row[2]), 64)
        self.assertIsNone(row[3])

    def test_backend_rejects_wrong_owner(self):
        customers = self.service.list_customers()
        owner = customers[0]['customer_id']
        other = customers[1]['customer_id']
        device = self.service.list_devices(owner)[0]['device_id']
        with self.assertRaises(ValueError):
            self.service.associate_recording(other, device, b'call audio')

    def test_context_changes_clear_audio_roles_and_analysis(self):
        for context in ((2, 4), (1, 5), (None, None)):
            state = dict.fromkeys(module.ANALYSIS_KEYS + ('customer_call_audio',), 'stale')
            state['voice_customer_context'] = (1, 4)
            module.reset_customer_context(state, context)
            self.assertEqual(state, {'voice_customer_context': context})
        state = {'voice_customer_context': (1, 4), 'analysis_results': 'keep'}
        module.reset_customer_context(state, (1, 4))
        self.assertEqual(state['analysis_results'], 'keep')


if __name__ == '__main__':
    unittest.main()
