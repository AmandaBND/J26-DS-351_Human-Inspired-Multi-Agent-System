"""Transactional evidence coordination. Voice/emotion remains standalone."""
from contextlib import closing
from datetime import date, datetime, timezone
import json
import sqlite3
from pathlib import Path
from uuid import uuid4
from emotion_aware_after_sales.database.setup_database import get_connection
from emotion_aware_after_sales.agents.contract_agent import ContractAgent
from emotion_aware_after_sales.agents.service_agent import ServiceAgent
from emotion_aware_after_sales.agents.payment_agent import PaymentAgent
from emotion_aware_after_sales.agents.policy_rag_agent import PolicyRAGAgent


class AMCMultiAgentOrchestrator:
    framework_version = 'research-prototype-2.0'

    def __init__(self, database_path=None, policy_dir=None):
        self.database_path = database_path
        self.contract_agent = ContractAgent()
        self.service_agent = ServiceAgent()
        self.payment_agent = PaymentAgent()
        self.policy_agent = PolicyRAGAgent(policy_dir)

    def analyze(self, customer_id, device_id, *, as_of=None):
        as_of = date.fromisoformat(str(as_of)) if as_of else date.today()
        context = dict(customer_id=customer_id, device_id=device_id, as_of=as_of.isoformat())
        result = dict(run_key=str(uuid4()), started_at=datetime.now(timezone.utc).isoformat(),
                      framework_version=self.framework_version, context=context, activity=[], evidence={})
        with closing(get_connection(self.database_path)) as conn:
            # Verify ownership before creating FK-constrained run records.
            conn.execute('BEGIN IMMEDIATE')
            contract = self.contract_agent.analyze(customer_id, device_id, connection=conn)
            if contract['status'] != 'completed':
                conn.rollback()
                return dict(result, status='blocked', assessment=contract['finding'], persistence='No run: invalid ownership')
            run_id = conn.execute("""INSERT INTO agent_runs(run_key,customer_id,device_id,started_at,status,framework_version)
                VALUES(?,?,?,?,'Running',?)""", (result['run_key'], customer_id, device_id,
                result['started_at'], self.framework_version)).lastrowid
            conn.commit()
            result['run_id'] = run_id
            try:
                with conn:
                    for schema in ('service_metrics_schema.sql', 'substitution_schema.sql'):
                        statement = ''
                        for line in (Path(__file__).parents[1]/'database'/schema).read_text().splitlines(True):
                            statement += line
                            if sqlite3.complete_statement(statement):
                                conn.execute(statement)
                                statement = ''
                    service = self.service_agent.analyze(customer_id, device_id, connection=conn, unlimited=True)
                    service['maintenance_schedule'] = [dict(r) for r in conn.execute(
                        'SELECT * FROM maintenance_schedule WHERE customer_id=? AND device_id=? ORDER BY scheduled_at',
                        (customer_id, device_id))]
                    service['visit_checks'] = [dict(r) for r in conn.execute("""SELECT c.* FROM service_visit_checks c
                        JOIN service_visits v USING(visit_id) JOIN service_requests r USING(request_id)
                        WHERE r.customer_id=? AND r.device_id=?""", (customer_id, device_id))]
                    service['approvals'] = [dict(r) for r in conn.execute("""SELECT a.* FROM maintenance_substitution_approvals a
                        JOIN maintenance_schedule m USING(maintenance_id) WHERE m.customer_id=? AND m.device_id=?""",
                        (customer_id, device_id))]
                    payment = self.payment_agent.analyze(customer_id, device_id, connection=conn, as_of=as_of.isoformat())
                    # Retrieve all relevant passages so the full conditional clause remains available.
                    policies = self.policy_agent.retrieve('synthetic policy version AMC repair maintenance preventive technician confirmation approval approve seven calendar days', top_k=100)
                    policy = dict(agent='Policy RAG Agent', status='completed' if policies else 'no_evidence',
                                  finding=f'Retrieved {len(policies)} synthetic policy passages.', policies=policies)
                    result['evidence'] = dict(contract=contract, service=service, payment=payment, policies=policies)
                    decisions = self._decide(contract, service, policies, as_of)
                    result.update(status='completed', decisions=decisions,
                                  assessment='; '.join(d['outcome']+': '+d['reason'] for d in decisions))
                    findings = [contract, service, payment, policy,
                        dict(agent='Orchestrator', status='completed', finding=result['assessment'], decisions=decisions)]
                    for finding in findings:
                        structured = dict(finding, context=context)
                        conn.execute('INSERT INTO agent_findings(run_id,agent_name,finding_key,finding) VALUES(?,?,?,?)',
                                     (run_id, finding['agent'], 'analysis', json.dumps(structured, ensure_ascii=False)))
                        result['activity'].append({k: finding[k] for k in ('agent','status','finding')})
                    result['finished_at'] = datetime.now(timezone.utc).isoformat()
                    conn.execute("UPDATE agent_runs SET status='Completed',finished_at=? WHERE run_id=?", (result['finished_at'], run_id))
            except Exception as exc:
                with conn:
                    conn.execute("UPDATE agent_runs SET status='Failed',finished_at=? WHERE run_id=?",
                                 (datetime.now(timezone.utc).isoformat(), run_id))
                    conn.execute('INSERT INTO agent_findings(run_id,agent_name,finding_key,finding) VALUES(?,?,?,?)',
                                 (run_id, 'Orchestrator', 'error', json.dumps(dict(context=context, error=type(exc).__name__))))
                raise
        return result

    @staticmethod
    def _decide(contract, service, policies, as_of):
        policy = [p for p in policies if p['policy_id']=='AMC-POL-004']
        # Only this reviewed synthetic policy version is implemented by the deterministic rule.
        policy_text = ' '.join(p['passage'].lower() for p in policy)
        policy_valid = bool(policy) and all(term in policy_text for term in
            ('version: 1.0', 'seven calendar days', 'technician', 'preventive maintenance checks', 'approve'))
        checks = {r['visit_id']:r for r in service['visit_checks']}
        decisions = []
        for scheduled in service['maintenance_schedule']:
            if scheduled['status'] != 'Scheduled': continue
            due = date.fromisoformat(scheduled['scheduled_at'][:10])
            candidates = []
            for visit in service['service_visits']:
                if not visit['completed_at'] or visit['request_status']!='Resolved': continue
                completed = date.fromisoformat(visit['completed_at'][:10])
                if not 0 <= (due-completed).days <= 7 or completed > as_of: continue
                check = checks.get(visit['visit_id'], {})
                confirmed = (check.get('visit_kind')=='Repair' and bool(str(check.get('preventive_checks_confirmed_by') or '').strip())
                             and bool(check.get('confirmed_at')) and completed <= date.fromisoformat(check['confirmed_at'][:10]) <= as_of)
                approved = any(a['repair_visit_id']==visit['visit_id'] and a['maintenance_id']==scheduled['maintenance_id']
                    and str(a['approved_by']).strip() and completed <= date.fromisoformat(a['approved_at'][:10]) <= as_of
                    for a in service['approvals'])
                covered = any(c['contract_status'].casefold()=='active' and c['start_date']<=completed.isoformat()<=due.isoformat()<=c['end_date']
                              for c in contract['contracts'])
                candidates.append(dict(visit_id=visit['visit_id'], completed_at=visit['completed_at'],
                    days_before=(due-completed).days, technician_confirmed=bool(confirmed), approval_recorded=bool(approved), contract_active=covered))
            eligible = policy_valid and any(c['technician_confirmed'] and c['approval_recorded'] and c['contract_active'] for c in candidates)
            decisions.append(dict(maintenance_id=scheduled['maintenance_id'], scheduled_at=scheduled['scheduled_at'],
                policy_id='AMC-POL-004' if policy else None, candidates=candidates,
                outcome='SUBSTITUTION ELIGIBLE' if eligible else 'MANUAL REVIEW REQUIRED',
                reason='Recorded repair, preventive checks, approval and active AMC satisfy synthetic AMC-POL-004.' if eligible else
                'Verify repair within seven days, active AMC, technician preventive checks and recorded approval under AMC-POL-004. No maintenance status changed.'))
        return decisions or [dict(outcome='MANUAL REVIEW REQUIRED', policy_id='AMC-POL-004' if policy else None,
                                 reason='No scheduled maintenance evidence available.')]
