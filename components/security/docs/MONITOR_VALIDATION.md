# Monitor execution and validation

## System configuration

The security workspace has four independent monitors: semantic prompt protection, data minimization, access policy, and behavior anomaly detection. Semantic protection uses the existing Meta Prompt Guard 2 86M implementation. Data minimization uses local Qwen2.5 1.5B through Ollama; it does not use keyword matching or another field selector in normal operation. The existing policy rules and Isolation Forest baseline remain unchanged. The database schema is unchanged.

The known-answer challenge bank now includes two deterministic Data Minimization checks: blocked payroll access and a request that does not access data. They do not validate field selection by Qwen.

The existing reliability model files and previous CSV/PNG results remain historical results from the earlier three-monitor synthetic benchmark. They have not been retrained or revalidated for four monitors. The operational system continues to update trust using available evidence, but no compatible newly validated compromise classifier is automatically loaded.

## Data origin and expected outcomes

- `data/public/injecagent/test_cases_ds_base.jsonl`: converted public InjecAgent attack cases. The benchmark's injection cases provide an attack-present label for evaluating prompt-injection protection. This label does not prove that all downstream agent behavior would be compromised.
- `data/public/injecagent/benign_user_cases.jsonl`: benchmark-derived benign tool-response templates, not natural production messages. Review the benchmark design before treating these as representative negatives.
- `data/evaluation/field_necessity_tasks.csv`: researcher-authored enterprise-inspired requests. Necessary-field ground truth is **unreviewed**. Field-selection precision and recall are intentionally not reported. The requests are not authentic Metropolitan records.
- `data/behavior_baseline/normal_agent_behavior.csv`: Python-generated normal-behavior baseline for the Isolation Forest, not collected enterprise telemetry.
- A fixed, explicitly marked activity context is used for the execution cases because the public benchmark does not contain comparable tool-activity telemetry. Behavior-monitor execution is measured, but behavior-detection accuracy against real application activity cannot be calculated from this input.
- A temporary local SQLite database containing demonstration records is used to check that permitted column selections are enforced at the database-query level. This is not enterprise customer data.

## Execution

From the component root:

```powershell
python scripts\validate_monitor_execution.py --attack-limit 10 --benign-limit 5 --task-limit 12
```

Use `--task-limit 0` to run a Prompt Guard benchmark subset without needing Ollama. An actual model is still required for Prompt Guard tests. To expand the prompt-attack benchmark evaluation:

```powershell
python scripts\validate_monitor_execution.py --attack-limit 100 --benign-limit 17 --task-limit 0
```

For each run the script creates a separate folder under `results/monitor_validation/` containing:

| File | Evidence |
| --- | --- |
| `monitor_observations.csv` | Observed outputs, model latency, decisions, field selections, and SQL projection checks for all four Python monitors |
| `controlled_faults.csv` | Deliberately altered decisions derived from measured output, not naturally compromised monitors |
| `summary.json` | Counts, semantic benchmark decision matches, selected-field SQL checks and missing evaluation categories |
| `manifest.json` | Hashes of used inputs, configurations, and monitor source code, plus model IDs |

The script aborts without reporting an evaluation if Prompt Guard cannot run or if Qwen fails on an authorized field-selection task. The operational dashboard instead returns REVIEW when these protections are unavailable. No silent substitution with rules occurs.

## Validation and publication

1. Check that public benchmark case IDs, file hashes and preprocessing are traceable to the original InjecAgent publication and source repository.
2. Use separate training, validation and final test groups when assembling a larger reliability dataset from measured monitor decisions. Avoid having related cases and their replay variants cross those splits.
3. Apply faults to actual output for controlled fault studies, and always distinguish these from naturally compromised monitors. A forced error's `fault_label=1` means fault *injected*, not that a detector recognized the fault.
4. Have independent authorized reviewers specify minimum necessary database columns before claiming field-selection precision or recall. Do not invent reviewers, approvals, or expert labels.
5. Obtain any necessary ethics determination and company permissions before collecting personal records, staff feedback or production event telemetry.
6. Retain all baseline failures, REVIEW decisions, runtime errors, model versions and negative results. A decision-match count against a benchmark is not proof of real-world security or task success.

A research paper can report controlled empirical executions and reproducibility after runs are completed, but should not claim validation of a newly trained four-monitor reliability model until a sufficiently diverse labelled dataset, grouped holdout evaluation, and an explicit model comparison have been completed.
