# main_v3 신호 조합별 백테스트 노트

- 생성 시각: 2026-06-29 23:17:27

## 1. 목적

35번에서 생성한 추가 지표 후보를 사용해 신호 조합별 HSI 상태분류와 main_v2b 기준 백테스트를 수행하였다. ETF 유니버스와 비중 규칙은 고정하고, 신호 조합만 바꾸었다.

## 2. 실험 설계

| experiment_id | experiment_name | signal_count | main_question |
|---|---|---:|---|
| combo_00_baseline_core | 기본 HSI 핵심 신호 | 4 | 기본 HSI 신호만으로 EW 대비 방어 효과가 있는가? |
| combo_01_trend_speed | 단기-중기 추세 보강 | 6 | 단기·중기 추세 보강이 상태분류와 성과를 개선하는가? |
| combo_02_risk_damage | 위험강도·누적손상 보강 | 6 | 변동성 확대와 누적 손상 신호가 방어 효과를 개선하는가? |
| combo_03_relative_strength | 현금성 자산 대비 상대강도 보강 | 5 | 위험자산이 현금성 자산 대비 약해지는 구간을 더 잘 포착하는가? |
| combo_04_speed_alignment_all | 단기-중기 신호 정렬 통합 | 9 | 추세·위험손상·상대강도 신호를 함께 쓰면 방어형 overlay 성과가 개선되는가? |

## 3. 성과 요약

| strategy_name | strategy_type | months | CAGR_pct | MDD_pct | Sharpe | Calmar | WinRate_pct |
|---|---|---:|---:|---:|---:|---:|---:|
| combo_00_baseline_core | HSI_combo | 167 | 5.64 | -13.80 | 0.8073 | 0.4086 | 61.68 |
| combo_01_trend_speed | HSI_combo | 167 | 5.78 | -14.03 | 0.8180 | 0.4116 | 60.48 |
| combo_02_risk_damage | HSI_combo | 167 | 5.67 | -14.03 | 0.8062 | 0.4043 | 60.48 |
| combo_03_relative_strength | HSI_combo | 167 | 5.65 | -14.57 | 0.8040 | 0.3875 | 60.48 |
| combo_04_speed_alignment_all | HSI_combo | 167 | 5.75 | -14.03 | 0.8102 | 0.4097 | 60.48 |

## 4. Turnover 요약

| experiment_id | avg_turnover_pct | max_turnover_pct | total_turnover_pct |
|---|---:|---:|---:|
| combo_00_baseline_core | 6.03 | 23.33 | 1006.67 |
| combo_01_trend_speed | 5.19 | 23.33 | 866.67 |
| combo_02_risk_damage | 5.23 | 23.33 | 873.33 |
| combo_03_relative_strength | 5.75 | 23.33 | 960.00 |
| combo_04_speed_alignment_all | 4.71 | 23.33 | 786.67 |

## 5. 후보 판단

| experiment_id | judgement | CAGR_gap_pct | MDD_improvement_pct | avg_turnover_pct | max_turnover_pct | selection_reason |
|---|---|---:|---:|---:|---:|---|
| combo_00_baseline_core | review | -1.07 | -0.23 | 6.03 | 23.33 | MDD not improved vs matched EW | avg turnover > 5% | max turnover <= 25% | state distribution is not overly concentrated |
| combo_04_speed_alignment_all | review | -0.96 | -0.46 | 4.71 | 23.33 | MDD not improved vs matched EW | avg turnover <= 5% | max turnover <= 25% | state distribution is not overly concentrated |
| combo_01_trend_speed | review | -0.93 | -0.46 | 5.19 | 23.33 | MDD not improved vs matched EW | avg turnover > 5% | max turnover <= 25% | state distribution is not overly concentrated |
| combo_02_risk_damage | review | -1.04 | -0.46 | 5.23 | 23.33 | MDD not improved vs matched EW | avg turnover > 5% | max turnover <= 25% | state distribution is not overly concentrated |
| combo_03_relative_strength | review | -1.06 | -1.00 | 5.75 | 23.33 | MDD not improved vs matched EW | avg turnover > 5% | max turnover <= 25% | state distribution is not overly concentrated |

## 6. 해석 원칙

이번 실험은 가장 높은 CAGR을 찾기 위한 절차가 아니라, 추가 신호 조합이 MDD, Turnover, 상태분포, 위험조정 성과 측면에서 기본 HSI보다 개선되는지 확인하기 위한 비교 실험이다.

## 7. 다음 단계

다음 단계에서는 성과표와 후보 판단표를 확인한 뒤, 후보 조합에 대해 θ 민감도 또는 사건균형지표 보조 진단을 붙일지 결정한다.
