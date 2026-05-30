# FinBERT Benchmark Report

Generated: 2026-05-30 19:20:06
Model: ProsusAI/finbert
Device: cpu

## Summary

### FiQA
- Samples: 3100
- Accuracy: 0.8968
- Macro F1-score: 0.8924
- Status: PASS - Meets 75% F1-score target

| Label | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| negative | 0.8341 | 0.9738 | 0.8986 | 382 |
| neutral | 0.9668 | 0.8645 | 0.9128 | 1852 |
| positive | 0.8086 | 0.9319 | 0.8659 | 866 |

Confusion matrix (rows=true, cols=pred): [[372, 6, 4], [64, 1601, 187], [10, 49, 807]]

### FinancialPhraseBank
- Samples: 970
- Accuracy: 0.8649
- Macro F1-score: 0.8561
- Status: PASS - Meets 75% F1-score target

| Label | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| negative | 0.7547 | 0.9600 | 0.8451 | 125 |
| neutral | 0.9439 | 0.8336 | 0.8853 | 565 |
| positive | 0.7949 | 0.8857 | 0.8378 | 280 |

Confusion matrix (rows=true, cols=pred): [[120, 3, 2], [32, 471, 62], [7, 25, 248]]

## Confusion Matrix Visualization

Image: confusion_matrix.png (left-to-right: FiQA, FinancialPhraseBank)
