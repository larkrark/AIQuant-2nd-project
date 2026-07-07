# main_final baseline HSI overlay 백테스트 노트

- 생성 시각: 2026-06-30 18:43:50

## 1. 목적

이 단계는 HSI 5상태를 최종 baseline 리밸런싱 규칙과 연결하여 EW 전략 대비 성과, Drawdown, Turnover를 비교한다.

## 2. 시점 정합성

- `signal_month_t_to_return_month_t_plus_1`
- 월말 HSI 상태를 다음 달 ETF 월간 수익률에 적용한다.

## 3. 성과 요약

| strategy | months | CAGR_pct | MDD_pct | Sharpe | Calmar | WinRate_pct |
|---|---:|---:|---:|---:|---:|---:|
| EW | 172 | 6.5101 | -13.5711 | 0.8318 | 0.4797 | 60.4651 |
| HSI_final_baseline_overlay | 172 | 7.7323 | -23.4594 | 0.6111 | 0.3296 | 65.1163 |

## 4. Turnover 요약

| strategy | avg_turnover_pct | max_turnover_pct | total_turnover_pct |
|---|---:|---:|---:|
| EW | 0.0000 | 0.0000 | 0.0000 |
| HSI_final_baseline_overlay | 22.0930 | 70.0000 | 3800.0000 |

## 5. 다음 단계

`06_build_relative_speed_diagnostics.py`에서는 HSI 입력 신호들이 위험 악화 또는 위험 완화 방향으로 얼마나 빠르게 움직이는지 진단한다.
