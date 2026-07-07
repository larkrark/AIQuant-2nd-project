# main_final 최종 후보 선정 노트

- 생성 시각: 2026-07-01 01:14:50

## 1. 목적

이 단계는 00~11번 실험에서 생성된 백테스트 시계열을 모아 Turnover 필터, 거래비용 민감도, MDD, Sharpe, Calmar 기준을 적용해 최종 후보군을 선별한다. 최고 CAGR 하나를 고르는 것이 아니라 방어형 overlay로 해석 가능한 후보를 압축하는 절차이다.

## 2. 거래비용 계산

```text
월별 거래비용 = 월별 Turnover × 거래비용률
비용 차감 후 월수익률 = 기존 월수익률 - 월별 거래비용
```

거래비용률 후보는 다음과 같다.

| label | cost_rate | 해석 |
|---|---:|---|
| cost_0bp | 0.0000 | 비용 미반영 기준 |
| cost_5bp | 0.0005 | 낮은 비용 가정 |
| cost_10bp | 0.0010 | 보통 비용 가정 |
| cost_20bp | 0.0020 | 보수적 비용 가정 |

## 3. 입력 파일

| source_file | source_type | rows | status | strategies |
|---|---|---:|---|---|
| main_final_baseline_backtest_timeseries.csv | baseline | 344 | OK | EW, HSI_final_baseline_overlay |
| main_final_event_balance_filter_backtest_timeseries.csv | event_balance_filter | 516 | OK | EW, HSI_event_balance_filter_overlay, HSI_final_baseline_overlay |
| main_final_lambda_backtest_timeseries.csv | lambda | 1032 | OK | EW, lambda_0.1, lambda_0.3, lambda_0.5, lambda_0.7, lambda_1.0 |
| main_final_signal_combo_backtest_timeseries.csv | signal_combo | 1032 | OK | EW, combo_00_core5, combo_01_core4_no_rs, combo_02_trend_only, combo_03_risk_damage_focus, combo_04_core5_plus_relative_speed |
| main_final_theta_backtest_timeseries.csv | theta | 1032 | OK | EW, theta_0.10, theta_0.15, theta_0.20, theta_0.25, theta_0.30 |

## 4. 최종 후보 판단 기준

- 대표 비용률: `cost_10bp` = 0.0010
- 엄격 Turnover 기준: 평균 10.0% 이하, 최대 40.0% 이하
- 유연 Turnover 기준: 평균 15.0% 이하, 최대 50.0% 이하
- MDD 기준: EW 대비 3.0%p 이상 악화되지 않을 것
- Sharpe 기준: 0.7 이상
- Calmar 기준: 0.45 이상
- 보수적 비용 기준: 20bp 비용 적용 후 CAGR 손상폭 1.0%p 이하

## 5. 최종 후보 상위표

| decision | source_type | strategy | CAGR | MDD | Sharpe | Calmar | avg_turnover | max_turnover | reason |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| final_candidate | lambda | lambda_0.1 | 8.6225 | -14.7879 | 0.7908 | 0.5831 | 2.5150 | 6.0171 | Turnover, 비용, MDD, Sharpe, Calmar, robustness proxy를 통과함 |
| final_candidate | lambda | lambda_0.3 | 8.9949 | -15.3348 | 0.7749 | 0.5866 | 6.9497 | 20.0119 | Turnover, 비용, MDD, Sharpe, Calmar, robustness proxy를 통과함 |

## 6. 요약

| item | value | note |
|---|---:|---|
| total_candidate_rows_at_final_cost | 23 | 대표 비용률 cost_10bp 기준 후보 행 수 |
| final_candidate_count | 2 | 최종 후보 수 |
| reserve_candidate_count | 0 | 보류 후보 수 |
| cost_rate_grid | {'cost_0bp': 0.0, 'cost_5bp': 0.0005, 'cost_10bp': 0.001, 'cost_20bp': 0.002} | 거래비용률 민감도 후보 |
| turnover_filter_strict | avg <= 10.0%, max <= 40.0% | 엄격 Turnover 후보 기준 |
| turnover_filter_flex | avg <= 15.0%, max <= 50.0% | 유연 Turnover 후보 기준 |
| decision_count_exclude_turnover | 15 | 최종 판단 분포 |
| decision_count_benchmark | 5 | 최종 판단 분포 |
| decision_count_final_candidate | 2 | 최종 판단 분포 |
| decision_count_exclude_risk_metric | 1 | 최종 판단 분포 |

## 7. 해석상 주의

이 표는 자동으로 최종 정답을 확정하기 위한 것이 아니라, 후보를 압축하기 위한 기준표이다. 최종 보고서에서는 선택 후보뿐 아니라 제외·보류 사유를 함께 기록해야 한다.
