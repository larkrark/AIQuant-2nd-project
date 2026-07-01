# main_final θ 민감도 실험 노트

- 생성 시각: 2026-06-30 18:44:18

## 1. 목적

θ 실험은 최고 CAGR을 찾는 최적화가 아니라, HSI 상태분류 기준이 조금 바뀌어도 상태분포, MDD, Turnover, Sharpe, Calmar가 크게 무너지지 않는지 확인하는 민감도 검증이다.

## 2. θ 후보

- 후보: [0.1, 0.15, 0.2, 0.25, 0.3]
- 기준값: 0.15

## 3. 성과 요약

| strategy | theta | CAGR_pct | MDD_pct | Sharpe | Calmar |
|---|---:|---:|---:|---:|---:|
| EW |  | 6.5101 | -13.5711 | 0.8318 | 0.4797 |
| theta_0.10 | 0.10 | 7.5025 | -21.7198 | 0.5972 | 0.3454 |
| theta_0.15 | 0.15 | 7.7323 | -23.4594 | 0.6111 | 0.3296 |
| theta_0.20 | 0.20 | 7.7153 | -20.2428 | 0.6210 | 0.3811 |
| theta_0.25 | 0.25 | 7.4423 | -20.8232 | 0.6194 | 0.3574 |
| theta_0.30 | 0.30 | 7.7368 | -20.8232 | 0.6397 | 0.3715 |

## 4. 후보 판단

- EW: benchmark — 동일가중 비교 기준
- theta_0.10: review_turnover — 상태 전환이 잦아 Turnover 확인 필요
- theta_0.15: baseline_theta — 기준 θ
- theta_0.20: review_turnover — 상태 전환이 잦아 Turnover 확인 필요
- theta_0.25: review_turnover — 상태 전환이 잦아 Turnover 확인 필요
- theta_0.30: review_turnover — 상태 전환이 잦아 Turnover 확인 필요
