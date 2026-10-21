"""Service evidence dashboard. Requests and visits retain separate date cohorts."""
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
import calendar
import sqlite3
from emotion_aware_after_sales.agents.service_agent import ServiceAgent
from emotion_aware_after_sales.services.pdf_report import build_pdf

DEFINITIONS = ('Metrics reflect recorded service requests and visits. Missing maintenance plans or response timestamps appear as “Unavailable.” '
    'High risk highlights urgent unresolved requests with overdue visits.')


def load_service_dashboard(conn, customer=None, year='All', month='All', now=None):
    now = now or datetime.now(ZoneInfo('Asia/Colombo'))
    owners = [dict(r) for r in conn.execute("""SELECT o.customer_id,c.customer_name,o.device_id,d.model
        FROM customer_devices o JOIN customers c ON c.customer_id=o.customer_id
        JOIN devices d ON d.device_id=o.device_id WHERE lower(trim(d.device_type)) IN ('printer','copier')""")]
    agent = ServiceAgent()
    requests, visits = [], []
    for owner in owners:
        evidence = agent.analyze(owner['customer_id'],owner['device_id'],connection=conn,unlimited=True)
        requests.extend({**r,**owner} for r in evidence['service_requests'])
        visits.extend({**v,**owner} for v in evidence['service_visits'])
    def stamp(value):
        try:
            value = datetime.fromisoformat(str(value))
            return value.replace(tzinfo=now.tzinfo) if value.tzinfo is None else value
        except (ValueError,TypeError): return None
    def selected(r, value):
        dt=stamp(value)
        return (customer is None or r['customer_id']==customer) and dt is not None and dt<=now and (year=='All' or dt.year==int(year)) and (month=='All' or dt.month==int(month))
    chosen=[r for r in requests if selected(r,r['opened_at'])]
    completed=[v for v in visits if selected(v,v['completed_at'])]
    scheduled=[v for v in visits if (customer is None or v['customer_id']==customer) and stamp(v['scheduled_at']) is not None
        and (year=='All' or stamp(v['scheduled_at']).year==int(year)) and (month=='All' or stamp(v['scheduled_at']).month==int(month))]
    overdue=[v for v in scheduled if stamp(v['scheduled_at'])<now and not v['completed_at'] and v['request_status']!='Cancelled']
    overdue_ids={v['request_id'] for v in overdue}
    high={r['request_id'] for r in chosen if r['priority'] in ('High','Urgent') and r['status'] not in ('Resolved','Cancelled') and r['request_id'] in overdue_ids}
    logs=[]
    for r in sorted(chosen,key=lambda r:r['opened_at'],reverse=True):
        comments=[v['resolution'] for v in visits if v['request_id']==r['request_id'] and v['resolution'] and stamp(v['completed_at']) and stamp(v['completed_at'])<=now]
        logs.append({'Date':r['opened_at'],'Device':f"{r['device_id']} / {r['model'] or 'Model unavailable'}",
            'Customer':f"{r['customer_name']} (ID {r['customer_id']})",'Customer comments (issue report)':r['issue_description'],
            'Technician comments':' | '.join(comments) or 'Not recorded','Status':'High Risk' if r['request_id'] in high else r['status']})
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    maintenance=[]
    if 'maintenance_schedule' in tables:
        owners_by_pair={(o['customer_id'],o['device_id']):o for o in owners}
        for row in conn.execute('SELECT * FROM maintenance_schedule'):
            row=dict(row)
            if (row['customer_id'],row['device_id']) in owners_by_pair:
                maintenance.append({**owners_by_pair[(row['customer_id'],row['device_id'])],**row})
    plans=[r for r in maintenance if r['status']!='Cancelled' and (customer is None or r['customer_id']==customer)
        and stamp(r['scheduled_at']) and (year=='All' or stamp(r['scheduled_at']).year==int(year))
        and (month=='All' or stamp(r['scheduled_at']).month==int(month))]
    responses={r['request_id']:r['first_response_at'] for r in conn.execute('SELECT request_id,first_response_at FROM service_responses')} if 'service_responses' in tables else {}
    hours=[]
    for r in chosen:
        response=stamp(responses.get(r['request_id']))
        opened=stamp(r['opened_at'])
        if response and opened and opened<=response<=now: hours.append((response-opened).total_seconds()/3600)
    response_value=f'{sum(hours)/len(hours):.1f} hrs' if hours else 'Unavailable'
    years=sorted({stamp(v).year for v in [r['opened_at'] for r in requests]+[v[k] for v in visits for k in ('scheduled_at','completed_at')]+[r['scheduled_at'] for r in maintenance] if stamp(v)},reverse=True)
    return dict(owners=owners,years=years,logs=logs,scheduled=scheduled,maintenance=plans,response_count=len(hours),request_count=len(chosen),high=len(high),kpis={
        'Breakdowns / requests':len(chosen),'Services completed':len(completed),'Expected maintenance':len(plans) if 'maintenance_schedule' in tables else 'Unavailable',
        'Service delays':len(overdue),'Avg response time':response_value})

def render_service_dashboard(st):
    from emotion_aware_after_sales.database.setup_database import DATABASE_PATH
    with closing(sqlite3.connect(DATABASE_PATH.resolve().as_uri()+'?mode=ro',uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        options=load_service_dashboard(conn)
        st.markdown('''<style>
        .service-title{font-size:34px;font-weight:800;margin:0 0 22px;color:#071b36}
        .service-risk{font-size:12px;color:#c8102e;background:#fff1f2;border:1px solid #fecdd3;border-radius:20px;padding:6px 12px;margin-left:14px;vertical-align:middle}
        .service-card{background:white;border:1px solid #d7dde5;padding:22px 20px;min-height:162px;margin:8px 0 24px}
        .service-card.alert{border-left:5px solid #c8102e}.service-card small{color:#52657b;font-size:13px}
        .service-card strong{display:block;color:#071b36;font-size:36px;margin:22px 0 6px}.service-card span{color:#64748b;font-size:11px}
        .service-log{background:#fff;border:1px solid #d7dde5;padding:22px 24px;font-weight:750;font-size:19px}
        </style>''',unsafe_allow_html=True)
        title,action=st.columns([5,1])
        names=dict(sorted({(o['customer_id'],o['customer_name']) for o in options['owners']}))
        cols=st.columns([1.5,1.2,1,1])
        customer=cols[0].selectbox('Customer',[None]+list(names),format_func=lambda v:'All Customers' if v is None else names[v],key='service_customer')
        ids=[None]+([customer] if customer is not None else list(names))
        if st.session_state.get('service_id') not in ids: st.session_state['service_id']=None
        customer_id=cols[1].selectbox('Customer ID',ids,format_func=lambda v:'All IDs' if v is None else str(v),key='service_id')
        year=cols[2].selectbox('Year',['All']+options['years'],key='service_year')
        month=cols[3].selectbox('Month',['All']+list(range(1,13)),format_func=lambda v:'All months' if v=='All' else calendar.month_name[v],key='service_month')
        data=load_service_dashboard(conn,customer_id if customer_id is not None else customer,year,month)
    badge=f'<span class="service-risk">HIGH RISK · {data["high"]}</span>' if data['high'] else ''
    title.markdown(f'<div class="service-title">Service Analysis{badge}</div>',unsafe_allow_html=True)
    filters={'Customer':names.get(customer,'All'),'Customer ID':customer_id if customer_id is not None else customer or 'All','Year':year,'Month':month}
    action.download_button('↓ EXPORT REPORT',build_pdf('Service & Operational Analysis',filters,data['kpis'],data['logs'],DEFINITIONS+f" Response timestamps available for {data['response_count']} of {data['request_count']} selected requests. Expected maintenance includes future planned dates in the selection."),'service_analysis.pdf','application/pdf',use_container_width=True)
    details=['Recorded service requests','Completed visits in selected period','Planned preventive maintenance','Overdue uncompleted visits',f"First response · {data['response_count']}/{data['request_count']} requests recorded"]
    for col,(label,value),detail in zip(st.columns(5),data['kpis'].items(),details):
        accent='alert' if label=='Service delays' and value else ''
        col.markdown(f'<div class="service-card {accent}"><small>{escape(label)}</small><strong>{value}</strong><span>{detail}</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="service-log">▣　Breakdown Feedback Log</div>',unsafe_allow_html=True)
    if data['logs']: st.dataframe(data['logs'],hide_index=True,use_container_width=True)
    else: st.info('No service requests match these filters.')
    st.caption('Includes labelled synthetic research examples · Printers & copiers only · Response time uses recorded first responses; missing responses are excluded.')
    with st.expander(f"Recorded scheduled visits ({len(data['scheduled'])}) & metric definitions"):
        st.write(DEFINITIONS)
        if data['scheduled']: st.dataframe(data['scheduled'],hide_index=True,use_container_width=True)
        if data['maintenance']:
            st.subheader('Preventive maintenance plan')
            st.dataframe(data['maintenance'],hide_index=True,use_container_width=True)
        st.caption('Requests: opened date. Completed services: completion date. Delays: overdue scheduled visits. Maintenance: planned date, including future visits. Average response: first response minus opened time, excluding missing or invalid responses.')
