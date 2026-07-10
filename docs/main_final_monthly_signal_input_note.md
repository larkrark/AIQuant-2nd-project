# main_final 월말 HSI 신호 입력표 정리 노트

- 생성 시각: 2026-06-30 18:43:43

## 1. 목적

이 단계는 일별 HSI 점수, direction, raw 3단계 signal, 원신호 입력표, 사건균형지표를 월말 기준으로 정리하여 다음 단계의 HSI 5상태 분류가 바로 사용할 수 있게 만드는 연결 단계이다.

## 2. 시점 정합성

- `signal_month_t_to_return_month_t_plus_1`
- 월말에 관측 가능한 HSI 신호를 다음 달 ETF 월간 수익률에 적용한다.

## 3. 컬럼 역할

| column | source | role |
|---|---|---|
| year_month | derived_or_metadata | 식별자 또는 날짜 정보 |
| score_date | hsi_scaled_scores | 표준화·부호통일·스케일링된 HSI 점수 |
| ticker | derived_or_metadata | 식별자 또는 날짜 정보 |
| ticker_name | derived_or_metadata | 식별자 또는 날짜 정보 |
| ticker_role | derived_or_metadata | 식별자 또는 날짜 정보 |
| score_return | hsi_scaled_scores | 표준화·부호통일·스케일링된 HSI 점수 |
| score_ma_pos | hsi_scaled_scores | 표준화·부호통일·스케일링된 HSI 점수 |
| score_momentum | hsi_scaled_scores | 표준화·부호통일·스케일링된 HSI 점수 |
| score_vol | hsi_scaled_scores | 표준화·부호통일·스케일링된 HSI 점수 |
| score_rs | hsi_scaled_scores | 표준화·부호통일·스케일링된 HSI 점수 |
| direction_date | derived_or_metadata | 식별자 또는 날짜 정보 |
| hsi_direction | hsi_direction | HSI 위험 악화/완화 방향 점수 |
| raw3_signal_date | derived_or_metadata | 식별자 또는 날짜 정보 |
| raw3_signal | hsi_signal | 데이터 파트 3단계 raw signal |
| raw_signal_date | derived_or_metadata | 식별자 또는 날짜 정보 |
| ret_1m | signal_inputs | 부호 반전 전 원신호 |
| ret_3m | signal_inputs | 부호 반전 전 원신호 |
| ma_gap | signal_inputs | 부호 반전 전 원신호 |
| momentum | signal_inputs | 부호 반전 전 원신호 |
| volatility | signal_inputs | 부호 반전 전 원신호 |
| relative_strength | signal_inputs | 부호 반전 전 원신호 |
| ret_6m | signal_inputs | 부호 반전 전 원신호 |
| ret_12m | signal_inputs | 부호 반전 전 원신호 |
| drawdown | signal_inputs | 부호 반전 전 원신호 |
| shock_count | signal_inputs | 부호 반전 전 원신호 |
| defensive_rs | signal_inputs | 부호 반전 전 원신호 |
| event_balance_raw | event_balance_monthly | 20/80 분위수 기반 사건균형·위험누적지표 |
| event_intensity_raw | event_balance_monthly | 20/80 분위수 기반 사건균형·위험누적지표 |
| event_balance_13612w | event_balance_monthly | 20/80 분위수 기반 사건균형·위험누적지표 |
| event_intensity_13612w | event_balance_monthly | 20/80 분위수 기반 사건균형·위험누적지표 |
| event_balance_13612w_label | event_balance_monthly | 20/80 분위수 기반 사건균형·위험누적지표 |
| event_intensity_13612w_label | event_balance_monthly | 20/80 분위수 기반 사건균형·위험누적지표 |

## 4. 품질 점검 요약

| item | value | status | note |
|---|---:|---|---|
| monthly_scores_wide_rows | 172 | OK | 월말 HSI score wide 행 수 |
| monthly_signal_long_rows | 516 | OK | 월말 HSI signal long 행 수 |
| monthly_signal_wide_rows | 172 | OK | 월말 HSI signal wide 행 수 |
| ticker_count_in_long | 3 | OK | long table 내 ETF 수 |
| first_signal_month | 2012-03 | OK | 월말 신호 첫 월 |
| last_signal_month | 2026-06 | OK | 월말 신호 마지막 월 |
| alignment_preview_rows | 172 | OK | signal_month t → return_month t+1 정렬 행 수 |
| alignment_missing_return_cells | 3 | OK | 마지막 월은 다음 달 수익률이 없어 정상 결측 가능 |
| event_balance_columns_merged | event_balance_raw, event_intensity_raw, event_balance_13612w, event_intensity_13612w, event_balance_13612w_label, event_intensity_13612w_label | OK | 02번 결과가 있으면 월말 신호표에 병합 |

## 5. 다음 단계

다음 단계인 `04_build_hsi_state5_baseline.py`에서는 `main_final_monthly_signal_inputs_long.csv`를 사용해 risk_relief, neutral_watch, conflict, risk_warning, accident_zone의 HSI 5상태를 생성한다.
