# 19. 간이 Walk-forward Robustness Check: λ 후보 안정성 점검

## 19.1 목적

본 실험은 HSI 전략의 λ 후보가 특정 전체기간 성과에만 맞춰진 것인지 점검하기 위한 간이 walk-forward robustness check이다. 이 실험은 상용 RA 수준의 완전한 walk-forward 검증이 아니라, 교육용 프로젝트의 과적합 방어를 보강하기 위한 후속 검증이다.

## 19.2 실험 설정

- train window: 72개월
- test window: 12개월
- step: 12개월
- 거래비용: 10.0bp
- 후보 λ: (0.1, 0.3, 0.5, 0.7, 1.0)
- 선택 기준: train Calmar 우선, 평균 연환산 Turnover 0.20 이하 후보 우선
- 원칙: train window 안에서만 λ를 선별하고, test window에서는 고정 적용

## 19.3 Window별 선택 결과

| window_id | train_start | train_end | test_start | test_end | selected_lambda | selection_reason | train_selected_cagr | train_selected_mdd | train_selected_calmar | train_selected_turnover_ann | test_cum_return | test_cagr | test_ann_vol | test_mdd | test_sharpe | test_calmar | test_monthly_win_rate | test_turnover_ann |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2012-04-30 | 2018-03-31 | 2018-04-30 | 2019-03-31 | 0.1000 | all candidates exceeded turnover cap; selected max Calmar without turnover filter | 0.0351 | -0.0634 | 0.5537 | 0.2428 | -0.0214 | -0.0214 | 0.0588 | -0.0564 | -0.3642 | -0.3798 | 0.4167 | 0.3512 |
| 2 | 2013-04-30 | 2019-03-31 | 2019-04-30 | 2020-03-31 | 0.3000 | all candidates exceeded turnover cap; selected max Calmar without turnover filter | 0.0255 | -0.0588 | 0.4339 | 0.8401 | -0.0352 | -0.0352 | 0.0915 | -0.0695 | -0.3853 | -0.5072 | 0.5000 | 0.9190 |
| 3 | 2014-04-30 | 2020-03-31 | 2020-04-30 | 2021-03-31 | 0.3000 | all candidates exceeded turnover cap; selected max Calmar without turnover filter | 0.0223 | -0.0719 | 0.3099 | 0.8684 | 0.3398 | 0.3398 | 0.1085 | -0.0182 | 3.1327 | 18.7000 | 0.9167 | 0.6940 |
| 4 | 2015-04-30 | 2021-03-31 | 2021-04-30 | 2022-03-31 | 0.3000 | all candidates exceeded turnover cap; selected max Calmar without turnover filter | 0.0694 | -0.0719 | 0.9640 | 0.8380 | -0.0201 | -0.0201 | 0.0323 | -0.0454 | -0.6238 | -0.4436 | 0.5000 | 0.8584 |
| 5 | 2016-04-30 | 2022-03-31 | 2022-04-30 | 2023-03-31 | 0.3000 | all candidates exceeded turnover cap; selected max Calmar without turnover filter | 0.0681 | -0.0719 | 0.9460 | 0.8081 | -0.0373 | -0.0373 | 0.1264 | -0.1060 | -0.2949 | -0.3516 | 0.5000 | 1.1337 |
| 6 | 2017-04-30 | 2023-03-31 | 2023-04-30 | 2024-03-31 | 0.3000 | all candidates exceeded turnover cap; selected max Calmar without turnover filter | 0.0446 | -0.1533 | 0.2910 | 0.9146 | 0.0872 | 0.0872 | 0.0926 | -0.0620 | 0.9414 | 1.4053 | 0.5833 | 0.7850 |
| 7 | 2018-04-30 | 2024-03-31 | 2024-04-30 | 2025-03-31 | 0.1000 | all candidates exceeded turnover cap; selected max Calmar without turnover filter | 0.0437 | -0.1479 | 0.2956 | 0.3274 | -0.0214 | -0.0214 | 0.0540 | -0.0595 | -0.3955 | -0.3595 | 0.3333 | 0.3768 |
| 8 | 2019-04-30 | 2025-03-31 | 2025-04-30 | 2026-03-31 | 0.1000 | all candidates exceeded turnover cap; selected max Calmar without turnover filter | 0.0437 | -0.1479 | 0.2956 | 0.3317 | 0.5026 | 0.5026 | 0.2340 | -0.1091 | 2.1475 | 4.6058 | 0.7500 | 0.3057 |

## 19.4 Walk-forward stitched test 성과

| strategy | months | cum_return | cagr | ann_vol | mdd | sharpe | calmar | monthly_win_rate | avg_turnover_ann |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WF_selected_lambda | 96 | 0.9076 | 0.0841 | 0.1217 | -0.1533 | 0.6907 | 0.5483 | 0.5625 | 0.6780 |
| FixedBM_70_20_10 | 96 | 1.2461 | 0.1064 | 0.1774 | -0.2567 | 0.6001 | 0.4146 | 0.5521 | 0.0000 |
| EW | 96 | 0.6298 | 0.0630 | 0.0862 | -0.1357 | 0.7303 | 0.4639 | 0.5729 | 0.0000 |
| static_lambda_0.1 | 96 | 0.9008 | 0.0836 | 0.1182 | -0.1479 | 0.7071 | 0.5653 | 0.5625 | 0.3309 |
| static_lambda_0.3 | 96 | 1.0263 | 0.0923 | 0.1324 | -0.1533 | 0.6972 | 0.6019 | 0.5729 | 0.9046 |
| static_lambda_0.5 | 96 | 0.9603 | 0.0878 | 0.1384 | -0.1769 | 0.6342 | 0.4962 | 0.5833 | 1.4133 |
| static_lambda_0.7 | 96 | 0.8788 | 0.0820 | 0.1438 | -0.2019 | 0.5704 | 0.4062 | 0.5938 | 1.9188 |
| static_lambda_1.0 | 96 | 0.8305 | 0.0785 | 0.1537 | -0.2386 | 0.5108 | 0.3290 | 0.6354 | 2.7000 |

## 19.5 Audit

| check | status | evidence |
| --- | --- | --- |
| return_unit_decimal | PASS | max_abs_return=0.349432 |
| hsi_state_loaded | PASS | state_mode=applied, source=C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\tables\main_final_portfolio_composition_dynamic_v1.csv, non_null_states=171 |
| walk_forward_no_test_reselection | PASS | selected lambda is determined only from each train window and fixed in the next test window |
| window_count | PASS | n_windows=8, train_months=72, test_months=12, step_months=12 |
| parameter_lock | PASS | {"experiment_id": "19_walk_forward_lambda_robustness", "experiment_name": "Limited walk-forward robustness check for lambda candidates", "version": "v1_pre_registered", "equity": "069500", "bond": "114260", "cash_like": "153130", "cost_bp": 10.0, "periods_per_year": 12, "lambda_candidates": [0.1, 0.3, 0.5, 0.7, 1.0], "train_months": 72, "test_months": 12, "step_months": 12, "turnover_cap_ann": 0.2, "target_risk_relief": [0.7, 0.2, 0.1], "target_neutral_watch": [0.5, 0.35, 0.15], "target_conflict": [0.35, 0.4, 0.25], "target_risk_warning": [0.2, 0.45, 0.35], "target_accident_zone": [0.0, 0.3, 0.7], "return_file_candidates": ["data/processed/main_final_monthly_return_decimal.csv", "data/processed/monthly_return_decimal.csv", "output/tables/main_final_monthly_return_decimal.csv"], "hsi_state_file_candidates": ["output/tables/main_final_portfolio_composition_dynamic_v1.csv", "data/processed/main_final_portfolio_composition_dynamic_v1.csv", "main_final_portfolio_composition_dynamic_v1.csv", "data/processed/main_final_hsi_state5.csv", "output/tables/main_final_hsi_state5.csv", "data/processed/main_final_hsi_signal.csv"], "out_table_dir": "output/tables", "out_figure_dir": "output/figures", "out_doc_dir": "docs"} |

## 19.6 해석 원칙

이 실험은 λ를 최적화했다는 의미가 아니다. 각 시점에서 과거 train 구간만 보고 방어형 목적에 맞는 후보를 고른 뒤, 다음 test 구간에 고정 적용했을 때 결과가 급격히 무너지는지 확인한 것이다. 따라서 결과가 양호하더라도 상용 RA 수준의 검증이 완료되었다고 말하지 않고, 결과가 약하더라도 HSI 전체가 무효라고 단정하지 않는다.
