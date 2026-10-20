"""Customer context and recording associations for the voice dashboard."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib

from emotion_aware_after_sales.database.setup_database import get_connection


ANALYSIS_KEYS = (
    'speaker_review_turns', 'verified_speaker_turns', 'speaker_role_editor',
    'analysis_results', 'role_scores', 'role_margin', 'review_identity',
    'role_review_confirmed', 'confirmed_agent_speaker', 'review_agent_speaker',
    'active_audio_identity', 'voice_recording_id',
)


def reset_customer_context(state, context):
    if state.get('voice_customer_context') != context:
        for key in ANALYSIS_KEYS + ('customer_call_audio',):
            state.pop(key, None)
        state['voice_customer_context'] = context


class VoiceCustomerService:
    def __init__(self, database_path=None):
        self.database_path = database_path

    def list_customers(self):
        with closing(get_connection(self.database_path)) as conn:
            return [dict(r) for r in conn.execute(
                'SELECT customer_id, customer_name FROM customers ORDER BY customer_id')]

    def list_devices(self, customer_id):
        with closing(get_connection(self.database_path)) as conn:
            return [dict(r) for r in conn.execute('''
                SELECT cd.customer_id, cd.device_id, cd.purchase_date,
                       cd.warranty_start_date, cd.warranty_end_date,
                       d.device_type, d.brand, d.model, d.serial_number
                FROM customer_devices cd JOIN devices d ON d.device_id=cd.device_id
                WHERE cd.customer_id=? ORDER BY cd.device_id
            ''', (customer_id,))]

    def contracts(self, customer_id, device_id):
        with closing(get_connection(self.database_path)) as conn:
            return [dict(r) for r in conn.execute('''
                SELECT contract_id, start_date, end_date, contract_status, coverage_type
                FROM amc_contracts WHERE customer_id=? AND device_id=?
                ORDER BY end_date DESC, contract_id DESC
            ''', (customer_id, device_id))]

    def associate_recording(self, customer_id, device_id, audio_bytes):
        digest = hashlib.sha256(audio_bytes).hexdigest()
        key = f'voice:{customer_id}:{device_id}:{digest}'
        with closing(get_connection(self.database_path)) as conn, conn:
            # Validate within the write transaction, including repeated uploads.
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('''SELECT 1 FROM customer_devices
                    WHERE customer_id=? AND device_id=?''',
                    (customer_id, device_id)).fetchone() is None:
                raise ValueError('The selected device does not belong to this customer.')
            conn.execute('''INSERT INTO call_recordings
                (recording_key, customer_id, device_id, recorded_at, sha256)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT(recording_key) DO NOTHING''',
                (key, customer_id, device_id, datetime.now(timezone.utc).isoformat(), digest))
            return conn.execute('SELECT recording_id FROM call_recordings WHERE recording_key=?',
                                (key,)).fetchone()['recording_id']
