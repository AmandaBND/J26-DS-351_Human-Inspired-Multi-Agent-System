"""Read-only contract cohorts for the existing AMC customer database."""
from datetime import date, timedelta
import sqlite3

STATUSES = ['All', 'Renewed', 'Not renewed', 'Pending', 'Warranty expired']
DEFINITIONS = '''Reporting uses the stated as-of date. Year selects contract start year; warranty opportunities use warranty expiry year. Only printer/copier customer-device ownership pairs are included. AMC customers are distinct customers with a selected contract, including historical contracts. Renewed means the latest renewal record (due date, then ID) is Accepted. Not renewed means no accepted renewal and contract end is before the reporting date. Pending includes other contracts. Customer counts can overlap when different devices have different outcomes. Warranty expired counts distinct customers with an expired owned-device warranty and no active, date-valid AMC for that same ownership pair. Active excludes cancelled, terminated, declined, expired and inactive contract statuses. Missing dates remain unknown. Invoiced and Paid count distinct selected contracts with explicit invoice-to-contract links and, respectively, fully settled invoices. Payments are aggregated by invoice through the reporting date; customer-only invoices cannot establish contract attribution. Unknown financial attribution is unavailable, not zero. Accepted renewals describe recorded status; this schema has no acceptance timestamp for historical reconstruction.'''

def load_dashboard(conn, year='All', customer=None, status='All', as_of=None):
    as_of = date.fromisoformat(str(as_of)) if as_of else date.today()
    conn.row_factory = sqlite3.Row
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required = {'customers', 'devices', 'customer_devices', 'amc_contracts'}
    if not required <= tables:
        raise ValueError('Customer ownership and AMC contract tables are required. Run the existing database setup first.')
    ownership = [dict(r) for r in conn.execute('''SELECT c.customer_id,c.customer_name,o.device_id,
        o.warranty_end_date,d.device_type,d.model FROM customer_devices o
        JOIN customers c ON c.customer_id=o.customer_id JOIN devices d ON d.device_id=o.device_id
        WHERE lower(trim(d.device_type)) IN ('printer','copier')''')]
    contracts = [dict(r) for r in conn.execute('''SELECT a.* FROM amc_contracts a
        WHERE EXISTS(SELECT 1 FROM customer_devices o JOIN devices d ON d.device_id=o.device_id
        WHERE o.customer_id=a.customer_id AND o.device_id=a.device_id
        AND lower(trim(d.device_type)) IN ('printer','copier'))''')]
    def day(value):
        try: return date.fromisoformat(str(value))
        except (ValueError, TypeError): return None
    latest = {}
    if 'amc_renewals' in tables:
        for r in conn.execute('SELECT * FROM amc_renewals ORDER BY due_date,renewal_id'):
            latest[r['contract_id']] = dict(r)
    owners = {(o['customer_id'],o['device_id']):o for o in ownership}
    rows = []
    for a in contracts:
        start, end = day(a['start_date']), day(a['end_date'])
        if start and start > as_of: continue
        renewal = latest.get(a['contract_id'], {})
        outcome = 'Renewed' if renewal.get('status') == 'Accepted' else 'Not renewed' if end and end < as_of else 'Pending'
        rows.append({**owners[(a['customer_id'],a['device_id'])], **a,
                     'year': str(start.year) if start else 'Unknown', 'outcome':outcome,
                     'renewal_status':renewal.get('status','Not recorded'), 'renewal_due':renewal.get('due_date')})
    warranties = []
    for o in ownership:
        expiry = day(o['warranty_end_date'])
        active = any(a['customer_id']==o['customer_id'] and a['device_id']==o['device_id']
            and day(a['start_date']) and day(a['end_date']) and day(a['start_date'])<=as_of<=day(a['end_date'])
            and str(a.get('contract_status','')).lower() not in ('cancelled','canceled','terminated','declined','expired','inactive') for a in contracts)
        if expiry and expiry < as_of and not active:
            warranties.append({**o,'year':str(expiry.year),'outcome':'Warranty expired'})
    years = sorted({r['year'] for r in rows+warranties}, reverse=True)
    def selected(r):
        return (year=='All' or str(year)==r['year']) and (customer is None or r['customer_id']==customer) and (status=='All' or r['outcome']==status)
    chosen = [r for r in rows if selected(r)]
    uncovered = [r for r in warranties if selected(r)]
    financial = 'invoices' in tables and 'contract_id' in {r[1] for r in conn.execute('PRAGMA table_info(invoices)')}
    invoiced, paid = set(), set()
    if financial:
        # Aggregate installments before joining; never multiply invoice amounts by payment rows.
        payments = {r['invoice_id']:r['amount'] for r in conn.execute('SELECT invoice_id,SUM(amount_cents) amount FROM payments WHERE date(paid_date)<=date(?) GROUP BY invoice_id',(as_of.isoformat(),))} if 'payments' in tables else {}
        invoice_groups = {}
        for r in conn.execute('SELECT * FROM invoices WHERE date(issued_date)<=date(?)',(as_of.isoformat(),)):
            invoice_groups.setdefault(r['contract_id'],[]).append(dict(r))
        invoiced = set(invoice_groups)
        paid = {k for k,v in invoice_groups.items() if all(payments.get(i['invoice_id'],0)>=i['amount_cents'] for i in v)}
    comparison = []
    for y in sorted(years):
        if year!='All' and y!=str(year): continue
        group = [r for r in chosen if r['year']==y]
        comparison.append({'Year':y,'Contracts':len(group),'Renewed':sum(r['outcome']=='Renewed' for r in group),
                           'Invoiced':sum(r['contract_id'] in invoiced for r in group) if financial else None,
                           'Paid':sum(r['contract_id'] in paid for r in group) if financial and 'payments' in tables else None})
    attention = []
    for r in chosen:
        end = day(r['end_date'])
        if r['outcome']=='Not renewed' or (r['outcome']=='Pending' and end and end<=as_of+timedelta(days=90)):
            attention.append({**r,'priority':'High risk' if r['outcome']=='Not renewed' else 'Due within 90 days'})
    attention += [{**r,'priority':'Warranty expired'} for r in uncovered]
    attention.sort(key=lambda r:(0 if r['priority']=='High risk' else 1,str(r.get('end_date') or r.get('warranty_end_date') or ''),r['customer_id']))
    return dict(as_of=as_of.isoformat(),years=years,customers=sorted({(r['customer_id'],r['customer_name']) for r in ownership},key=lambda x:(x[1],x[0])),
        rows=chosen,warranties=uncovered,comparison=comparison,attention=attention,financial=financial,
        kpis=[len({r['customer_id'] for r in uncovered}),len({r['customer_id'] for r in chosen}),
              len({r['customer_id'] for r in chosen if r['outcome']=='Renewed'}),len({r['customer_id'] for r in chosen if r['outcome']=='Not renewed'})],
        warnings=([] if 'amc_renewals' in tables else ['Renewal records unavailable; no accepted renewals can be confirmed.']))
