# main_v3 HSI 5상태 분류 노트

- 생성 시각: 2026-06-29 23:16:34

## 1. 목적

32번에서 생성한 월말 HSI 신호 입력표를 사용해 HSI 5상태 분류표를 생성하였다. 이번 단계는 비중 조정과 백테스트로 넘어가기 전, 월말 신호가 상태분류로 연결되는지 확인하는 단계이다.

## 2. 상태 정의

| 상태 | 의미 |
|---|---|
| risk_relief | 위험 완화 우세 |
| neutral_watch | 관찰·중립 |
| conflict | 위험 악화 신호와 위험 완화 신호가 충돌 |
| risk_warning | 위험 악화 우세 |
| accident_zone | 강한 위험 악화 |
| insufficient_data | rolling 계산 초기 구간 등으로 신호 부족 |

## 3. 사용 신호

상태분류는 위험자산 대표 ETF인 `069500`의 핵심 신호를 기준으로 계산하였다. `069500`은 상대강도 benchmark이므로 `score_rs`는 자기비교 값으로 보아 상태분류에서 제외하였다.

사용 신호:

- `score_return`
- `score_ma_pos`
- `score_momentum`
- `score_vol`

## 4. 상태분포

| hsi_state | state_valid | month_count | share_all_months | share_valid_months |
|---|---|---:|---:|---:|
| risk_relief | True | 66 | 0.3837 | 0.3929 |
| neutral_watch | True | 10 | 0.0581 | 0.0595 |
| conflict | True | 48 | 0.2791 | 0.2857 |
| risk_warning | True | 13 | 0.0756 | 0.0774 |
| accident_zone | True | 31 | 0.1802 | 0.1845 |
| insufficient_data | False | 4 | 0.0233 |  |

## 5. 품질 점검

| check_item | result | status | note |
|---|---|---|---|
| hsi_state_table_shape | 172 rows x 19 columns | OK | 월별 HSI 상태표 생성 여부 |
| valid_state_months | 168 | OK | warm-up 이후 상태분류 가능 월 수 |
| insufficient_data_months | 4 | INFO | rolling 계산 초기 구간은 insufficient_data가 자연스러움 |
| first_valid_month | 2012-07 | OK | 백테스트 연결 시 이 시점 이후 사용 권장 |
| last_valid_month | 2026-06 | OK | 상태분류 마지막 월 |
| valid_state_types | accident_zone, conflict, neutral_watch, risk_relief, risk_warning | OK | 한 가지 상태만 나오면 기준 조정 필요 |
| alignment_preview_shape | 171 rows x 13 columns | OK | 월말 HSI 상태와 다음 달 수익률 연결 preview |

## 6. 다음 단계

다음 단계에서는 이 HSI 상태표를 `main_v2b` 기준 비중 규칙에 연결하여 월별 리밸런싱 비중표를 생성한다. 이후 월간 수익률과 결합해 백테스트로 넘어간다.
