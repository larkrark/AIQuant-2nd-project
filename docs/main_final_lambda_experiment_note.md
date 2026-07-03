# main_final λ 기반 포트폴리오 관성 실험 노트

- 생성 시각: 2026-06-30 18:44:13

## 1. 목적

λ 실험은 HSI 상태가 바뀔 때 목표 비중으로 한 번에 이동하는 것이 좋은지, 또는 일부만 이동하는 것이 더 안정적인지 확인하는 실험이다.

## 2. 공식

```text
actual_weight_t = previous_weight + λ × (target_weight_t - previous_weight)
```

## 3. 성과 요약

| strategy | lambda | CAGR_pct | MDD_pct | Sharpe | Calmar |
|---|---:|---:|---:|---:|---:|
| EW |  | 6.5101 | -13.5711 | 0.8318 | 0.4797 |
| lambda_0.1 | 0.1 | 8.6551 | -14.7442 | 0.7935 | 0.5870 |
| lambda_0.3 | 0.3 | 9.0852 | -15.2197 | 0.7818 | 0.5969 |
| lambda_0.5 | 0.5 | 8.5773 | -17.5193 | 0.7353 | 0.4896 |
| lambda_0.7 | 0.7 | 8.0646 | -19.9646 | 0.6819 | 0.4039 |
| lambda_1.0 | 1.0 | 7.7323 | -23.4594 | 0.6111 | 0.3296 |

## 4. Turnover 요약

| strategy | avg_turnover_pct | max_turnover_pct | total_turnover_pct |
|---|---:|---:|---:|
| EW | 0.0000 | 0.0000 | 0.0000 |
| lambda_0.1 | 2.5150 | 6.0171 | 432.5814 |
| lambda_0.3 | 6.9497 | 20.0119 | 1195.3451 |
| lambda_0.5 | 11.1378 | 34.8299 | 1915.7069 |
| lambda_0.7 | 15.4061 | 48.9898 | 2649.8497 |
| lambda_1.0 | 22.0930 | 70.0000 | 3800.0000 |

## 5. 후보 판단

- EW: benchmark — 동일가중 비교 기준
- lambda_0.1: candidate — Turnover가 감소하고 MDD 악화가 제한적
- lambda_0.3: candidate — Turnover가 감소하고 MDD 악화가 제한적
- lambda_0.5: candidate — Turnover가 감소하고 MDD 악화가 제한적
- lambda_0.7: candidate — Turnover가 감소하고 MDD 악화가 제한적
- lambda_1.0: baseline_lambda — 목표 비중 즉시 이동 기준
