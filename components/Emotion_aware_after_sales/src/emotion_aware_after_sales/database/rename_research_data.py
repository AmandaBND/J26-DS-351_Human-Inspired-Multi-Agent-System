"""Rename demo display fields while retaining identifiers and research provenance."""
import sqlite3
import sys
from pathlib import Path

NAMES=['Matheesha Imalka','Enuri Isivari','Sachith Dilshan','Dewmini Kavindya']
FIRST=['Matheesha','Enuri','Sachith','Dewmini','Nipun','Kavisha','Sahan','Ishara','Dulaj','Senuri']
LAST=['Imalka','Isivari','Wickramasinghe','Jayawardena','Rathnayake','Senanayake']
def device(kind):
    return {'Printer':('HP','LaserJet Pro M404dn'),'Copier':('Canon','imageRUNNER 2425'),
            'Scanner':('Epson','WorkForce DS-530 II')}[kind]

def apply(path,revenue=False):
    path=Path(path)
    backup=path.with_name(path.name+'.before-realistic-names.bak')
    if not backup.exists():
        with sqlite3.connect(path) as src,sqlite3.connect(backup) as dest: src.backup(dest)
    with sqlite3.connect(path) as c:
        c.execute('PRAGMA foreign_keys=ON')
        before={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t, in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if revenue:
            for id,name in c.execute("SELECT customer_id,customer_name FROM customers WHERE customer_name LIKE 'Demo Organisation %'").fetchall():
                name=FIRST[(id-1)%10]+' '+LAST[(id-1)//10]
                c.execute('UPDATE customers SET customer_name=? WHERE customer_id=?',(name,id))
            devices=c.execute("SELECT device_id,device_type FROM devices WHERE brand='Demo'").fetchall()
        else:
            for i,name in enumerate(NAMES,1):
                c.execute('UPDATE customers SET customer_name=?,email=? WHERE customer_name=?',
                          (name,name.lower().replace(' ','.')+'@example.invalid',f'SYNTHETIC Demo Customer {i}'))
            devices=c.execute("SELECT device_id,device_type FROM devices WHERE serial_number LIKE 'SYNTH-V5-%'").fetchall()
            for id,kind in devices:
                c.execute("UPDATE devices SET device_features=replace(device_features,'Illustrative: ','') WHERE device_id=?",(id,))
            issues=['Paper repeatedly jams when feeding from the main tray.',
                    'Printed pages have faded text and uneven toner coverage.',
                    'Dark streaks appear on copied documents.',
                    'The printer stops during duplex printing.',
                    'Paper is feeding slowly and occasionally creases.',
                    'Black marks appear near the edge of printed pages.']
            for i,(id,) in enumerate(c.execute("SELECT request_id FROM service_requests WHERE request_number LIKE 'SYNTH-%' ORDER BY request_id").fetchall()):
                c.execute('UPDATE service_requests SET issue_description=? WHERE request_id=?',(issues[i%len(issues)],id))
            c.execute("UPDATE service_visits SET technician_name='Kasun Wijesinghe' WHERE technician_name='SYNTHETIC Technician A'")
            c.execute("UPDATE service_visits SET technician_name='Dhanushka Perera' WHERE technician_name='SYNTHETIC Technician B'")
            c.execute("UPDATE service_visits SET resolution='Cleaned feed rollers, checked the paper path and completed a successful test print.' WHERE visit_key LIKE 'SYNTH-%' AND resolution LIKE 'SYNTHETIC:%'")
            c.execute("UPDATE maintenance_schedule SET notes='Preventive maintenance: inspect paper path, clean rollers and complete test prints.' WHERE is_synthetic=1 AND maintenance_key LIKE 'SYNTH-MAINTENANCE-%'")
            c.execute("UPDATE amc_contracts SET coverage_type='Standard service' WHERE coverage_type='Synthetic standard service'")
            c.execute("UPDATE amc_renewals SET notes='Annual maintenance contract renewal quotation' WHERE notes='SYNTHETIC illustrative quotation'")
            c.execute("UPDATE invoices SET description='Annual printer/copier maintenance contract' WHERE description='SYNTHETIC annual AMC invoice'")
            c.execute("UPDATE payments SET method='Bank transfer' WHERE method='Synthetic bank transfer'")
            # Policy and source metadata continue to identify research assumptions.
        for id,kind in devices:
            brand,model=device(kind)
            c.execute('UPDATE devices SET brand=?,model=? WHERE device_id=?',(brand,model,id))
        assert all(c.execute('SELECT count(*) FROM '+t).fetchone()[0]==n for t,n in before.items())
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        print(path.name+': display names updated; row counts and relationships preserved.')

if __name__=='__main__':
    root=Path(sys.argv[1])
    apply(root/'amc_service.db')
    apply(root/'amc_revenue_demo.db',True)
