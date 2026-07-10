# 18. 기존 카나리아형 동적자산배분 proxy와 HSI 비교 실험 노트

## 18.1 실험의 출발점

HSI의 출발점은 처음부터 DAA, VAA, BAA 같은 기존 카나리아형 동적자산배분 전략을 개선하려는 목적이 아니었다. 초기 문제의식은 미국 시장 충격이 한국 시장으로 전이되는 현상을 관찰하고, 이런 외부 위험 신호를 한국 ETF 방어형 포트폴리오 판단에 활용할 수 있는지 확인해 보는 탐구적 실험이었다.

다만 프로젝트를 정리하는 과정에서 HSI는 기존 카나리아형 동적자산배분 계보와 비교해 볼 필요가 있다. 따라서 본 실험은 원 논문 전략을 완전 복제하려는 것이 아니라, 동일 국내 ETF 3종 유니버스 안에서 구현 가능한 VAA-like, DAA-like, BAA-like proxy 전략을 만들고, HSI_dynamic_v1과 같은 비용·같은 리밸런싱·같은 IS/OOS 조건에서 비교한다.

## 18.2 실험 가설

### H0
HSI_dynamic_v1의 5단계 상태분류와 λ 부분조정 구조는 단순 카나리아형 proxy 대비 OOS 기준 MDD, Calmar, Turnover, whipsaw 측면에서 개선을 보이지 않는다.

### H1
HSI_dynamic_v1은 기존 이진적 risk-on/risk-off proxy보다 OOS 기준 MDD, Calmar, Turnover 또는 whipsaw 측면에서 방어형 개선을 보인다. 단, 본 실험은 HSI가 DAA/VAA/BAA 원 논문 전략보다 우월하다는 결론이 아니라, 동일 국내 ETF 유니버스에서 HSI 구조가 어떤 차이를 보이는지 확인하는 후속 검증이다.

## 18.3 전략 정의

- FixedBM_70_20_10: 069500 70%, 114260 20%, 153130 10% 고정비중
- EW: 세 ETF 동일비중
- VAA_like_proxy: 세 ETF의 1/3/6/12개월 평균 momentum이 모두 양수이면 70/20/10, 하나라도 음수이면 0/30/70
- DAA_like_proxy: 069500, 114260을 canary proxy로 두고 bad canary 수에 따라 70/20/10, 35/30/35, 0/30/70 적용
- BAA_like_proxy: canary가 모두 양수이면 069500 100%, 아니면 114260과 153130 중 momentum이 높은 방어자산 100%
- HSI_dynamic_v1: 기존 프로젝트 산출 weight 파일을 읽어 동일 엔진으로 비용차감 재계산

기존 dynamic_v1 weight 파일을 자동으로 찾지 못해 이번 실행에는 HSI_dynamic_v1이 포함되지 않았다. HSI weight 파일 경로를 CFG.hsi_weight_file_candidates에 추가한 뒤 재실행해야 한다.

## 18.4 과적합 방지 장치

1. 동일 ETF 유니버스 사용: 069500, 114260, 153130만 사용한다.
2. 동일 비용 적용: 모든 전략에 10bp 비용을 적용한다.
3. 동일 리밸런싱 규칙 적용: t월 신호를 t+1월 수익률에 적용한다.
4. 모멘텀 산식 고정: 1/3/6/12개월 누적수익률의 단순 평균을 사용한다.
5. 임계값 고정: momentum > 0이면 양호, momentum <= 0이면 bad로 판정한다.
6. IS/OOS 분리: OOS 시작일은 `2021-01-31`로 고정한다.
7. score 최적화 미사용: CAGR, Calmar 등을 합산한 사후 score로 후보를 재선정하지 않는다.
8. whipsaw proxy 기록: 위험자산 비중 50% 기준 risk-on/risk-off mode flip 횟수를 기록한다.
9. audit table 저장: 수익률 단위, 비중 합계, 음수 비중, t→t+1 적용 근거를 파일로 남긴다.

## 18.5 OOS 성과 요약

| strategy         |   months |   cum_return |   cagr |   ann_vol |     mdd |   sharpe |   calmar |   monthly_win_rate |   avg_turnover_ann |
|:-----------------|---------:|-------------:|-------:|----------:|--------:|---------:|---------:|-------------------:|-------------------:|
| FixedBM_70_20_10 |       66 |       1.8137 | 0.2069 |    0.2311 | -0.2567 |   0.8954 |   0.8060 |             0.5606 |             0.0000 |
| EW               |       66 |       0.7779 | 0.1103 |    0.1123 | -0.1357 |   0.9819 |   0.8127 |             0.5909 |             0.0000 |
| VAA_like_proxy   |       66 |       0.4627 | 0.0716 |    0.1112 | -0.1129 |   0.6439 |   0.6339 |             0.6212 |             1.6545 |
| DAA_like_proxy   |       66 |       1.0821 | 0.1426 |    0.1458 | -0.1505 |   0.9785 |   0.9478 |             0.5606 |             1.3364 |
| BAA_like_proxy   |       66 |       0.6486 | 0.0952 |    0.1578 | -0.1623 |   0.6031 |   0.5863 |             0.6818 |             2.3636 |

## 18.6 Whipsaw proxy 요약

| strategy         |   risk_mode_flips |   avg_equity_weight |   min_equity_weight |   max_equity_weight |
|:-----------------|------------------:|--------------------:|--------------------:|--------------------:|
| FixedBM_70_20_10 |                 1 |              0.7000 |              0.7000 |              0.7000 |
| EW               |                 1 |              0.3333 |              0.3333 |              0.3333 |
| VAA_like_proxy   |                45 |              0.3152 |              0.0000 |              0.7000 |
| DAA_like_proxy   |                46 |              0.5076 |              0.0000 |              0.7000 |
| BAA_like_proxy   |                45 |              0.4503 |              0.0000 |              1.0000 |

## 18.7 검증 audit

| check                               | status   | evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|:------------------------------------|:---------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| return_unit_decimal                 | PASS     | max_abs_return=0.349432                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| FixedBM_70_20_10_weight_sum_1       | PASS     | max_abs_sum_error=0.000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| FixedBM_70_20_10_no_negative_weight | PASS     | min_weight=0.100000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| EW_weight_sum_1                     | PASS     | max_abs_sum_error=0.000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| EW_no_negative_weight               | PASS     | min_weight=0.333333333333                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| VAA_like_proxy_weight_sum_1         | PASS     | max_abs_sum_error=0.000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| VAA_like_proxy_no_negative_weight   | PASS     | min_weight=0.000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| DAA_like_proxy_weight_sum_1         | PASS     | max_abs_sum_error=0.000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| DAA_like_proxy_no_negative_weight   | PASS     | min_weight=0.000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| BAA_like_proxy_weight_sum_1         | PASS     | max_abs_sum_error=0.000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| BAA_like_proxy_no_negative_weight   | PASS     | min_weight=0.000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| signal_to_return_alignment          | PASS     | backtest uses weights.shift(1) * current_month_returns to enforce t signal -> t+1 return                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| parameter_lock                      | PASS     | {"experiment_id": "18_canary_lineage_benchmark", "experiment_name": "HSI vs canary-style DAA/VAA/BAA proxy benchmark", "version": "v1_pre_registered", "equity": "069500", "bond": "114260", "cash_like": "153130", "cost_bp": 10.0, "periods_per_year": 12, "momentum_windows": [1, 3, 6, 12], "oos_start": "2021-01-31", "hsi_weight_file_candidates": ["output/tables/main_final_final_ra_weights.csv", "output/tables/main_final_dynamic_v1_weights.csv", "data/processed/main_final_dynamic_v1_weights.csv", "data/processed/main_final_ra_weights.csv", "data/processed/main_final_all_strategy_weights.csv"], "return_file_candidates": ["data/processed/main_final_monthly_return_decimal.csv", "data/processed/monthly_return_decimal.csv", "output/tables/main_final_monthly_return_decimal.csv"], "out_table_dir": "output/tables", "out_figure_dir": "output/figures", "out_doc_dir": "docs"} |

## 18.8 생성된 그림

- `../output/figures/main_final_fig_canary_lineage_cumret.png`
- `../output/figures/main_final_fig_canary_lineage_drawdown.png`
- `../output/figures/main_final_fig_canary_lineage_oos_calmar.png`
- `../output/figures/main_final_fig_canary_lineage_turnover.png`
- `../output/figures/main_final_fig_canary_lineage_whipsaw.png`

## 18.9 해석 원칙

이 실험의 목적은 HSI가 DAA/VAA/BAA보다 우월하다고 단정하는 것이 아니다. 정직한 해석은 다음과 같다.

첫째, HSI는 개인적 시장 전이 관찰에서 출발한 탐구적 실험이었다. 둘째, 기존 카나리아형 동적자산배분 계보와 비교할 필요가 있음을 인식했다. 셋째, 본 실험에서는 동일 국내 ETF 유니버스 안에서 VAA-like, DAA-like, BAA-like proxy를 만들어 HSI와 비교했다. 넷째, 만약 HSI가 OOS 기준 MDD, Calmar, Turnover, whipsaw에서 우위를 보인다면, 이는 5단계 상태분류와 λ 부분조정 구조가 이진적 카나리아 proxy보다 방어형 운용에 유리했을 가능성을 보여주는 보조 근거이다. 다섯째, 반대로 proxy 전략이 더 우수하다면, HSI의 구조적 복잡성이 성과 개선으로 이어지지 않았다는 한계로 받아들여야 한다.

## 18.10 후속 과제

원 논문 DAA/VAA/BAA를 완전 복제하려면 글로벌 ETF offensive/defensive/canary universe가 필요하다. 이번 실험은 국내 ETF 3종 유니버스에서 가능한 proxy 비교이며, 원 논문 전략과의 엄밀한 비교는 후속 연구로 남긴다.
