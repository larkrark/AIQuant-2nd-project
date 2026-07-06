# main_final HSI 5상태 기준선 생성 노트

- 생성 시각: 2026-06-30 18:43:46

## 1. 목적

이 단계는 월말 HSI 점수를 이용해 risk_relief, neutral_watch, conflict, risk_warning, accident_zone의 5상태를 생성한다. HSI는 미래 수익률 예측값이 아니라 시장상태 해석 보조지표이다.

## 2. 상태분류 기준

- 기준 티커: `069500`
- 최소 유효 점수 수: `3`
- θ 기준값: `0.15`
- accident extra: `0.2`
- conflict direction band: `0.2`

## 3. 상태분포

| hsi_state | state_kr | months | ratio_total | ratio_valid |
|---|---|---:|---:|---:|
| risk_relief | 위험 완화 우세 | 81 | 0.4709 | 0.48214285714285715 |
| neutral_watch | 중립 관찰 | 35 | 0.2035 | 0.20833333333333334 |
| conflict | 신호 충돌 | 4 | 0.0233 | 0.023809523809523808 |
| risk_warning | 위험 악화 우세 | 14 | 0.0814 | 0.08333333333333333 |
| accident_zone | 강한 위험 구간 | 34 | 0.1977 | 0.20238095238095238 |
| insufficient_data | 자료 부족 | 4 | 0.0233 |  |

## 4. 품질 점검

| item | value | status | note |
|---|---:|---|---|
| state_table_rows | 172 | OK | 월말 HSI 5상태표 행 수 |
| valid_state_months | 168 | OK | insufficient_data 제외 유효 상태 월 수 |
| first_valid_month | 2012-07 | OK | 첫 유효 상태 월 |
| last_valid_month | 2026-06 | OK | 마지막 유효 상태 월 |
| state_type_count | 5 | OK | 유효 상태 종류 수 |
| alignment_preview_rows | 172 | OK | signal_month t → return_month t+1 정렬 미리보기 행 수 |
| alignment_missing_return_cells | 3 | OK | 마지막 월은 다음 달 수익률이 없어 정상 결측 가능 |

## 5. 다음 단계

`05_backtest_baseline_allocation_rule.py`에서 이 상태표를 최종 baseline 리밸런싱 규칙과 연결해 EW 대비 HSI overlay 성과, Drawdown, Turnover를 계산한다.
