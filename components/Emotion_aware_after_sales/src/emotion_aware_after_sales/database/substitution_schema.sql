-- Additive evidence only; no service or maintenance status is changed.
CREATE TABLE IF NOT EXISTS service_visit_checks (
 visit_id INTEGER PRIMARY KEY REFERENCES service_visits(visit_id),
 visit_kind TEXT NOT NULL CHECK(visit_kind IN ('Repair','Maintenance')),
 preventive_checks_confirmed_by TEXT,
 confirmed_at TEXT
);
CREATE TABLE IF NOT EXISTS maintenance_substitution_approvals (
 maintenance_id INTEGER NOT NULL REFERENCES maintenance_schedule(maintenance_id),
 repair_visit_id INTEGER NOT NULL REFERENCES service_visits(visit_id),
 approved_by TEXT NOT NULL CHECK(length(trim(approved_by))>0),
 approved_at TEXT NOT NULL,
 PRIMARY KEY(maintenance_id,repair_visit_id)
);
