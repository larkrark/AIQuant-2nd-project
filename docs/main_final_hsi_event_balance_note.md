# main_final HSI 사건균형·위험누적지표 생성 노트

- 생성 시각: 2026-06-30 18:43:39

## 1. 목적

사건균형지표는 외부 사건 달력이 아니라, HSI 입력 신호 자체에서 위험 악화 또는 위험 완화 방향의 극단 신호가 최근 기간 동안 얼마나 반복되었는지 확인하는 내부 보조지표이다.

## 2. 계산 방식

1. 각 원신호를 HSI 위험 방향 기준으로 통일한다.
2. ETF별·신호별 과거 rolling 분포에서 20분위수와 80분위수를 계산한다.
3. 현재 값이 80분위수 이상이면 위험 사건, 20분위수 이하이면 완화 사건으로 표시한다.
4. 날짜별 위험 사건 비율과 완화 사건 비율을 계산한다.
5. 사건균형과 사건강도를 계산한다.

```text
event_balance = risk_event_ratio - relief_event_ratio
event_intensity = risk_event_ratio + relief_event_ratio
```

## 3. 해석

- event_balance > 0: 위험 사건 우세
- event_balance < 0: 완화 사건 우세
- event_intensity 높음: 방향과 무관하게 극단 신호가 많음
- event_balance ≈ 0 이고 event_intensity 높음: 위험·완화 신호가 충돌하는 혼합 국면 가능성

## 4. 사용 신호

| signal | family | direction_sign | note |
|---|---|---:|---|
| ret_1m | return | -1 | 원신호가 클수록 위험 완화 방향이므로 -1을 곱해 위험 방향으로 통일한다. |
| ret_3m | return | -1 | 원신호가 클수록 위험 완화 방향이므로 -1을 곱해 위험 방향으로 통일한다. |
| ma_gap | trend | -1 | 원신호가 클수록 위험 완화 방향이므로 -1을 곱해 위험 방향으로 통일한다. |
| momentum | trend | -1 | 원신호가 클수록 위험 완화 방향이므로 -1을 곱해 위험 방향으로 통일한다. |
| volatility | risk_damage | 1 | 원신호가 클수록 위험 악화 방향으로 해석한다. |
| relative_strength | relative_strength | -1 | 원신호가 클수록 위험 완화 방향이므로 -1을 곱해 위험 방향으로 통일한다. |
| ret_6m | return | -1 | 원신호가 클수록 위험 완화 방향이므로 -1을 곱해 위험 방향으로 통일한다. |
| ret_12m | return | -1 | 원신호가 클수록 위험 완화 방향이므로 -1을 곱해 위험 방향으로 통일한다. |
| drawdown | risk_damage | -1 | 원신호가 클수록 위험 완화 방향이므로 -1을 곱해 위험 방향으로 통일한다. |
| shock_count | risk_damage | 1 | 원신호가 클수록 위험 악화 방향으로 해석한다. |
| defensive_rs | relative_strength | -1 | 원신호가 클수록 위험 완화 방향이므로 -1을 곱해 위험 방향으로 통일한다. |

## 5. 생성 결과 요약

| item | value | status | note |
|---|---|---|---|
| input_file | C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\data\processed\main_final_signal_inputs.csv | OK | 01번에서 생성한 HSI 원신호 입력표 |
| signal_columns | ret_1m, ret_3m, ma_gap, momentum, volatility, relative_strength, ret_6m, ret_12m, drawdown, shock_count, defensive_rs | OK | 사건균형지표 계산에 사용한 신호 |
| quantile_rule | q20=0.2, q80=0.8 | OK | q80 이상 위험 사건, q20 이하 완화 사건 |
| rolling_window | 252 | OK | 과거 분위수 계산 기준 길이 |
| min_periods | 60 | OK | 분위수 계산 최소 관측치 |
| time_weights | {'1m': 0.4, '3m': 0.3, '6m': 0.2, '12m': 0.1} | OK | 13612W 시간가중 구조 |
| flag_rows | 10461 | OK | ETF·날짜별 사건 플래그 행 수 |
| daily_rows | 3487 | OK | 일별 사건균형지표 행 수 |
| monthly_rows | 172 | OK | 월말 사건균형지표 행 수 |
| first_valid_daily_13612w | 2012-10-02 00:00:00 | OK | 13612W 지표가 처음 유효해진 일자 |
| first_valid_monthly_13612w | 2012-10 | OK | 13612W 월말 지표가 처음 유효해진 월 |
| event_balance_mean | 0.02567 | OK | 월말 사건균형 13612W 평균 |
| event_intensity_mean | 0.532981 | OK | 월말 사건강도 13612W 평균 |

## 6. 다음 단계

다음 단계에서는 월말 사건균형지표를 HSI 5상태표와 대조하여 risk_warning, accident_zone, conflict 상태에서 사건균형과 사건강도가 해석상 정합적인지 확인한다.
