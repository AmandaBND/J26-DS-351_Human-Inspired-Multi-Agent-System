"""Payment and business workspace matching the supplied five-card reference."""
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
import sqlite3
from emotion_aware_after_sales.services.payment_business_service import load_payment_dashboard, DEFINITIONS
from emotion_aware_after_sales.services.pdf_report import build_pdf

def render_payment_business(st):
    from emotion_aware_after_sales.database.setup_database import DATABASE_PATH
    now=datetime.now(ZoneInfo('Asia/Colombo'))
    with closing(sqlite3.connect(DATABASE_PATH.resolve().as_uri()+'?mode=ro',uri=True)) as conn:
        options=load_payment_dashboard(conn,as_of=now.date())
        st.markdown('''<style>
        .payment-heading{display:flex;align-items:center;gap:16px;margin:0 0 22px}
        .payment-heading h1{margin:0;padding:0;font-size:34px!important}
        .payment-badge{color:#bd1731;border:1px solid #fecaca;background:#fff1f2;padding:5px 12px;border-radius:30px;font-size:12px;font-weight:750}
        .payment-card{background:white;border:1px solid #d7dde5;padding:22px 18px;min-height:164px;margin:10px 0 24px}
        .payment-card.alert{border-left:5px solid #c8102e}.payment-card small{font-size:12px;color:#52657b}
        .payment-card strong{display:block;font-size:28px;line-height:1.4;margin:20px 0 8px;color:#071b36}
        .payment-card.alert strong{color:#bd1731}.payment-card span{font-size:11px;color:#64748b}
        .payment-progress{height:6px;background:#e5e7eb;margin:10px 0}.payment-progress i{display:block;height:6px;background:#071b36}
        .payment-panel{font-size:19px;font-weight:750;color:#071b36;margin:0 0 18px}
        .payment-factor{padding:18px 0;border-bottom:1px solid #dce2ea;font-size:14px}
        .payment-factor p{font-size:12px;line-height:1.6;color:#60738c;margin:10px 0 0}
        .payment-factor span{float:right;border-radius:24px;background:#edf1f5;padding:4px 10px;font-size:10px;color:#52657b}
        .payment-factor .high{background:#bd1731;color:white}.payment-factor .medium{background:#657180;color:white}
        .st-key-payment_apply button,.st-key-payment_recommend button{background:#071b36!important;color:white!important;border-radius:0!important}
        .st-key-payment_apply button p,.st-key-payment_recommend button p{color:white!important}
        </style>''',unsafe_allow_html=True)
        heading,updated=st.columns([4,1])
        heading_slot=heading.empty()
        updated.caption('Updated '+now.strftime('%d %b %Y · %H:%M'))
        names=options['customers']
        with st.form('payment_filters'):
            cols=st.columns([1.1,1.1,1.4,.85],vertical_alignment='bottom')
            contract=cols[0].selectbox('Contract ID',[None]+list(options['contracts']),format_func=lambda v:'All Contracts' if v is None else f'AMC-{v:04}',key='payment_contract')
            customer=cols[1].selectbox('Customer ID',[None]+list(names),format_func=lambda v:'All Customers' if v is None else str(v),key='payment_customer')
            name=cols[2].selectbox('Customer Name',[None]+list(names),format_func=lambda v:'All Names' if v is None else names[v],key='payment_name')
            with cols[3].container(key='payment_apply'): st.form_submit_button('▼ APPLY FILTERS',use_container_width=True)
        data=load_payment_dashboard(conn,contract,customer,name,now.date())
    badge='<span class="payment-badge">▲ HIGH RISK</span>' if data['high_risk'] else ''
    heading_slot.markdown(f'<div class="payment-heading"><h1>Payment &amp; Business Analysis</h1>{badge}</div>',unsafe_allow_html=True)
    k=data['kpis']; paid=k['Amount Paid'];total=k['Total Invoice Amount']
    details=['Selected invoice cohort','Recorded receipts through reporting date','Unpaid invoice balance','Fully settled invoices · days after due date','Distinct invoices · trailing 365 days']
    for i,(col,(label,value),detail) in enumerate(zip(st.columns(5),k.items(),details)):
        display=f'Rs {value:,.0f}' if i<3 else 'Unavailable' if value is None else f'{value:g} days' if i==3 else str(value)
        accent='alert' if i==2 and value>0 else ''
        progress=f'<div class="payment-progress"><i style="width:{min(100,paid/total*100) if total else 0:.1f}%"></i></div>' if i==1 else ''
        col.markdown(f'<div class="payment-card {accent}"><small>{label}</small><strong>{display}</strong>{progress}<span>{detail}</span></div>',unsafe_allow_html=True)
    st.caption(f"Research data · Printers & copiers · LKR · As of {data['as_of']} · Unlinked customer invoices: {data['unlinked']}")
    if data['credit_cents']: st.info(f"Customer credit from overpayments: Rs {data['credit_cents']/100:,.2f}")
    left,right=st.columns([2.2,1],gap='medium')
    with left,st.container(border=True):
        st.markdown('<div class="payment-panel">▣　Outstanding Contracts Summary</div>',unsafe_allow_html=True)
        if data['outstanding']: st.dataframe(data['outstanding'],hide_index=True,use_container_width=True)
        else: st.info('No outstanding invoices match these filters.')
    with right,st.container(border=True):
        st.markdown('<div class="payment-panel">⌕　Business Factors</div>',unsafe_allow_html=True)
        assessed=[r for r in data['factors'] if r['risk_level']!='Unassessed']
        for r in assessed[:3]:
            level=r['risk_level']
            st.markdown(f'<div class="payment-factor"><span class="{level.lower()}">{level.upper()}</span><b>{escape(r["factor_name"])}</b><p>{escape(r["notes"] or "No assessment notes recorded.")}</p></div>',unsafe_allow_html=True)
        if not assessed: st.info('No recorded business-risk assessments for this selection.')
        st.caption('Illustrative research scenarios · Validate applicability to the customer.')
    actions=st.columns([1,1,1.5])
    actions[0].button('VIEW PAYMENT HISTORY',on_click=lambda:st.session_state.update(payment_history_open=True),use_container_width=True)
    actions[1].button('VIEW BUSINESS FACTORS',on_click=lambda:st.session_state.update(payment_factors_open=True),use_container_width=True)
    with actions[2].container(key='payment_recommend'):
        st.button('GENERATE FINAL RECOMMENDATION ✦',on_click=lambda:st.session_state.update(payment_recommend_open=True),use_container_width=True)
    if st.session_state.get('payment_history_open'):
        with st.expander('Payment history',expanded=True):
            if data['history']: st.dataframe(data['history'],hide_index=True,use_container_width=True)
            else: st.info('No recorded payments match these filters.')
    if st.session_state.get('payment_factors_open'):
        with st.expander('Business factor evidence',expanded=True):
            if data['factors']:
                st.dataframe([{'Factor':r['factor_name'],'Customer':names.get(r['customer_id'],'Portfolio scenario'),
                    'Value':r['numeric_value'],'Unit':r['unit'],'Risk':r['risk_level'],'Observed':r['observed_at'],
                    'Source':r['source'],'Notes':r['notes']} for r in data['factors']],hide_index=True,use_container_width=True)
            else: st.info('No business-factor observations match these filters.')
    if st.session_state.get('payment_recommend_open'):
        with st.expander('AMC recommendation · payment and business evidence',expanded=True):
            if not data['rows']: st.info('Select a customer or contract with recorded invoices to generate a recommendation.')
            else:
                recommendation=('Review overdue balances with the customer before renewal approval. Agree a payment plan and verify applicable business-factor evidence.'
                    if data['high_risk'] else 'Follow up outstanding invoices by their due dates and review contract and service evidence before confirming renewal.'
                    if k['Outstanding Balance'] else 'No unpaid balance in the selected invoice cohort. Proceed to contract and service review before confirming renewal.')
                st.write(recommendation)
                st.caption('Payment-informed research guidance; final AMC approval requires contract, service and policy evidence. No decision is saved automatically.')
                eligible=sorted({r['customer_id'] for r in data['rows']})
                target=st.selectbox('Customer for full AMC evidence',eligible,format_func=lambda v:names[v],key='payment_evidence_customer')
                def analyze():
                    st.session_state.update(hub_page='AMC Revenue Dashboard',amc_view='AMC Evidence Analysis',amc_customer_selector=f'{names[target]} (ID: {target})')
                st.button('Open full AMC evidence →',on_click=analyze)
    filters={'Contract':f'AMC-{contract:04}' if contract is not None else 'All','Customer ID':customer if customer is not None else 'All',
        'Customer Name':names.get(name,'All'),'As of':data['as_of']}
    report_rows=[{'Section':'Invoice register','Contract':r['contract_id'] or 'Unlinked','Customer':r['customer_name'],
        'Invoice':r['invoice_number'],'Due':r['due_date'],'Invoiced LKR':r['amount_cents']/100,'Paid LKR':r['paid_cents']/100,
        'Outstanding LKR':r['balance_cents']/100,'Status':r['status']} for r in data['rows']]
    st.download_button('↓ EXPORT PAYMENT & BUSINESS REPORT',build_pdf('Payment & Business Analysis',filters,
        {label:('Unavailable' if value is None else f'Rs {value:,.2f}' if i<3 else value) for i,(label,value) in enumerate(k.items())},report_rows,
        DEFINITIONS+' Business factors: '+'; '.join(f"{r['factor_name']} ({r['risk_level']}): {r['notes'] or r['numeric_value']}" for r in data['factors'])),
        'payment_business_analysis.pdf','application/pdf',use_container_width=True)
    with st.expander('How these metrics are calculated'):
        st.write(DEFINITIONS)
