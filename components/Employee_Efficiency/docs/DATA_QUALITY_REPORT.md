# Data quality report

Generated from aggregate preprocessing counts. No employee identifiers or row-level values are included.

## Row counts

| Source file | Before | After |
|---|---:|---:|
| amc_contracts.csv | 5005 | 5005 |
| amc_proposals.csv | 7256 | 7220 |
| branch_territory_map.csv | 17 | 17 |
| competitor_notes.csv | 105 | 105 |
| employee_feedback.csv | 886 | 886 |
| employees.csv | 34 | 34 |
| hr_attendance_monthly.csv | 1122 | 1122 |
| hr_reviews.csv | 136 | 136 |
| price_list_changes.csv | 3 | 3 |
| public_holidays.csv | 15 | 15 |
| service_jobs.csv | 33326 | 33148 |
| system_downtime_log.csv | 57 | 57 |

## Cleaning actions

| Stage | Source file | Rule | Rows affected | Action | Detail |
|---|---|---|---:|---|---|
| cleaning | employees.csv | duplicate_employee_number | 0 | drop |  |
| cleaning | employees.csv | file_total_rows | 0 | clean | Aggregate source row counts. |
| cleaning | branch_territory_map.csv | file_total_rows | 0 | clean | Aggregate source row counts. |
| cleaning | public_holidays.csv | file_total_rows | 0 | clean | Aggregate source row counts. |
| cleaning | service_jobs.csv | test_records | 13 | drop |  |
| cleaning | service_jobs.csv | exact_duplicates | 165 | drop |  |
| cleaning | service_jobs.csv | duplicate_job_id | 0 | drop |  |
| cleaning | service_jobs.csv | assigned_by_normalized | 514 | normalize |  |
| cleaning | service_jobs.csv | technician_no_invalid_or_unknown | 283 | set_missing | Employee references not present in employees.csv. |
| cleaning | service_jobs.csv | technician_no_normalized | 791 | normalize |  |
| cleaning | service_jobs.csv | closed_by_invalid_or_unknown | 634 | set_missing | Employee references not present in employees.csv. |
| cleaning | service_jobs.csv | closed_by_normalized | 1125 | normalize |  |
| cleaning | service_jobs.csv | priority_variants | 5000 | normalize |  |
| cleaning | service_jobs.csv | repeat_visit_flag_boolean | 33148 | normalize |  |
| cleaning | service_jobs.csv | report_complete_boolean | 33148 | normalize |  |
| cleaning | service_jobs.csv | reassigned_flag_boolean | 33148 | normalize |  |
| cleaning | service_jobs.csv | admin_error_flag_boolean | 33148 | normalize |  |
| cleaning | service_jobs.csv | record_complete_flag_boolean | 33148 | normalize |  |
| cleaning | service_jobs.csv | product_category_unknown | 0 | classify_unknown |  |
| cleaning | service_jobs.csv | probable_x10_repair_typos | 142 | divide_by_10 | Outliers corrected only when the scaled value was plausible. |
| cleaning | service_jobs.csv | implausible_repair_time | 2 | set_missing |  |
| cleaning | service_jobs.csv | timestamp_order | 147 | set_invalid_timestamp_missing |  |
| cleaning | service_jobs.csv | completed_without_arrival | 237 | retain_missing | Excluded from response-time calculations. |
| cleaning | service_jobs.csv | file_total_rows | 178 | clean | Aggregate source row counts. |
| cleaning | amc_proposals.csv | duplicate_proposals | 36 | drop |  |
| cleaning | amc_proposals.csv | coordinator_no_normalized | 112 | normalize |  |
| cleaning | amc_proposals.csv | processor_no_invalid_or_unknown | 5332 | set_missing | Employee references not present in employees.csv. |
| cleaning | amc_proposals.csv | processor_no_normalized | 5364 | normalize |  |
| cleaning | amc_proposals.csv | file_total_rows | 36 | clean | Aggregate source row counts. |
| cleaning | amc_contracts.csv | duplicate_contracts | 0 | drop |  |
| cleaning | amc_contracts.csv | processor_no_normalized | 63 | normalize |  |
| cleaning | amc_contracts.csv | file_total_rows | 0 | clean | Aggregate source row counts. |
| cleaning | hr_attendance_monthly.csv | file_total_rows | 0 | clean | Aggregate source row counts. |
| cleaning | system_downtime_log.csv | file_total_rows | 0 | clean | Aggregate source row counts. |
| cleaning | price_list_changes.csv | file_total_rows | 0 | clean | Aggregate source row counts. |
| cleaning | competitor_notes.csv | file_total_rows | 0 | clean | Aggregate source row counts. |
| cleaning | hr_reviews.csv | file_total_rows | 0 | clean | Aggregate source row counts. |
| cleaning | employee_feedback.csv | file_total_rows | 0 | clean | Aggregate source row counts. |
| aggregation | all source files | outside_configured_period | 147 | exclude | Retained periods 2024-01 through 2026-09. |
