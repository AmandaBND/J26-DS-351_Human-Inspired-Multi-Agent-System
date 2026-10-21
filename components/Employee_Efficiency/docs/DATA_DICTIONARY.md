# Company export data dictionary

Export date: 02/10/2026 09:00. Period: 01/2024 - 09/2026 (33 months).
Employee numbers are 6 characters: `00` + 4 digits. Date format is `dd/mm/yyyy HH:MM`
except 01/2024-06/2024 (legacy system), which exports ISO `yyyy-mm-dd HH:MM:SS`.

| File | Grain | Rows (approx) |
|---|---|---|
| employees.csv | one row per employee | 34 |
| service_jobs.csv | one row per service job / repeat visit | 33,300 |
| amc_proposals.csv | one row per AMC proposal | 7,250 |
| amc_contracts.csv | one row per contract (new, renewal, legacy stock) | 5,000 |
| hr_attendance_monthly.csv | employee x month | 1,120 |
| system_downtime_log.csv | one row per outage | 60 |
| price_list_changes.csv | one row per AMC price revision | 3 |
| competitor_notes.csv | one row per note | ~120 |
| hr_reviews.csv | employee x review cycle | 136 |
| employee_feedback.csv | employee x month comment | ~880 |
| branch_territory_map.csv | branch -> service territory (reference) | 20 |
| public_holidays.csv | fixed-date holidays (reference) | 15 |

## employees.csv
employee_no, designation (free text: variants per role), base_territory, join_date, employment_status.

## service_jobs.csv
| Column | Meaning |
|---|---|
| job_id | `SR` + yymm + running number |
| request_dt | call registered by the 24-hour call centre |
| assigned_dt / assigned_by | technician assigned / TPO who assigned |
| technician_no | assigned technician (receives KPI credit) |
| arrival_dt | technician arrival (response time = request -> arrival, in WORKING hours) |
| completion_dt | repair completed |
| closure_dt / closed_by | administrative closure / TPO who closed |
| sla_due_dt | SLA deadline (P1 4 wh, P2 1 wd, P3 3 wd from request, P4 appointment day) |
| sla_alert_dt | when the TPO raised a pre-breach alert (blank = not monitored) |
| job_type | Breakdown repair / Preventive maintenance / Installation / Repeat visit / Other service |
| product_type, fault_type, fault_complexity | free-text model, fault, Low/Medium/High |
| priority | P1 critical, P2 high, P3 normal, P4 planned (many label variants) |
| branch | Metropolitan branch (maps to territory) |
| customer_ref | pseudonymous customer reference |
| contract_status | AMC / Warranty / Chargeable |
| repeat_visit_flag, parent_job_id | repeat visit marker and the original job it repeats |
| repair_time_hrs | ACTIVE repair time (MTTR basis), NOT elapsed time |
| parts_wait_hrs | working hours waiting for spare parts (tracked separately from repair time) |
| report_complete | service report fully completed |
| csat | 1-5 rating, only ~45% of customers respond |
| status | Closed / Completed / In Progress / Assigned / Open / Cancelled |
| reassigned_flag, admin_error_flag, record_complete_flag | TPO quality flags |

## amc_proposals.csv
proposal_id, coordinator_no, processor_no (set once accepted), proposal_dt, first_contact_dt,
followup_due_dates / followup_done_dates (`;`-separated), status, rejection_reason, approval_dt,
contract_id, quoted_price (LKR, text), customer_segment, product_category, customer_ref, data_complete_flag.

## amc_contracts.csv
contract_id, proposal_id, contract_type (New / Renewal / Legacy), processor_no, approval_dt,
contract_created_dt (blank = still pending), contract_start_date, renewal_due_date,
renewal_followup_date, data_complete_flag, correction_required_flag, pm_schedule_created_date,
pm_schedule_dates (`;`-separated), contract_value_lkr, product_category, status.

## Context / HR files
hr_attendance_monthly (employee_no, month, leave_days, overtime_hours); system_downtime_log
(incident_id, system, start_dt, end_dt, severity, remarks); price_list_changes (effective_date,
product_group, change_pct, remarks); competitor_notes (note_date, territory, product_category,
note_text, source); hr_reviews (employee_no, review_cycle, rating 1-5, manager_comment,
action_taken); employee_feedback (employee_no, month, comment_text).

## KPI derivation rules
- SLA compliance = completion_dt <= sla_due_dt.  FTFR = original breakdown/installation jobs with NO child repeat job (credited to the original technician via parent_job_id).
- MTTR = mean repair_time_hrs (active repair only).  Response = working hours request -> arrival (P1-P3).
- Assignment time = working minutes request -> assigned (after-hours requests start at next working period; P4 excluded).
- AMC conversion = proposals accepted within 45 days / proposals issued in the cohort month (only for cohorts older than 45 days).
- Contract processing time = working days approval -> contract creation.
- Renewal follow-up on time = renewal_followup_date at least 30 days before renewal_due_date.
- Working hours: Mon-Fri 08:30-17:00, Sat 08:30-13:00, Sunday/fixed holidays closed (prototype assumption).
