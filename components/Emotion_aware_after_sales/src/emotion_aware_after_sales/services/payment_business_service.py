"""Read-only payment aggregation with explicit invoice-to-contract attribution."""
from datetime import date, timedelta
import sqlite3

DEFINITIONS = ('Invoice and payment totals use the selected invoice cohort through the reporting date. '
    'Payments are aggregated once per invoice; overpayments are shown as credit, never negative outstanding. '
    'Average payment delay is days after the due date until full settlement, averaged across settled invoices (on-time = 0). '
    'Previous late incidents count distinct invoices paid late in the trailing 365 days, including late installments. '
    'High risk requires an unpaid invoice more than 30 days overdue. Contract filtering uses explicit links only. '
    'Unlinked customer invoices are shown only without a contract filter, separately from contract balances. '
    'Business factor severity comes from recorded assessments, not inferred from numeric values. Synthetic research data; human review required.')

def load_payment_dashboard(conn, contract=None, customer=None, name=None, as_of=None):
    conn.row_factory=sqlite3.Row
    as_of=date.fromisoformat(str(as_of)) if as_of else date.today()
    def day(value):
        try: return date.fromisoformat(str(value)[:10])
        except (ValueError,TypeError): return None
    owners=[dict(r) for r in conn.execute("""SELECT o.customer_id,c.customer_name,o.device_id FROM customer_devices o
        JOIN customers c ON c.customer_id=o.customer_id JOIN devices d ON d.device_id=o.device_id
        WHERE lower(trim(d.device_type)) IN ('printer','copier')""")]
    pairs={(o['customer_id'],o['device_id']) for o in owners}
    names={o['customer_id']:o['customer_name'] for o in owners}
    contracts={r['contract_id']:dict(r) for r in conn.execute('SELECT * FROM amc_contracts') if (r['customer_id'],r['device_id']) in pairs}
    linked='contract_id' in {r[1] for r in conn.execute('PRAGMA table_info(invoices)')}
    selected=[]
    history=[]
    all_payments={}
    for p in conn.execute('SELECT * FROM payments ORDER BY paid_date,payment_id'):
        p=dict(p)
        if day(p['paid_date']) and day(p['paid_date'])<=as_of: all_payments.setdefault(p['invoice_id'],[]).append(p)
    for raw in conn.execute('SELECT * FROM invoices ORDER BY due_date,invoice_id'):
        r=dict(raw);cid=r.get('contract_id') if linked else None
        if r['customer_id'] not in names or not day(r['issued_date']) or day(r['issued_date'])>as_of: continue
        if cid is not None and (cid not in contracts or contracts[cid]['customer_id']!=r['customer_id']): continue
        if contract is not None and cid!=contract: continue
        if customer is not None and r['customer_id']!=customer: continue
        if name is not None and r['customer_id']!=name: continue
        receipts=all_payments.get(r['invoice_id'],[])
        paid=sum(p['amount_cents'] for p in receipts)
        balance=max(0,r['amount_cents']-paid)
        due=day(r['due_date']);settled=None;running=0
        for p in receipts:
            running+=p['amount_cents']
            if settled is None and running>=r['amount_cents']: settled=day(p['paid_date'])
            history.append({'Invoice':r['invoice_number'],'Contract ID':cid or 'Unlinked','Customer':names[r['customer_id']],
                'Date':p['paid_date'],'Amount (LKR)':p['amount_cents']/100,'Method':p['method']})
        delay=max(0,(settled-due).days) if settled and due else None
        late=bool(due and any(due<day(p['paid_date']) and as_of-timedelta(days=365)<day(p['paid_date'])<=as_of for p in receipts))
        overdue=(as_of-due).days if due and balance>0 and due<as_of else 0
        selected.append({**r,'contract_id':cid,'customer_name':names[r['customer_id']],'paid_cents':paid,
            'balance_cents':balance,'credit_cents':max(0,paid-r['amount_cents']),'delay_days':delay,'late':late,
            'overdue_days':overdue,'status':'Overdue' if overdue else 'Pending' if balance else 'Paid'})
    currencies={r['currency'] for r in selected}
    if currencies-{'LKR'}: raise ValueError('This dashboard reports LKR only; mixed currencies cannot be totalled.')
    delays=[r['delay_days'] for r in selected if r['delay_days'] is not None]
    factors=[]
    for raw in conn.execute('SELECT * FROM business_factors ORDER BY observed_at DESC,factor_id DESC'):
        r=dict(raw)
        if not day(r['observed_at']) or day(r['observed_at'])>as_of: continue
        if r['customer_id'] is not None and r['customer_id'] not in names: continue
        target=contracts.get(contract,{}).get('customer_id') if contract is not None else customer if customer is not None else name
        if target is not None and r['customer_id'] not in (None,target): continue
        if customer is not None and name is not None and customer!=name: continue
        if contract is not None and any(v is not None and v!=target for v in (customer,name)): continue
        factors.append({**r,'risk_level':r.get('risk_level') or 'Unassessed'})
    # Keep the latest observation for each customer/factor instead of showing stale assessments.
    latest={}
    for r in factors: latest.setdefault((r['customer_id'],r['factor_name']),r)
    outstanding=[{'Contract ID':r['contract_id'] or 'Unlinked','Customer':r['customer_name'],
        'Invoice':r['invoice_number'],'Outstanding (LKR)':r['balance_cents']/100,'Due date':r['due_date'],
        'Status':r['status']} for r in selected if r['balance_cents']]
    return dict(as_of=as_of.isoformat(),customers=names,contracts=contracts,rows=selected,history=history,
        factors=list(latest.values()),outstanding=outstanding,high_risk=any(r['overdue_days']>30 for r in selected),
        unlinked=sum(r['contract_id'] is None for r in selected),credit_cents=sum(r['credit_cents'] for r in selected),
        kpis={'Total Invoice Amount':sum(r['amount_cents'] for r in selected)/100,
              'Amount Paid':sum(r['paid_cents'] for r in selected)/100,
              'Outstanding Balance':sum(r['balance_cents'] for r in selected)/100,
              'Average Payment Delay':round(sum(delays)/len(delays),1) if delays else None,
              'Previous Late Incidents':sum(r['late'] for r in selected)})
