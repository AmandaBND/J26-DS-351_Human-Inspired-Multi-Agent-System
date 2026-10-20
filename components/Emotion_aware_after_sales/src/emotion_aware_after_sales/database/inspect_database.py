"""Read-only inspection; explicitly select a database."""
import argparse
import sqlite3
from pathlib import Path

def inspect(path):
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as c:
        print('Schema version:',c.execute('PRAGMA user_version').fetchone()[0])
        print('Integrity:',c.execute('PRAGMA integrity_check').fetchall())
        print('Foreign key errors:',c.execute('PRAGMA foreign_key_check').fetchall())
        for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
            safe = name.replace('"','""')
            print(name,c.execute(f'SELECT count(*) FROM "{safe}"').fetchone()[0])
        print('Multi-device customers:',c.execute('SELECT customer_id,count(*) FROM customer_devices GROUP BY customer_id HAVING count(*)>1').fetchall())

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--database',required=True,type=Path)
    inspect(p.parse_args().database)
