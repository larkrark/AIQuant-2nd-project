# main_final 상대속도 진단 노트

- 생성 시각: 2026-06-30 18:43:53

## 1. 목적

상대속도 실험은 선행/후행지표 예측 실험이 아니라, HSI 내부 신호들이 전체 중심 흐름보다 위험 악화 또는 위험 완화 방향으로 얼마나 빠르게 움직이는지 진단하는 실험이다.

## 2. 계산식

```text
signal_velocity   = signal_score_t - signal_score_t-1
centroid_score    = 같은 월·같은 ETF의 HSI 점수 평균
centroid_velocity = centroid_score_t - centroid_score_t-1
relative_velocity = signal_velocity - centroid_velocity
```

## 3. 해석

- relative_velocity > 0: 해당 신호가 중심보다 위험 악화 방향으로 빠르게 움직임
- relative_velocity < 0: 해당 신호가 중심보다 위험 완화 방향으로 빠르게 움직임
- moving_with_centroid: 전체 HSI 중심 흐름과 비슷하게 움직임

## 4. 품질 점검

| item | value | status | note |
|---|---:|---|---|
| relative_speed_rows | 2580 | OK | 상대속도 long 전체 행 수 |
| valid_relative_velocity_rows | 2341 | OK | relative_velocity 유효 행 수 |
| ticker_count | 3 | OK | 상대속도 계산 대상 ETF 수 |
| signal_count | 5 | OK | 상대속도 계산 대상 신호 수 |
| first_valid_month | 2012-07 | OK | 상대속도 첫 유효 월 |
| last_valid_month | 2026-06 | OK | 상대속도 마지막 유효 월 |
| rank_table_rows | 669 | OK | 069500 기준 월별 상대속도 상위 신호표 행 수 |
| state_summary_rows | 25 | OK | HSI 상태별 상대속도 요약표 행 수 |

## 5. 다음 단계

`07_run_signal_combo_backtests.py`에서는 기본 신호, 확장 신호, 상대속도 진단 결과를 어떻게 전략 비교에 연결할지 실험한다.
