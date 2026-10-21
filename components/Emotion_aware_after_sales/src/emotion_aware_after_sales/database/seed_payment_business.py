"""Add explicit links and idempotent payment research fixtures. Existing amounts untouched."""
import sqlite3
from pathlib import Path

def seed(path):
    path=Path(path);backup=path.with_name(path.name+'.before-payment-business.bak')
    if not backup.exists():
        with sqlite3.connect(path) as src,sqlite3.connect(backup) as dest: src.backup(dest)
    with sqlite3.connect(path) as c:
        c.execute('PRAGMA foreign_keys=ON')
        if 'contract_id' not in {r[1] for r in c.execute('PRAGMA table_info(invoices)')}:
            c.execute('ALTER TABLE invoices ADD COLUMN contract_id INTEGER REFERENCES amc_contracts(contract_id)')
        if 'risk_level' not in {r[1] for r in c.execute('PRAGMA table_info(business_factors)')}:
            c.execute("ALTER TABLE business_factors ADD COLUMN risk_level TEXT CHECK(risk_level IN ('High','Medium','Low') OR risk_level IS NULL)")
        # Original fixture request/invoice keys explicitly share one device/contract context.
        for iid,customer,device in c.execute('''SELECT i.invoice_id,i.customer_id,s.device_id FROM invoices i
            JOIN service_requests s ON s.request_number=i.invoice_number AND s.customer_id=i.customer_id
            WHERE i.invoice_number LIKE 'SYNTH-V5-%' AND i.contract_id IS NULL''').fetchall():
            links=c.execute('SELECT contract_id FROM amc_contracts WHERE customer_id=? AND device_id=?',(customer,device)).fetchall()
            if len(links)==1: c.execute('UPDATE invoices SET contract_id=? WHERE invoice_id=?',(links[0][0],iid))
        contracts=c.execute("""SELECT a.contract_id,a.customer_id FROM amc_contracts a JOIN devices d ON d.device_id=a.device_id
            WHERE d.serial_number LIKE 'SYNTH-V5-%' AND d.device_type IN ('Printer','Copier') ORDER BY a.contract_id""").fetchall()
        for i,(contract,customer) in enumerate(contracts[:4]):
            key=f'INV-2026-PB-{i+1:03}'
            c.execute('''INSERT OR IGNORE INTO invoices(invoice_number,customer_id,issued_date,due_date,amount_cents,currency,description,contract_id)
                VALUES(?,?,'2026-07-01','2026-07-31',?,'LKR','Quarterly printer/copier maintenance',?)''',
                (key,customer,(i+2)*1000000,contract))
            iid=c.execute('SELECT invoice_id FROM invoices WHERE invoice_number=?',(key,)).fetchone()[0]
            if i<2:
                c.execute("""INSERT OR IGNORE INTO payments(invoice_id,payment_reference,paid_date,amount_cents,method)
                    VALUES(?,?,'2026-08-20',?,'Bank transfer')""",(iid,f'PAY-PB-{i+1}',(i+2)*1000000))
            elif i==2:
                c.execute("""INSERT OR IGNORE INTO payments(invoice_id,payment_reference,paid_date,amount_cents,method)
                    VALUES(?,?,'2026-09-05',1000000,'Bank transfer')""",(iid,f'PAY-PB-{i+1}'))
        factors=[('Treasury payment cycle','High','Extended payment approval cycles may affect collection dates. Confirm the customer’s funding source before applying this assumption.'),
                 ('Private sector demand','Medium','Budget reviews may affect renewal timing; discuss the planned renewal with the customer.'),
                 ('Customer account performance','Low','Review invoice settlement and outstanding balances alongside service history.')]
        for i,(name,risk,notes) in enumerate(factors):
            c.execute('''INSERT OR IGNORE INTO business_factors(factor_key,customer_id,factor_name,observed_at,source,notes,risk_level)
                VALUES(?,NULL,?,'2026-10-01','Synthetic research scenario; not a verified economic assessment',?,?)''',
                (f'PAYMENT-BUSINESS-{i+1}',name,notes,risk))
        assert not c.execute('PRAGMA foreign_key_check').fetchall()

if __name__=='__main__':
    import sys
    seed(sys.argv[1])
