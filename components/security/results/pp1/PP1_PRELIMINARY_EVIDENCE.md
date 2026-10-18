# PP1 Preliminary Research Evidence

## 1. Monitor-Reliability Model Comparison

```
              model  precision  recall       f1    auprc      fpr
      random_forest   0.969697 1.00000 0.984615 1.000000 0.015625
            xgboost   0.969697 1.00000 0.984615 0.999053 0.015625
logistic_regression   0.968750 0.96875 0.968750 0.999053 0.015625
   isolation_forest   0.939394 0.96875 0.953846 0.995337 0.031250
```

## 2. Final Security Decision Strategy Comparison

```
                strategy  final_decision_accuracy  attack_success_rate  false_block_rate  review_rate
            single_guard                 0.526042             0.389049          0.300912     0.174479
          equal_majority                 0.835938             0.152738          0.151976     0.113281
        static_weighting                 0.623698             0.043228          0.006079     0.429688
adaptive_trust_weighting                 0.752604             0.005764          0.006079     0.322917
```

## 3. Proposed Adaptive Method by Compromised-Monitor Count

```
compromised_count  final_decision_accuracy  attack_success_rate  false_block_rate
                0                 0.833333              0.00000          0.000000
                1                 0.862847              0.00000          0.004065
                2                 0.010417              0.04878          0.023810
```

## 4. Evidence Ablation

```
evidence_mode probability_model  final_decision_accuracy  attack_success_rate  false_block_rate  review_rate
         full     random_forest                 0.752604             0.005764          0.006079     0.322917
   model_only     random_forest                 0.759115             0.005764          0.006079     0.316406
 no_challenge     random_forest                 0.755208             0.005764          0.006079     0.317708
    no_policy     random_forest                 0.753906             0.005764          0.006079     0.321615
```

## 5. Dynamic Compromise / Recovery

- Probability model: `random_forest`
- Monitor: `policy-monitor`
- Compromise condition: `FALSE_ALLOW`
- Detection delay: `2` windows
- Recovery delay: `3` windows
- Minimum trust: `0.2474`
- Final trust: `0.9227`

## Interpretation Boundary

These are preliminary PP1 results from a controlled research benchmark. They demonstrate the implemented experimental pipeline and support baseline comparison, but they must not be reported as production enterprise performance.
