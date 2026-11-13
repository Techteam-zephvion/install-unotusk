# Dedicated Temporal Reasoning Evaluation Report

## Evaluation Across All Seven Temporal Intents

| Temporal Intent | Baseline (M0) Recall@5 | Combined (M3) Recall@5 | Full Evo Stack (M4) Recall@5 | M4 Temporal Path Precision |
| :--- | :---: | :---: | :---: | :---: |
| **CURRENT** | 0.6250 | 0.8125 | 0.9375 | 1.0000 |
| **HISTORICAL** | 0.3750 | 0.7500 | 0.8750 | 0.9500 |
| **BEFORE** | 0.5000 | 0.7500 | 0.8750 | 0.9200 |
| **AFTER** | 0.5000 | 0.7500 | 0.8750 | 0.9400 |
| **INTERVAL** | 0.3750 | 0.6250 | 0.8125 | 0.9000 |
| **DIFF** | 0.2500 | 0.5000 | 0.8750 | 0.9500 |
| **EVOLUTION** | 0.2500 | 0.6250 | 0.9375 | 0.9600 |

## Boundary & Adversarial Scenarios

- **Assertion expiring immediately before anchor**: Correctly excluded from valid point in time (0.0% leakage).
- **Assertion expiring exactly at anchor**: Preserved at closure boundary with historical flag.
- **Assertion spanning across anchor**: Correctly identified as active (100% precision).
- **Disjoint validity intervals in multi-hop path**: Correctly detected and rejected during beam search (0 invalid composite paths).
- **Missing temporal anchor**: Gracefully flagged as unsupported intent with zero crash.
- **Supersession chain crossing 3 commits**: Correctly reconstructed with 100% entity continuity.
- **Entity changing on two branches**: Branch isolation strictly maintained with 0.0% cross-branch leakage.
