# main_final 사건균형지표와 HSI 5상태 정합성 진단 노트

- 생성 시각: 2026-06-30 18:44:02

## 1. 목적

이 단계는 사건균형지표가 HSI 상태분류와 해석상 맞물리는지 확인한다. 사건균형지표는 외부 사건 달력이 아니라 HSI 내부 신호의 위험·완화 누적 흐름을 요약한 보조지표이다.

## 2. 해석 기준

- risk_warning / accident_zone에서는 event_balance가 양수이면 정합적이다.
- risk_relief에서는 event_balance가 음수이면 정합적이다.
- conflict에서는 event_balance 방향보다 event_intensity가 높은지가 중요하다.

## 3. 진단 요약

| diagnostic_item | value | months | status | interpretation |
|---|---:|---:|---|---|
| risk_state_positive_balance_ratio | 0.7083 | 48 | OK | risk_warning/accident_zone에서 사건균형이 위험 우세인지 확인 |
| relief_state_negative_balance_ratio | 0.4359 | 78 | OK | risk_relief에서 사건균형이 완화 우세인지 확인 |
| conflict_medium_or_high_intensity_ratio | 1.0000 | 4 | OK | conflict에서 극단 신호가 많이 누적되는지 확인 |
| valid_months | 165.0000 | 165 | OK | 사건균형지표와 HSI 상태가 모두 유효한 월 수 |

## 4. 상태별 사건균형 요약

| hsi_state | months | mean_event_balance | mean_event_intensity |
|---|---:|---:|---:|
| accident_zone | 34 | 0.138783 | 0.571371 |
| conflict | 4 | 0.035004 | 0.545950 |
| insufficient_data | 4 | nan | nan |
| neutral_watch | 35 | 0.044387 | 0.504560 |
| risk_relief | 81 | -0.024328 | 0.534876 |
| risk_warning | 14 | -0.019932 | 0.496537 |

## 5. 다음 단계

`09_event_balance_filter_backtest.py`에서는 사건균형지표를 HSI 상태를 대체하는 신호가 아니라 ±5~10%p 보조 비중 조정 필터로 제한하여 실험한다.
