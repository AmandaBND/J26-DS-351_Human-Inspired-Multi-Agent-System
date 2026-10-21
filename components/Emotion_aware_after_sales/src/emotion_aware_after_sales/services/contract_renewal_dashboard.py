"""Streamlit presentation for the customer database contract dashboard."""
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
from emotion_aware_after_sales.services.pdf_report import build_pdf

from emotion_aware_after_sales.services.contract_renewal_service import load_dashboard, STATUSES, DEFINITIONS

def render_contract_renewal(st):
    from emotion_aware_after_sales.database.setup_database import DATABASE_PATH
    import sqlite3
    as_of = datetime.now(ZoneInfo('Asia/Colombo')).date()
    with closing(sqlite3.connect(DATABASE_PATH.resolve().as_uri()+'?mode=ro',uri=True)) as conn:
        options = load_dashboard(conn,as_of=as_of)
        st.markdown('<div class="contract-breadcrumb">AMC OVERVIEW　 ›　 CONTRACT ANALYSIS</div>',unsafe_allow_html=True)
        st.markdown('''<style>
        .contract-breadcrumb {font-size:12px;letter-spacing:.06em;color:#526882;margin:0 0 12px}
        .contract-title {font-size:32px!important;color:#071b36;margin:0!important;padding:0!important;line-height:1.5!important;font-weight:750}
        .st-key-contract_export_action button {background:#071b36!important;color:#fff!important;border:1px solid #071b36!important;min-height:48px;font-weight:600}
        .st-key-contract_export_action button p {color:#fff!important}
        .st-key-contract_export_action button:hover {background:#173553!important;border-color:#173553!important}
        .contract-card {background:white;border:1px solid #d5dce6;padding:20px;min-height:132px;margin:12px 0 22px}
        .contract-card small {font-size:11px;color:#60738c}.contract-card strong {display:block;font-size:30px;color:#071b36;margin:7px 0}
        .contract-card.alert strong {color:#c8102e}.contract-card span {font-size:12px;color:#718198}
        .contract-attention {border:1px solid #dce2ea;background:#f8fafc;padding:14px;margin:10px 0;color:#071b36;font-size:13px}
        .contract-attention b {float:right;color:#a92138;font-size:11px}
        </style>''',unsafe_allow_html=True)
        heading, export = st.columns([4,1],vertical_alignment='center')
        with heading:
            st.markdown('<h1 class="contract-title">Contract &amp; Renewal Analysis</h1>',unsafe_allow_html=True)
        export_action = export.container(key='contract_export_action')
        st.caption('View historical performance and renewal patterns across customer segments.')
        with st.form('contract_filters'):
            cols=st.columns([1,1.5,1,1],vertical_alignment='bottom')
            year=cols[0].selectbox('Year',['All']+options['years'])
            names=dict(options['customers'])
            customer=cols[1].selectbox('Customer',[None]+list(names),format_func=lambda v:'All customers' if v is None else f'{names[v]} · {v}')
            status=cols[2].selectbox('Status',STATUSES)
            cols[3].form_submit_button('Apply filters',type='primary',use_container_width=True)
        data=load_dashboard(conn,year,customer,status,as_of)
    st.caption(f"Customer research database · Printers & copiers · As of {data['as_of']}")
    for warning in data['warnings']: st.warning(warning)
    for col,label,value,detail in zip(st.columns(4),['WARRANTY EXPIRED','AMC CUSTOMERS','RENEWED','NOT RENEWED'],data['kpis'],['No active AMC on expired device','Distinct customers in cohort','Recorded accepted renewal','Expired contract · follow up']):
        col.markdown(f'<div class="contract-card {"alert" if label=="NOT RENEWED" else ""}"><small>{label}</small><strong>{value:,}</strong><span>{detail}</span></div>',unsafe_allow_html=True)
    left,right=st.columns([1.6,1])
    with left:
        with st.container(border=True):
            st.subheader('Year Comparison')
            if data['comparison']:
                st.dataframe([{k:('Unavailable' if v is None else v) for k,v in r.items()} for r in data['comparison']],hide_index=True,use_container_width=True)
            else: st.info('No records match these filters.')
            st.caption('Counts of contracts · Year = contract start year · Paid = fully settled')
            if not data['financial']: st.caption('Invoiced / Paid unavailable: customer invoices have no contract link.')
    with right:
        with st.container(border=True):
            st.subheader('Renewal Attention')
            if not data['attention']: st.info('No overdue contracts or renewals due within 90 days, or uncovered expired warranties, in this selection.')
            for r in data['attention'][:6]:
                detail=f"Device {r['device_id']} · {r.get('end_date') or r.get('warranty_end_date') or 'Date unavailable'}"
                st.markdown(f'<div class="contract-attention"><b>{escape(r["priority"])}</b>{escape(r["customer_name"])}<br><small>{escape(detail)}</small></div>',unsafe_allow_html=True)
            if len(data['attention'])>6: st.caption(f"Showing 6 of {len(data['attention'])}; full list in report.")
    filters={'Year':year,'Customer ID':customer if customer is not None else 'All','Status':status,'As of':data['as_of']}
    kpis=dict(zip(['Warranty expired','AMC customers','Renewed','Not renewed'],data['kpis']))
    pdf=build_pdf('Contract & Renewal Analysis',filters,kpis,data['rows']+data['warranties'],DEFINITIONS)
    export_action.download_button('↓ Export report',pdf,'contract_renewal_report.pdf','application/pdf',type='primary',use_container_width=True)
    actions=st.columns([1,1,1])
    actions[0].download_button('Export PDF',pdf,'contract_renewal.pdf','application/pdf',use_container_width=True)
    actions[1].button('View non-renewed customers',on_click=lambda:st.session_state.update(contract_show_nonrenewed=True),use_container_width=True)
    eligible=sorted({r['customer_id'] for r in data['rows']+data['warranties']})
    target=st.selectbox('Customer to analyze',eligible,format_func=lambda v:f'{names[v]} · {v}') if eligible else None
    def analyze():
        st.session_state.update(hub_page='AMC Revenue Dashboard',amc_view='AMC Evidence Analysis',amc_customer_selector=f'{names[target]} (ID: {target})')
    actions[2].button('Analyze customer →',on_click=analyze,disabled=target is None,type='primary',use_container_width=True)
    if st.session_state.get('contract_show_nonrenewed'):
        with st.expander('Non-renewed customers',expanded=True):
            nonrenewed=[r for r in data['rows'] if r['outcome']=='Not renewed']
            if nonrenewed:
                st.dataframe([{k:r[k] for k in ('customer_id','customer_name','device_id','contract_id','end_date','renewal_status')} for r in nonrenewed],hide_index=True,use_container_width=True)
                st.download_button('Download non-renewed PDF',build_pdf('Non-renewed Customers',filters,kpis,nonrenewed,DEFINITIONS),'non_renewed_customers.pdf','application/pdf')
            else: st.info('No non-renewed customers match these filters.')
    with st.expander('Metric definitions & data limitations'):
        st.write(DEFINITIONS)
