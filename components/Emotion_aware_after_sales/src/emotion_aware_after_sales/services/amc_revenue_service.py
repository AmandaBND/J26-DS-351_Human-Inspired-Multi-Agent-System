"""Isolated synthetic AMC revenue ledger. No production/customer DB mutations.

Run with --database PATH --seed to create the deterministic 2023–2026 demo.
"""
from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

DEMO_AS_OF = date(2026, 10, 20)
SCHEMA = '''
CREATE TABLE IF NOT EXISTS demo_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers(customer_id INTEGER PRIMARY KEY, customer_name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS devices(device_id INTEGER PRIMARY KEY, device_type TEXT NOT NULL CHECK(device_type IN ('Printer','Copier')), brand TEXT NOT NULL, model TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customer_devices(customer_id INTEGER NOT NULL REFERENCES customers, device_id INTEGER NOT NULL UNIQUE REFERENCES devices, PRIMARY KEY(customer_id,device_id));
CREATE TABLE IF NOT EXISTS amc_contracts(
 contract_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL, device_id INTEGER NOT NULL,
 start_date TEXT NOT NULL, end_date TEXT NOT NULL CHECK(end_date>=start_date),
 renewed_from_id INTEGER UNIQUE REFERENCES amc_contracts, coverage_type TEXT NOT NULL,
 FOREIGN KEY(customer_id,device_id) REFERENCES customer_devices(customer_id,device_id));
CREATE TABLE IF NOT EXISTS amc_renewals(
 renewal_id INTEGER PRIMARY KEY, contract_id INTEGER NOT NULL UNIQUE REFERENCES amc_contracts,
 due_date TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('Accepted','Pending','Contacted','Declined')));
CREATE TABLE IF NOT EXISTS invoices(
 invoice_id INTEGER PRIMARY KEY, contract_id INTEGER NOT NULL UNIQUE REFERENCES amc_contracts,
 invoice_number TEXT NOT NULL UNIQUE, issued_date TEXT NOT NULL, due_date TEXT NOT NULL CHECK(due_date>=issued_date),
 amount_cents INTEGER NOT NULL CHECK(amount_cents>0), currency TEXT NOT NULL CHECK(currency='LKR'));
CREATE TABLE IF NOT EXISTS payments(
 payment_id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL REFERENCES invoices,
 payment_reference TEXT NOT NULL UNIQUE, paid_date TEXT NOT NULL,
 amount_cents INTEGER NOT NULL CHECK(amount_cents>0));
CREATE INDEX IF NOT EXISTS idx_demo_payments_invoice ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_demo_contract_dates ON amc_contracts(start_date,end_date);
'''


def default_database_path():
    return Path(__file__).resolve().parents[3] / 'data' / 'amc_revenue_demo.db'


def seed_demo(path):
    """Idempotent, transactional fixture, frozen at DEMO_AS_OF; never overwrite data."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        # Refuse to seed a customer/production DB or an unrelated existing file.
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if names and 'demo_metadata' not in names:
            raise ValueError('Expected a dedicated AMC revenue demo database; no records changed.')
        conn.executescript(SCHEMA)
        with conn:
            version = conn.execute("SELECT value FROM demo_metadata WHERE key='seed_version'").fetchone()
            if version:
                if version[0] != '1':
                    raise ValueError('Unsupported demo seed version')
                return
            for n in range(1, 61):
                conn.execute('INSERT INTO customers VALUES(?,?)', (n, ['Matheesha','Enuri','Sachith','Dewmini','Nipun','Kavisha','Sahan','Ishara','Dulaj','Senuri'][(n-1)%10]+' '+['Imalka','Isivari','Wickramasinghe','Jayawardena','Rathnayake','Senanayake'][(n-1)//10]))
                kind = 'Copier' if n % 3 == 0 else 'Printer'
                conn.execute('INSERT INTO devices VALUES(?,?,?,?)', (n, kind, 'Canon' if kind=='Copier' else 'HP', 'imageRUNNER 2425' if kind=='Copier' else 'LaserJet Pro M404dn'))
                conn.execute('INSERT INTO customer_devices VALUES(?,?)', (n,n))
            previous = {}
            contract_id = 0
            for year, count in ((2023,18), (2024,28), (2025,38), (2026,48)):
                # Moving cohorts include both attrition and new business.
                first = 1 + (year - 2023) * 4
                current = {}
                for n in range(first, first + count):
                    contract_id += 1
                    start = date(year, (n % 9) + 1, (n % 20) + 1)
                    end = date(year + 1, start.month, start.day) - timedelta(days=1)
                    prior = previous.get(n)
                    conn.execute('INSERT INTO amc_contracts VALUES(?,?,?,?,?,?,?)',
                                 (contract_id,n,n,start.isoformat(),end.isoformat(),prior,'Comprehensive' if n % 2 else 'Standard'))
                    current[n] = contract_id
                    if prior:
                        conn.execute("UPDATE amc_renewals SET status='Accepted' WHERE contract_id=?", (prior,))
                    status = ('Declined' if end < DEMO_AS_OF else
                              'Contacted' if (end - DEMO_AS_OF).days <= 90 else 'Pending')
                    conn.execute('INSERT INTO amc_renewals VALUES(?,?,?,?)', (contract_id,contract_id,end.isoformat(),status))
                    # Some contracts have not yet been invoiced. Never infer invoices from contracts.
                    if (n + year) % 11 == 0:
                        continue
                    amount = (24000 + n * 850 + (year - 2023) * 1800) * 100
                    issued = start + timedelta(days=2)
                    due = issued + timedelta(days=30)
                    conn.execute('INSERT INTO invoices VALUES(?,?,?,?,?,?,?)',
                                 (contract_id,contract_id,f'DEMO-AMC-{year}-{n:03d}',issued.isoformat(),due.isoformat(),amount,'LKR'))
                    mode = (n + year) % 5
                    if mode == 0:
                        continue
                    # Two installments test correct aggregation and avoid join fanout.
                    amounts = [amount // 2] if mode == 1 else [amount // 2, amount - amount // 2]
                    for part, paid in enumerate(amounts,1):
                        paid_date = issued + timedelta(days=7 * part)
                        if paid_date <= DEMO_AS_OF:
                            conn.execute('INSERT INTO payments(invoice_id,payment_reference,paid_date,amount_cents) VALUES(?,?,?,?)',
                                         (contract_id,f'DEMO-PAY-{contract_id}-{part}',paid_date.isoformat(),paid))
                previous = current
            conn.executemany('INSERT INTO demo_metadata VALUES(?,?)',
                             [('seed_version','1'),('is_synthetic','1'),('as_of',DEMO_AS_OF.isoformat())])
            if conn.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Demo foreign-key validation failed')


def load_dashboard(conn, year='All years', status='All statuses', device='All devices'):
    """All amounts are integer cents; year refers to contract start cohort.

    Payments belong to cohort invoices, through the fixed demo reporting date.
    Aggregate payments first, then join one invoice per contract to avoid fanout.
    """
    meta = dict(conn.execute('SELECT key,value FROM demo_metadata'))
    if meta.get('is_synthetic') != '1' or meta.get('seed_version') != '1':
        raise ValueError('Unsupported or unlabelled demo database')
    as_of = meta['as_of']
    rows = [dict(r) for r in conn.execute('''
      SELECT a.*,c.customer_name,d.device_type,d.brand,d.model,
       CASE WHEN a.end_date < :as_of THEN 'Expired'
            WHEN a.start_date > :as_of THEN 'Upcoming' ELSE 'Active' END dashboard_status,
       i.invoice_id, i.invoice_number, i.due_date, COALESCE(i.amount_cents,0) invoiced_cents,
       COALESCE(p.paid_cents,0) paid_cents,
       MAX(COALESCE(i.amount_cents,0)-COALESCE(p.paid_cents,0),0) outstanding_cents
      FROM amc_contracts a
      JOIN customer_devices cd ON cd.customer_id=a.customer_id AND cd.device_id=a.device_id
      JOIN customers c ON c.customer_id=a.customer_id JOIN devices d ON d.device_id=a.device_id
      LEFT JOIN invoices i ON i.contract_id=a.contract_id AND i.issued_date<=:as_of
      LEFT JOIN (SELECT invoice_id,SUM(amount_cents) paid_cents FROM payments
                 WHERE paid_date<=:as_of GROUP BY invoice_id) p ON p.invoice_id=i.invoice_id
      WHERE lower(d.device_type) IN ('printer','copier') ORDER BY a.start_date,a.contract_id
    ''', {'as_of': as_of})]
    base = [r for r in rows if (status == 'All statuses' or r['dashboard_status'] == status)
            and (device == 'All devices' or r['device_type'] == device)]
    selected = [r for r in base if year == 'All years' or r['start_date'][:4] == str(year)]
    ids = {r['contract_id'] for r in selected}
    renewals = [dict(r) for r in conn.execute('SELECT * FROM amc_renewals') if r['contract_id'] in ids]
    return dict(rows=selected,growth=base,renewals=renewals,as_of=as_of,
                years=sorted({r['start_date'][:4] for r in rows},reverse=True),
                statuses=sorted({r['dashboard_status'] for r in rows}),
                invoiced_cents=sum(r['invoiced_cents'] for r in selected),
                paid_cents=sum(r['paid_cents'] for r in selected),
                outstanding_cents=sum(r['outstanding_cents'] for r in selected),
                renewed_contracts=sum(r['renewed_from_id'] is not None for r in selected))


def open_demo(path=None):
    path = Path(path or default_database_path()).resolve()
    conn = sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=default_database_path())
    parser.add_argument('--seed', action='store_true')
    args = parser.parse_args()
    if args.seed:
        seed_demo(args.database)
    with closing(open_demo(args.database)) as connection:
        data = load_dashboard(connection)
        print(f"Synthetic AMC demo, as of {data['as_of']}: {len(data['rows'])} contracts")
        for key in ('invoiced_cents','paid_cents','outstanding_cents'):
            print(key.replace('_cents',''), f"LKR {data[key]/100:,.2f}")
