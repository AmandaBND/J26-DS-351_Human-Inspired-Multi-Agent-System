"""Deterministic 2026 fixtures; never seed the runtime customer database."""
import json
from pathlib import Path
import sqlite3
from unittest.mock import patch
import pytest
from emotion_aware_after_sales.database.setup_database import initialize_database
from emotion_aware_after_sales.agents.orchestrator import AMCMultiAgentOrchestrator

@pytest.fixture
def scenario(tmp_path):
    path = tmp_path/'scenario.db'
    initialize_database(path)
    with sqlite3.connect(path) as c:
        c.executescript((Path(__file__).parents[1]/'src/emotion_aware_after_sales/database/service_metrics_schema.sql').read_text())
        c.executescript((Path(__file__).parents[1]/'src/emotion_aware_after_sales/database/substitution_schema.sql').read_text())
        c.execute("INSERT INTO devices VALUES(1,'Printer','Test','P1','SYNTH-TEST','Synthetic',12)")
        c.execute("INSERT INTO customers VALUES(1,'Synthetic Customer',NULL,NULL,1,'2024-01-01','2024-01-01','2024-12-31')")
        c.execute("INSERT INTO amc_contracts VALUES(1,1,'2026-01-01','2026-12-31','Active','AMC',1)")
        c.execute("INSERT INTO service_requests VALUES(1,'TEST-REPAIR',1,1,'2026-10-21','Repair','Normal','Resolved')")
        c.execute("INSERT INTO service_visits VALUES(1,1,'TEST-VISIT','2026-10-22T09:00:00','2026-10-22T10:00:00','Test Technician','Repair completed')")
        c.execute("INSERT INTO maintenance_schedule VALUES(1,'TEST-AMC',1,1,'2026-10-24T09:00:00','Scheduled',1,'Synthetic scenario')")
        c.execute('ALTER TABLE invoices ADD COLUMN contract_id INTEGER REFERENCES amc_contracts(contract_id)')
        c.execute("INSERT INTO invoices VALUES(1,'TEST-INVOICE',1,'2026-10-01','2026-10-15',10000,'LKR','AMC',1)")
        c.execute("INSERT INTO payments VALUES(1,1,'TEST-PAY','2026-10-16',4000,'Synthetic')")
    return path

def approve(path, confirm=True, approval=True):
    with sqlite3.connect(path) as c:
        if confirm:
            c.execute("INSERT INTO service_visit_checks VALUES(1,'Repair','Test Technician','2026-10-22T11:00:00')")
        if approval:
            c.execute("INSERT INTO maintenance_substitution_approvals VALUES(1,1,'Test Coordinator','2026-10-23T09:00:00')")

def analyze(path, **kwargs):
    return AMCMultiAgentOrchestrator(path).analyze(1,1,as_of=kwargs.get('as_of','2026-10-23'))

@pytest.mark.parametrize('confirm,approval,expected',[(False,False,'MANUAL REVIEW REQUIRED'),
    (True,False,'MANUAL REVIEW REQUIRED'),(False,True,'MANUAL REVIEW REQUIRED'),(True,True,'SUBSTITUTION ELIGIBLE')])
def test_october_22_before_october_24(scenario,confirm,approval,expected):
    approve(scenario,confirm,approval)
    result=analyze(scenario)
    d=result['decisions'][0]
    assert d['outcome']==expected
    assert d['policy_id']=='AMC-POL-004'
    assert d['candidates'][0]['days_before']==2
    assert result['evidence']['payment']['invoices'][0]['outstanding_cents']==6000
    assert len(result['activity'])==5
    with sqlite3.connect(scenario) as c:
        assert c.execute('SELECT status FROM agent_runs').fetchone()[0]=='Completed'
        findings=c.execute('SELECT finding FROM agent_findings').fetchall()
        assert len(findings)==5
        assert all(json.loads(r[0])['context']==result['context'] for r in findings)
        assert c.execute('SELECT status FROM maintenance_schedule').fetchone()[0]=='Scheduled'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()

@pytest.mark.parametrize('change',[
    "UPDATE service_visits SET completed_at='2026-10-14' ,scheduled_at='2026-10-14'",
    "UPDATE amc_contracts SET end_date='2026-10-23'",
    "UPDATE amc_contracts SET contract_status='Cancelled'",
    "UPDATE service_visit_checks SET visit_kind='Maintenance'",
    "UPDATE maintenance_substitution_approvals SET approved_at='2026-10-25'",
    "UPDATE service_requests SET status='Open'",
    "DELETE FROM service_visits",
])
def test_incomplete_or_ineligible_evidence(scenario,change):
    approve(scenario)
    with sqlite3.connect(scenario) as c: c.execute(change)
    assert analyze(scenario)['decisions'][0]['outcome']=='MANUAL REVIEW REQUIRED'

def test_no_future_repair_or_invalid_owner(scenario):
    approve(scenario)
    assert analyze(scenario,as_of='2026-10-21')['decisions'][0]['outcome']=='MANUAL REVIEW REQUIRED'
    result=AMCMultiAgentOrchestrator(scenario).analyze(999,1,as_of='2026-10-23')
    assert result['status']=='blocked'

def test_missing_policy_and_failure_persisted(scenario,tmp_path):
    approve(scenario)
    result=AMCMultiAgentOrchestrator(scenario,tmp_path).analyze(1,1,as_of='2026-10-23')
    assert result['decisions'][0]['outcome']=='MANUAL REVIEW REQUIRED'
    agent=AMCMultiAgentOrchestrator(scenario)
    with patch.object(agent.service_agent,'analyze',side_effect=RuntimeError('test')):
        with pytest.raises(RuntimeError): agent.analyze(1,1,as_of='2026-10-23')
    with sqlite3.connect(scenario) as c:
        assert c.execute('SELECT status FROM agent_runs ORDER BY run_id DESC').fetchone()[0]=='Failed'

def test_other_device_invoice_excluded(scenario):
    with sqlite3.connect(scenario) as c:
        c.execute("INSERT INTO devices VALUES(2,'Printer','Test','P2','SYNTH-TEST2','Synthetic',12)")
        c.execute("INSERT INTO customer_devices VALUES(1,2,'2024-01-01','2024-01-01','2024-12-31')")
        c.execute("INSERT INTO amc_contracts VALUES(2,2,'2026-01-01','2026-12-31','Active','AMC',1)")
        c.execute("INSERT INTO invoices VALUES(2,'OTHER',1,'2026-10-01','2026-10-15',99999,'LKR','Other device',2)")
    assert len(analyze(scenario)['evidence']['payment']['invoices'])==1
