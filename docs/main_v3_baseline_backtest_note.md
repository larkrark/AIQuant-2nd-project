# main_v3 baseline backtest note

- 생성 시각: 2026-06-29 23:16:39

## 1. 목적

33번에서 생성한 HSI 5상태표를 main_v2b 기준 비중 규칙에 연결하여 baseline 백테스트를 수행하였다. 이 결과는 후속 추가 지표 실험과 비교할 기준선이다.

## 2. 비중 규칙

- `conflict`는 즉시 방어 전환하지 않고 동일비중 관찰로 처리한다.
- `risk_warning`과 `accident_zone`에서만 위험자산 비중을 축소한다.
- 위험자산 축소분은 114260과 153130에 균등하게 배분한다.

## 3. 시점 정합성

월말 HSI 상태는 다음 달 수익률에 적용하였다. 즉, `signal_month`의 상태를 `return_month = signal_month + 1`에 적용한다.

## 4. 성과 요약

| strategy_name | months | total_return_pct | CAGR_pct | MDD_pct | Sharpe | Calmar | WinRate_pct |
|---|---:|---:|---:|---:|---:|---:|---:|
| EW_1_3 | 167 | 3104279126013.23 | 467.43 | -19276.63 | 0.8480 | 0.0242 | 60.48 |
| HSI_main_v2b_baseline | 167 | -3331843627.19 | nan | -54220.72 | 0.8073 | nan | 61.68 |

## 5. Turnover 요약

| strategy_name | avg_turnover_pct | max_turnover_pct | total_turnover_pct |
|---|---:|---:|---:|
| HSI_main_v2b_baseline | 6.03 | 23.33 | 1006.67 |
| EW_1_3 | 0.00 | 0.00 | 0.00 |

## 6. 점검표

| check_item | result | status | note |
|---|---|---|---|
| valid_state_months | 168 | OK | 33번 HSI 상태표에서 state_valid=True인 월 수 |
| signal_months_used | 167 | OK | 다음 달 수익률이 존재해 실제 백테스트에 사용된 신호 월 수 |
| return_months_used | 167 | OK | 실제 백테스트 수익률 월 수 |
| first_valid_state_month | 2012-07 | OK | 첫 유효 HSI 상태 월 |
| last_valid_state_month | 2026-06 | OK | 마지막 유효 HSI 상태 월. 마지막 월은 다음 달 수익률이 없으면 백테스트에서 제외될 수 있음. |
| alignment_rule | signal_month_t_to_return_month_t_plus_1 | OK | 월말 HSI 상태를 다음 달 수익률에 적용하여 look-ahead bias를 피함 |
| monthly_return_unit | input_percent_converted_to_decimal | OK | monthly_returns.csv의 % 수익률을 백테스트 내부에서 decimal로 변환 |

## 7. 다음 단계

다음 단계에서는 추가 지표 후보를 생성하거나 수령한 뒤, 동일한 main_v2b 비중 규칙을 고정한 상태에서 신호 조합만 바꾸어 성과표를 비교한다.
