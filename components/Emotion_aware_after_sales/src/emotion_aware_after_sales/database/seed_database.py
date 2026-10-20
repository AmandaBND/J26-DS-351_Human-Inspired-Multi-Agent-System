"""Add explicitly synthetic dashboard fixtures once; never reset or overwrite data."""
import argparse
from pathlib import Path
try:
    from .setup_database import initialize_database, get_connection, DATABASE_PATH, FEATURES
except ImportError:
    from setup_database import initialize_database, get_connection, DATABASE_PATH, FEATURES

def seed_database(path=None, reset_demo=False):
    if reset_demo:
        raise ValueError('Reset is disabled: use a separate demo database')
    initialize_database(path)
    c = get_connection(path)
    try:
        c.execute('BEGIN IMMEDIATE')
        c.execute('CREATE TABLE IF NOT EXISTS synthetic_seed_batches(batch_key TEXT PRIMARY KEY, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
        if c.execute("SELECT 1 FROM synthetic_seed_batches WHERE batch_key='dashboard-v5'").fetchone():
            c.rollback()
            return
        if c.execute("SELECT 1 FROM devices WHERE serial_number LIKE 'SYNTH-V5-%'").fetchone():
            raise ValueError('Synthetic namespace collision; no fixtures saved')
        for i in range(1,5):
            customer = None
            for j in range(2 if i<4 else 1):
                kind = ('Printer','Copier','Scanner')[(i+j-1)%3]
                device = c.execute('INSERT INTO devices(device_type,brand,model,serial_number,device_features,warranty_period_months) VALUES(?,?,?,?,?,?)',
                    (kind,{'Printer':'HP','Copier':'Canon','Scanner':'Epson'}[kind],{'Printer':'LaserJet Pro M404dn','Copier':'imageRUNNER 2425','Scanner':'WorkForce DS-530 II'}[kind],f'SYNTH-V5-{i}-{j}',FEATURES[kind],12)).lastrowid
                if customer is None:
                    customer = c.execute('INSERT INTO customers(customer_name,email,device_id,purchase_date,warranty_start_date,warranty_end_date) VALUES(?,?,?,?,?,?)',
                        (['Matheesha Imalka','Enuri Isivari','Sachith Dilshan','Dewmini Kavindya'][i-1],f'demo-v5-{i}@example.invalid',device,'2025-10-01','2025-10-01','2026-09-30')).lastrowid
                else:
                    c.execute('INSERT INTO customer_devices VALUES(?,?,?,?,?)',(customer,device,'2026-03-01','2026-03-01','2027-02-28'))
                key = f'SYNTH-V5-{i}-{j}'
                contract = c.execute('INSERT INTO amc_contracts(customer_id,device_id,start_date,end_date,contract_status,coverage_type) VALUES(?,?,?,?,?,?)',
                    (customer,device,'2026-10-01','2027-09-30','Active','Standard service')).lastrowid
                c.execute('INSERT INTO amc_renewals(contract_id,renewal_key,due_date,quoted_amount_cents,status,notes) VALUES(?,?,?,?,?,?)',
                    (contract,key,'2027-09-30',2400000,'Pending','Annual maintenance contract renewal quotation'))
                invoice = c.execute('INSERT INTO invoices(invoice_number,customer_id,issued_date,due_date,amount_cents,description) VALUES(?,?,?,?,?,?)',
                    (key,customer,'2026-10-01','2026-10-31',2400000,'Annual printer/copier maintenance contract')).lastrowid
                if i%2:
                    c.execute('INSERT INTO payments(invoice_id,payment_reference,paid_date,amount_cents,method) VALUES(?,?,?,?,?)',(invoice,key,'2026-10-10',1200000,'Bank transfer'))
                request = c.execute('INSERT INTO service_requests(request_number,customer_id,device_id,opened_at,issue_description,priority,status) VALUES(?,?,?,?,?,?,?)',
                    (key,customer,device,'2026-10-15T09:00:00+05:30',f'{kind}: paper feed or image quality issue','Normal','Scheduled')).lastrowid
                c.execute('INSERT INTO service_visits(request_id,visit_key,scheduled_at,technician_name) VALUES(?,?,?,?)',(request,key,'2026-10-22T10:00:00+05:30','Kasun Wijesinghe'))
                recording = c.execute('INSERT INTO call_recordings(recording_key,customer_id,device_id,recorded_at,duration_seconds,is_synthetic) VALUES(?,?,?,?,?,1)',
                    (key,customer,device,'2026-10-15T09:00:00+05:30',60)).lastrowid
                c.execute('INSERT INTO emotion_segments(recording_id,start_seconds,end_seconds,speaker_role,emotion,confidence,model_version) VALUES(?,0,20,?,?,?,?)',
                    (recording,'customer','neutral',0.72,'SYNTHETIC example; no inference performed'))
            c.execute('INSERT INTO business_factors(factor_key,customer_id,factor_name,numeric_value,unit,observed_at,source) VALUES(?,?,?,?,?,?,?)',
                (f'SYNTH-V5-{i}',customer,'Monthly page volume',3000*i,'pages','2026-10-01','SYNTHETIC demonstration assumption'))
        doc = c.execute('INSERT INTO policy_documents(document_key,title,version,is_synthetic) VALUES(?,?,?,1)',('SYNTH-V5','SYNTHETIC AMC policy example','demo-1')).lastrowid
        c.execute('INSERT INTO policy_chunks(document_id,chunk_index,content) VALUES(?,0,?)',(doc,'SYNTHETIC example: verify device ownership and coverage before service scheduling. Not an actual business policy.'))
        # No fabricated agent runs, findings, recommendations, audio files, or embeddings.
        if c.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Seed foreign key validation failed')
        c.execute("INSERT INTO synthetic_seed_batches(batch_key) VALUES('dashboard-v5')")
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--database',type=Path,default=DATABASE_PATH)
    seed_database(p.parse_args().database)
