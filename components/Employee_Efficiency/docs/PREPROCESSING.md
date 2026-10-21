# Preprocessing and data interpretation

## Pipeline

Run `uv run python -m src.services.preprocessing.pipeline` from this component directory.
The pipeline validates its input directory, rebuilds the SQLite schema, reads each CSV with
string-valued columns, applies explicit cleaning rules, pseudonymizes employee references, then
derives monthly KPI and operating-context records. The run ID and aggregate data-quality events are
stored in `data_quality_log`; `DATA_QUALITY_REPORT.md` is regenerated with file-level before/after
counts. The pipeline prints the row counts and period coverage after a successful run.

The database is rebuilt on each run. This also clears local recommendation, manager-decision, and
intervention records, so export or record those decisions before deliberately re-running it.
By default, the company CSV pipeline uses `data/employee_efficiency_company.db`; the previous
`data/employee_efficiency.db` is preserved. Set `DATABASE_PATH` to deliberately target a different database.

## Cleaning rules

- Employee numbers are stripped, zero-padded to six digits, validated against `employees.csv`, then
  mapped in ascending order to `EMP-001` through `EMP-034`. The source-to-code map is private and
  excluded from version control.
- Service-job test records are excluded by test job ID, customer reference, or test product marker.
  Exact duplicate rows and duplicate job IDs after the first are excluded.
- Priority, service status, job type, flags, designation, product category, and fault complexity are
  normalized to canonical values. Unknown priority/status values, unknown branches/products, and
  defaulted complexity values are counted in the quality log.
- Dates and timestamps use the explicit formats in `utils.py`; malformed non-empty values are set
  missing and counted. Invalid assignment/arrival ordering is retained as a flagged row with the
  broken timestamp excluded from relevant calculations.
- Repair durations in `HH:MM` are converted to hours. Values above five times their job-type median
  are divided by ten only when the result is plausible; otherwise they are set missing. CSAT values
  outside 1–5 are set missing.
- Contract/proposal duplicates, unknown employee references, invalid ratings, and invalid date values
  are recorded as aggregate counts. Free-text feedback and manager comments stay local; six-digit
  employee-number strings in persisted text are redacted.

Latest aggregate counts are available in [DATA_QUALITY_REPORT.md](./DATA_QUALITY_REPORT.md) and in
the dashboard's **Data & preprocessing** workspace.

## KPI attribution and formulas

KPI rows are attributed to the role-specific employee and period below. Only observations that meet
the configured role minimum are stored (`MIN_N`); CSAT uses its five-response minimum. Every stored
record includes `n_obs`.

| Role | KPI | Attribution and calculation |
|---|---|---|
| Technician | SLA compliance | Request month; completed eligible jobs completed by SLA due time / eligible completed jobs |
| Technician | First-time fix | Original completed breakdown/installation jobs mature by 14 days before extract; no child repeat / mature originals |
| Technician | MTTR | Mean active repair duration for completed breakdown jobs |
| Technician | Response time | Mean working hours from request to arrival for P1–P3 with valid timestamps |
| Technician | Repeat service | Mature completed originals that triggered a repeat / mature completed originals |
| Technician | Report completion | Complete reports / completed jobs with a recorded report flag |
| Technician | CSAT | Mean valid 1–5 customer response |
| Technician | Completion rate | Mature non-cancelled assigned jobs completed within five working days / mature assigned jobs |
| TPO - Service | Assignment time | Median working minutes from request to assignment for P1–P3 |
| TPO - Service | Assignment accuracy | Assigned jobs without reassignment / assigned jobs with a recorded flag |
| TPO - Service | Unassigned rate | P1–P3 non-cancelled jobs taking over 240 working minutes to assign or still unassigned after that duration |
| TPO - Service | SLA monitoring | P1–P3 jobs with a pre-breach alert before the due time / eligible jobs |
| TPO - Service | Processing accuracy | Closed jobs without an administrative-error flag / closed jobs with a recorded flag |
| TPO - Service | Closure time | Mean working hours from completion to administrative closure, attributed to the closer |
| TPO - Service | Pending case rate | Completed jobs still open or closed more than 1,020 working minutes after completion |
| TPO - Service | Documentation completeness | Closed jobs with complete record flag / closed jobs with a recorded flag |
| AMC processing | Processing time | Median working days from approval to creation for new contracts, by creation month |
| AMC processing | Contract accuracy | Created contracts without a correction-required flag / created contracts with a recorded flag |
| AMC processing | Completion rate | New contracts approved in the cohort month and created within three working days / matured new approvals |
| AMC processing | Renewal follow-up | Due-month renewals followed up at least 30 calendar days before renewal / due renewals |
| AMC processing | PM scheduling | Created contracts scheduled within seven calendar days / created contracts |
| AMC processing | Pending contract rate | New approvals not created within five working days / matured new approvals |
| AMC processing | Data completeness | Created contracts with complete input / created contracts with a recorded flag |
| Contracts coordinator | Contact response | Mean working hours from proposal to first contact |
| Contracts coordinator | Follow-up compliance | On-time matched follow-up items / due follow-up items; each due date greedily matches the first unused completion in `[due, due + 7 days]` |
| Contracts coordinator | Follow-up completion | Matched due follow-up items / due follow-up items |
| Contracts coordinator | Conversion | Mature proposal cohorts accepted within 45 calendar days / proposals issued in the cohort month |
| Contracts coordinator | Proposal cycle | Median calendar days from proposal to acceptance for accepted proposals in the cohort |
| Contracts coordinator | Rejection reason | Rejected proposals with a recorded reason / rejected proposals |

Working-hours calculations use `src/services/working_time.py`: weekdays 08:30–17:00, Saturday
08:30–13:00, Sundays closed, and exported fixed-date holidays closed. A working day is 510 working
minutes.

## Missing data, maturity, and performance scores

- First-time fix and repeat service have a one-month maturity lag. Conversion and proposal-cycle
  measures have a two-month lag. `load_bundle(as_of)` excludes values that have not matured by the
  selected period.
- A role-weighted monthly performance score is produced only when at least 85% of the role's
  registered KPIs are present and every weighted category has a KPI. Incomplete months remain
  missing and do not improve the composite by omission.
- The role-wide 2024 mean and standard deviation center each KPI score at 75; one standard deviation
  changes the score by 12 points, clipped to 0–100. Category scores use the role weights in
  `src/schemas/kpi.py`.
- An employee is not assessed when the latest complete month is more than the role's maximum KPI lag
  plus one month behind, fewer than six complete months exist, or the three latest complete months
  span more than four calendar months. At least 15 leave days in the latest attendance month are
  reported as extended leave context. Insufficient-data employees are excluded from peer shares and
  receive no diagnosis or recommendation.
- Trajectories are confirmed only through that employee's last complete month. Later points through
  the selected year's end are estimated from recent complete scores and are labeled as estimates.

## Context and diagnosis

Workload is normalized against the employee's own 2024 monthly work volume and the same-role
seasonal change in total work volume. Parts-wait and incomplete-input evidence are recent-three-month
shares minus each employee's 2024 average. Competitor and pricing context is assigned to contract
coordinators; equipment age is unavailable in the export and is stored as zero.

Diagnosis weights are named in `src/services/diagnosis.py`. Process evidence includes same-role
declines, system downtime, parts-wait growth, incomplete incoming records, and process-related
feedback. A parts-wait increase of at least 12 percentage points reduces skill-cause evidence by
0.25. Process and market explanations are not treated as individual responsibility.

## Assumptions and limitations

- The working calendar and fixed holidays follow the documented component calendar. Exported public
  holidays are added to it; moving holidays not present in the export are not inferred.
- Designation and operational labels are mapped using transparent substring/alias rules in
  `cleaning.py`. Unknown role designations stop the run instead of being assigned silently.
- Cohort age uses calendar days; working-time intervals use the shared business calendar.
- Performance scores are decision-support signals, not standalone employment decisions. Context,
  missingness, and the employee's explanation must be reviewed by a manager.
- Exported manager reviews provide context but are not treated as validated deviation/cause labels.
  Evaluation accuracy is unavailable until period-specific, verified outcome labels are supplied as
  `data/verified_outcomes.csv`.
- Historical as-of replays use the current export snapshot. Later corrections can change the values
  that were available at an earlier replay date.

## Diagnosis tuning log

The documented general evidence weights have not been tuned against employee-specific outcome labels.
No employee-specific rules or hidden scenario mappings are used at assessment time.
