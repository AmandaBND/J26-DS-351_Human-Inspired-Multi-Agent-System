"""AMC v4 schema: customer purchase/warranty and device specifications."""
import argparse
import sqlite3
from contextlib import closing
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / 'data' / 'amc_service.db'

def get_connection(path=None):
    path = Path(path or DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def backup_database(path):
    path = Path(path).resolve()
    if not path.exists():
        return
    backup = path.with_name(path.name + datetime.now().strftime('.%Y%m%d-%H%M%S-%f.bak'))
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as source, closing(sqlite3.connect(backup)) as target:
        with target:
            source.backup(target)
    print('Backup:', backup)

CUSTOMERS = '''CREATE TABLE customers_new (
 customer_id INTEGER PRIMARY KEY,
 customer_name TEXT NOT NULL,
 phone_number TEXT,
 email TEXT,
 device_id INTEGER NOT NULL UNIQUE REFERENCES devices(device_id),
 purchase_date TEXT NOT NULL CHECK(length(purchase_date)=10 AND date(purchase_date,'+0 days') IS NOT NULL AND date(purchase_date,'+0 days')=purchase_date),
 warranty_start_date TEXT NOT NULL CHECK(length(warranty_start_date)=10 AND date(warranty_start_date,'+0 days') IS NOT NULL AND date(warranty_start_date,'+0 days')=warranty_start_date),
 warranty_end_date TEXT NOT NULL CHECK(length(warranty_end_date)=10 AND date(warranty_end_date,'+0 days') IS NOT NULL AND date(warranty_end_date,'+0 days')=warranty_end_date),
 CHECK(warranty_start_date >= purchase_date),
 CHECK(warranty_end_date >= warranty_start_date)
)'''
DEVICES = '''CREATE TABLE devices_new (
 device_id INTEGER PRIMARY KEY,
 device_type TEXT NOT NULL CHECK(device_type IN ('Printer','Copier','Scanner')),
 brand TEXT,
 model TEXT,
 serial_number TEXT UNIQUE,
 device_features TEXT NOT NULL,
 warranty_period_months INTEGER NOT NULL CHECK(typeof(warranty_period_months)='integer' AND warranty_period_months > 0)
)'''
FEATURES = {
 'Printer': 'Illustrative: monochrome laser printing; automatic duplex; USB and network connectivity',
 'Copier': 'Illustrative: document copying; automatic document feeder; duplex copying; zoom adjustment',
 'Scanner': 'Illustrative: document scanning; automatic document feeder; duplex scanning; PDF and JPEG output',
}

def _initialize_empty_v4(path=None):
    path = Path(path or DATABASE_PATH).resolve()
    backup_database(path)
    c = get_connection(path)
    try:
        # SQLite requires FK disabling before BEGIN for safe table reconstruction.
        c.execute('PRAGMA foreign_keys=OFF')
        c.execute('BEGIN IMMEDIATE')
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not tables:
            c.execute(DEVICES.replace('devices_new', 'devices'))
            c.execute(CUSTOMERS.replace('customers_new', 'customers'))
        elif 'device_id' not in {r[1] for r in c.execute('PRAGMA table_info(customers)')}:
            if c.execute('SELECT 1 FROM customers c LEFT JOIN devices d ON d.customer_id=c.customer_id GROUP BY c.customer_id HAVING count(d.device_id) != 1').fetchone():
                raise ValueError('This layout requires one device per customer. Migration stopped without changing records.')
            if c.execute('SELECT 1 FROM devices WHERE purchase_date IS NULL OR warranty_start_date IS NULL OR warranty_end_date IS NULL').fetchone():
                raise ValueError('Missing purchase/warranty dates; supply verified dates before migrating.')
            unknown = c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name IN ('customers','devices') AND name NOT LIKE 'amc_v2_%'").fetchall()
            if unknown:
                raise ValueError('Custom triggers need review before rebuilding customer/device tables')
            c.execute('DROP VIEW IF EXISTS device_warranties')
            for row in c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'amc_v2_%'").fetchall():
                c.execute('DROP TRIGGER "'+row[0].replace('"','""')+'"')
            c.execute(DEVICES)
            c.execute(CUSTOMERS)
            c.execute('INSERT INTO customers_new SELECT c.customer_id,c.customer_name,c.phone_number,c.email,d.device_id,d.purchase_date,d.warranty_start_date,d.warranty_end_date FROM customers c JOIN devices d ON d.customer_id=c.customer_id')
            for d in c.execute('SELECT * FROM devices').fetchall():
                c.execute('INSERT INTO devices_new VALUES (?,?,?,?,?,?,?)', (d['device_id'],d['device_type'],d['brand'],d['model'],d['serial_number'],FEATURES[d['device_type']],12))
            c.execute('DROP TABLE customers')
            c.execute('DROP TABLE devices')
            c.execute('ALTER TABLE devices_new RENAME TO devices')
            c.execute('ALTER TABLE customers_new RENAME TO customers')
        for sql in (
            'CREATE TABLE IF NOT EXISTS amc_contracts(contract_id INTEGER PRIMARY KEY, device_id INTEGER NOT NULL REFERENCES devices(device_id), start_date TEXT NOT NULL, end_date TEXT NOT NULL, contract_status TEXT NOT NULL, coverage_type TEXT, customer_id INTEGER NOT NULL REFERENCES customers(customer_id))',
            'CREATE TABLE IF NOT EXISTS service_history(service_id INTEGER PRIMARY KEY, device_id INTEGER NOT NULL REFERENCES devices(device_id), service_date TEXT NOT NULL, issue_description TEXT, resolution TEXT, service_status TEXT NOT NULL, customer_id INTEGER NOT NULL REFERENCES customers(customer_id))',
            'CREATE TABLE IF NOT EXISTS amc_policies(policy_id INTEGER PRIMARY KEY, policy_name TEXT NOT NULL, policy_description TEXT NOT NULL, policy_category TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS call_analyses(analysis_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id), contract_id INTEGER REFERENCES amc_contracts(contract_id), call_date TEXT NOT NULL, dominant_emotion TEXT, vocal_activation REAL, recommended_action TEXT, decision_reason TEXT)',
        ): c.execute(sql)
        for table in ('amc_contracts','service_history'):
            if c.execute(f'SELECT 1 FROM {table} t LEFT JOIN customers c ON c.customer_id=t.customer_id WHERE c.customer_id IS NULL OR c.device_id IS NOT t.device_id').fetchone():
                raise ValueError(f'{table}: existing ownership mismatch')
            for event in ('INSERT','UPDATE'):
                c.execute(f"CREATE TRIGGER IF NOT EXISTS amc_v4_{table}_{event.lower()} BEFORE {event} ON {table} WHEN NOT EXISTS(SELECT 1 FROM customers c WHERE c.customer_id=NEW.customer_id AND c.device_id=NEW.device_id) BEGIN SELECT RAISE(ABORT,'Customer and device must match'); END")
        c.execute("CREATE TRIGGER IF NOT EXISTS amc_v4_customer_device BEFORE UPDATE OF device_id,customer_id ON customers WHEN EXISTS(SELECT 1 FROM amc_contracts a WHERE a.customer_id=OLD.customer_id AND (a.customer_id IS NOT NEW.customer_id OR a.device_id IS NOT NEW.device_id)) OR EXISTS(SELECT 1 FROM service_history s WHERE s.customer_id=OLD.customer_id AND (s.customer_id IS NOT NEW.customer_id OR s.device_id IS NOT NEW.device_id)) BEGIN SELECT RAISE(ABORT,'Customer has linked contracts or service history'); END")
        c.execute('CREATE VIEW IF NOT EXISTS device_warranties AS SELECT c.customer_id,c.customer_name,c.device_id,d.device_type,d.brand,d.model,c.purchase_date,c.warranty_start_date,c.warranty_end_date,d.warranty_period_months FROM customers c JOIN devices d USING(device_id)')
        if c.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('Foreign key check failed')
        c.commit()
        c.execute('PRAGMA foreign_keys=ON')
        print('Schema ready:', path)
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def initialize_database(path=None):
    """Add v5 to verified v4 databases; never rebuild populated legacy tables."""
    path = Path(path or DATABASE_PATH).resolve()
    if not path.exists():
        _initialize_empty_v4(path)
    backup_database(path)
    c = get_connection(path)
    try:
        c.execute('BEGIN IMMEDIATE')
        version = c.execute('PRAGMA user_version').fetchone()[0]
        if version > 5:
            raise ValueError('Database is newer than this migration')
        required = {'customers','devices','amc_contracts','service_history','amc_policies','call_analyses'}
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required <= tables:
            raise ValueError('Expected complete v4 schema; migration rolled back')
        if not {'device_id','purchase_date','warranty_start_date','warranty_end_date'} <= {r[1] for r in c.execute('PRAGMA table_info(customers)')}:
            raise ValueError('Expected v4 customer columns; migration rolled back')
        if c.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Existing foreign key errors; repair before migration')
        from pathlib import Path as _Path
        # Execute statements individually: executescript would commit the transaction.
        statement = ''
        for line in _Path(__file__).with_name('schema_v5.sql').read_text(encoding='utf-8').splitlines(True):
            statement += line
            if sqlite3.complete_statement(statement):
                c.execute(statement)
                statement = ''
        if statement.strip():
            raise ValueError('Incomplete migration SQL')
        c.execute('''INSERT INTO customer_devices(customer_id,device_id,purchase_date,warranty_start_date,warranty_end_date)
          SELECT customer_id,device_id,purchase_date,warranty_start_date,warranty_end_date FROM customers WHERE 1
          ON CONFLICT(customer_id,device_id) DO NOTHING''')
        for table in ('amc_contracts','service_history'):
            if c.execute(f'SELECT 1 FROM {table} t LEFT JOIN customer_devices d ON d.customer_id=t.customer_id AND d.device_id=t.device_id WHERE d.device_id IS NULL').fetchone():
                raise ValueError(f'{table}: ownership mismatch')
            for event in ('INSERT','UPDATE'):
                c.execute(f'DROP TRIGGER IF EXISTS amc_v4_{table}_{event.lower()}')
                c.execute(f"CREATE TRIGGER IF NOT EXISTS amc_v5_{table}_{event.lower()} BEFORE {event} ON {table} WHEN NOT EXISTS(SELECT 1 FROM customer_devices d WHERE d.customer_id=NEW.customer_id AND d.device_id=NEW.device_id) BEGIN SELECT RAISE(ABORT,'Customer and device must match'); END")
        c.execute('DROP VIEW IF EXISTS device_warranties')
        c.execute('''CREATE VIEW device_warranties AS SELECT c.customer_id,c.customer_name,o.device_id,d.device_type,d.brand,d.model,o.purchase_date,o.warranty_start_date,o.warranty_end_date,d.warranty_period_months FROM customer_devices o JOIN customers c USING(customer_id) JOIN devices d USING(device_id)''')
        if c.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Migration foreign key check failed')
        c.execute('PRAGMA user_version=5')
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--database',type=Path,default=DATABASE_PATH)
    initialize_database(p.parse_args().database)
