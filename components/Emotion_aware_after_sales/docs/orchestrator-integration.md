# AMC orchestration verification

Contract, Service, Payment and Policy RAG evidence is coordinated by
AMCMultiAgentOrchestrator. Emotion/Voice remains standalone and is not imported
or called by the orchestrator. Existing standalone UI is preserved.

Each valid customer/device run has a UUID and agent_runs row; five structured
JSON agent_findings contain shared customer_id, device_id, as_of and evidence.
Failures update the run to Failed with an error finding. Invalid ownership
is blocked before insertion because agent_runs enforces ownership foreign keys.
Payment evidence includes only explicit invoice-to-contract-to-device links;
unlinked customer invoices are reported separately and never inferred as device debt.
Payments do not authorize or deny substitution.

The additive service_visit_checks and maintenance_substitution_approvals tables
record explicit repair classification, technician preventive-check confirmation,
and service-team approval for a particular repair/maintenance pair. They and
missing service-metric tables are created on the first valid analysis. Existing
service records and scheduled visit statuses are never changed by analysis.
The existing v5 schema and runtime columns were inspected before implementation.

## Deterministic scenario

tests/test_orchestrator_integration.py creates disposable SQLite fixtures using
the schema, never production/demo seeds. Explicit year: 2026. Repair completes
October 22, maintenance is scheduled October 24, analysis date is October 23.
Synthetic policy AMC-POL-004 version 1.0 permits at most seven calendar days.
Missing confirmation or approval yields MANUAL REVIEW REQUIRED. Both recorded,
with active coverage and completed repair, yield SUBSTITUTION ELIGIBLE. This is
a decision-support finding and does not mark maintenance completed.

The tests cover missing checks/approval, wrong visit kind, future evidence,
out-of-window repair, expired/cancelled contracts, missing visits/policy,
invalid ownership, payment device isolation, persisted runs/findings/failures.

## Verification on 20 October 2026

- Integration and voice customer lookup: 19 passed.
- Full tests directory: 52 passed, 1 failed because torch is not installed
  (test_automatic_diarization_assigns_roles).
- Source and app compilation: passed.
- Read-only aggregation and PDF generation/parsing: Service (2 pages), Contract
  (3 pages), Payment (3 pages), Revenue (29 pages) passed against existing data.
- All six dashboard export controls declare application/pdf.
- Live Streamlit app/voice model smoke: blocked by missing Streamlit, torch and
  pyannote dependencies. Installing dashboard verification dependencies failed
  with No space left on device. Installation was partial; environment repair
  is required after freeing space. No model/audio regression pass is claimed.
- Main merge is withheld until the required runtime checks pass.

Run from the repository root with components/Emotion_aware_after_sales/src on
PYTHONPATH: python -m pytest components/Emotion_aware_after_sales/tests -q.
Use the existing local virtual environment after restoring its dependencies.
No runtime database, recordings, personal audio, datasets, backups or secrets
belong in commits; .gitignore excludes these. Existing local artifacts are kept.
