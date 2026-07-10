# Colab 보조 Walk-forward Robustness 실험 노트

본 Colab 실험은 로컬 VSCode에서 생성한 공식 19번 walk-forward 결과를 대체하지 않고, train/test window 길이를 바꾼 보조 robustness 점검입니다.

## 핵심 결과: WF_selected_lambda

| variant              | strategy           |   months |   cum_return |   cagr |   ann_vol |     mdd |   sharpe |   calmar |   monthly_win_rate |   avg_turnover_ann |
|:---------------------|:-------------------|---------:|-------------:|-------:|----------:|--------:|---------:|---------:|-------------------:|-------------------:|
| train60_test12       | WF_selected_lambda |      108 |       1.0658 | 0.0839 |    0.1164 | -0.1533 |   0.7214 |   0.5474 |             0.5926 |             0.7184 |
| train72_test12_colab | WF_selected_lambda |       96 |       0.9076 | 0.0841 |    0.1217 | -0.1533 |   0.6907 |   0.5483 |             0.5625 |             0.6780 |
| train72_test24       | WF_selected_lambda |       96 |       0.8953 | 0.0832 |    0.1215 | -0.1533 |   0.6849 |   0.5426 |             0.5625 |             0.6036 |

## 선택 λ 빈도

| variant              |   selected_lambda |   count |
|:---------------------|------------------:|--------:|
| train60_test12       |               0.1 |       3 |
| train60_test12       |               0.3 |       6 |
| train72_test12_colab |               0.1 |       3 |
| train72_test12_colab |               0.3 |       5 |
| train72_test24       |               0.1 |       2 |
| train72_test24       |               0.3 |       2 |

## Audit

| check               | status   | evidence                                                                                                                                                                                                                                                                                                                                                                                   |
|:--------------------|:---------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| return_unit_decimal | PASS     | max_abs_return=0.349432                                                                                                                                                                                                                                                                                                                                                                    |
| hsi_state_loaded    | PASS     | state_mode=applied, source=main_final_portfolio_composition_dynamic_v1.csv, non_null_states=171                                                                                                                                                                                                                                                                                            |
| weight_sum_1        | PASS     | max_abs_sum_error=0.000000000000                                                                                                                                                                                                                                                                                                                                                           |
| parameter_lock      | PASS     | {"equity": "069500", "bond": "114260", "cash_like": "153130", "cost_bp": 10.0, "periods_per_year": 12, "lambda_candidates": [0.1, 0.3, 0.5, 0.7, 1.0], "turnover_cap_ann": 0.2, "target_risk_relief": [0.7, 0.2, 0.1], "target_neutral_watch": [0.5, 0.35, 0.15], "target_conflict": [0.35, 0.4, 0.25], "target_risk_warning": [0.2, 0.45, 0.35], "target_accident_zone": [0.0, 0.3, 0.7]} |

해석 원칙: 이 결과는 λ 최적화가 아니라 시간 안정성 보조 점검입니다. 공식 주 결과는 로컬 VSCode 19번 결과를 기준으로 삼고, Colab 결과는 window 설정 변화에 대한 보조 민감도 확인으로 사용합니다.
