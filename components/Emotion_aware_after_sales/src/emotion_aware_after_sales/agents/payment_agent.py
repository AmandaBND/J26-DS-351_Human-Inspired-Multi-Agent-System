"""Payment evidence is device-scoped only through explicit contract links."""
class PaymentAgent:
    name = 'Payment Agent'

    def analyze(self, customer_id, device_id, *, connection, as_of):
        columns = {r[1] for r in connection.execute('PRAGMA table_info(invoices)')}
        if 'contract_id' not in columns:
            return dict(agent=self.name, status='no_evidence', invoices=[],
                        finding='No explicit invoice-to-contract links; device balances cannot be inferred.')
        rows = connection.execute("""SELECT i.*, coalesce((SELECT sum(p.amount_cents)
            FROM payments p WHERE p.invoice_id=i.invoice_id AND date(p.paid_date)<=date(?)),0) AS paid_cents
            FROM invoices i JOIN amc_contracts a ON a.contract_id=i.contract_id
            WHERE i.customer_id=? AND a.customer_id=? AND a.device_id=? AND date(i.issued_date)<=date(?)
            ORDER BY i.invoice_id""", (as_of, customer_id, customer_id, device_id, as_of)).fetchall()
        invoices = [dict(r) for r in rows]
        for r in invoices:
            r['outstanding_cents'] = max(0, r['amount_cents']-r['paid_cents'])
        unlinked = connection.execute('SELECT count(*) FROM invoices WHERE customer_id=? AND contract_id IS NULL',
                                      (customer_id,)).fetchone()[0]
        return dict(agent=self.name, status='completed', invoices=invoices, unlinked_customer_invoices=unlinked,
                    finding=f'{len(invoices)} explicitly linked invoice(s); {unlinked} unlinked customer invoice(s) excluded. Payment does not authorize maintenance substitution.')
