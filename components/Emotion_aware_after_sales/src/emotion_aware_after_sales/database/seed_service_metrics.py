"""Idempotent, explicitly synthetic service examples for existing synthetic owners."""
import sqlite3
from pathlib import Path

def seed(path):
    path=Path(path)
    backup=path.with_name(path.name+'.before-service-metrics.bak')
    if not backup.exists():
        with sqlite3.connect(path) as source, sqlite3.connect(backup) as target: source.backup(target)
    with sqlite3.connect(path) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.executescript(Path(__file__).with_name('service_metrics_schema.sql').read_text())
        owners=conn.execute("""SELECT o.customer_id,o.device_id FROM customer_devices o
            JOIN customers c ON c.customer_id=o.customer_id JOIN devices d ON d.device_id=o.device_id
            WHERE d.serial_number LIKE 'SYNTH-V5-%'
            AND lower(trim(d.device_type)) IN ('printer','copier') ORDER BY o.customer_id,o.device_id""").fetchall()
        if not owners: raise ValueError('No synthetic printer/copier owners found; no customer records will be fabricated.')
        for i in range(6):
            customer,device=owners[i%len(owners)]
            key=f'SYNTH-SERVICE-METRICS-{i+1}'
            day=5+i
            opened=f'2026-10-{day:02}T08:00:00+05:30'
            response=f'2026-10-{day:02}T{10+i%3:02}:00:00+05:30'
            scheduled=f'2026-10-{day+1:02}T10:00:00+05:30'
            completed=f'2026-10-{day+1:02}T12:00:00+05:30' if i<3 else None
            status='Resolved' if completed else 'In progress'
            priority='High' if i==3 else 'Normal'
            conn.execute('''INSERT OR IGNORE INTO service_requests
                (request_number,customer_id,device_id,opened_at,issue_description,priority,status)
                VALUES(?,?,?,?,?,?,?)''',(key,customer,device,opened,['Paper repeatedly jams when feeding from the main tray.','Printed pages have faded text and uneven toner coverage.','Dark streaks appear on copied documents.','The printer stops during duplex printing.','Paper is feeding slowly and occasionally creases.','Black marks appear near the edge of printed pages.'][i],priority,status))
            request=conn.execute('SELECT request_id FROM service_requests WHERE request_number=?',(key,)).fetchone()[0]
            conn.execute('''INSERT OR IGNORE INTO service_visits
                (request_id,visit_key,scheduled_at,completed_at,technician_name,resolution) VALUES(?,?,?,?,?,?)''',
                (request,key,scheduled,completed,'Dhanushka Perera','Cleaned feed rollers, checked the paper path and completed a successful test print.' if completed else None))
            conn.execute('INSERT OR IGNORE INTO service_responses VALUES(?,?,1,?)',(request,response,'SYNTHETIC research example; not measured operational performance'))
        for i,(customer,device) in enumerate(owners):
            conn.execute('''INSERT OR IGNORE INTO maintenance_schedule
                (maintenance_key,customer_id,device_id,scheduled_at,status,is_synthetic,notes)
                VALUES(?,?,?,?,?,1,?)''',(f'SYNTH-MAINTENANCE-{i+1}',customer,device,
                    f'2026-10-{23+i%5:02}T10:00:00+05:30','Scheduled','Preventive maintenance: inspect paper path, clean rollers and complete test prints.'))
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()

if __name__=='__main__':
    import sys
    seed(sys.argv[1])
