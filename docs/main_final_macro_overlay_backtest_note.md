# main_final macro companion soft overlay 백테스트 노트

- 생성 시각: 2026-07-02 12:05:25

## 1. 목적

이 단계는 05번 baseline HSI 비중 위에 macro companion 보조값을 소폭 반영하여, baseline과 macro overlay의 성과 및 비중 조정 정도를 비교한다.

## 2. 핵심 원칙

- HSI 상태분류는 바꾸지 않는다.
- macro companion은 HSI baseline 비중 위의 작은 방어 보정값으로만 사용한다.
- `macro_data_available = 0`인 월은 baseline 비중을 그대로 사용한다.
- 위험자산 `069500`에서 줄인 비중은 `114260` 30%, `153130` 70%로 이동한다.
- macro overlay delta는 최대 3.0%p로 제한한다.

## 3. 적용 강도 규칙

| 구분 | 적용 강도 | 해석 |
|---|---:|---|
| both_hsi_and_macro_risk | 1.00 | HSI와 macro가 동시에 위험을 말할 때만 온전히 반영 |
| macro_risk_only + conflict/neutral_watch | 0.50 | HSI가 확실한 위험은 아니므로 절반만 반영 |
| macro_risk_only + risk_relief | 0.25 | HSI가 완화 쪽이면 과잉방어 방지를 위해 작게 반영 |
| hsi_risk_only 또는 both_relief_or_neutral | 0.00 | baseline 유지 |

## 4. 성과 요약

| strategy | months | CAGR_pct | MDD_pct | Sharpe | Calmar | WinRate_pct |
|---|---:|---:|---:|---:|---:|---:|
| HSI_final_baseline_overlay | 172 | 7.7323 | -23.4594 | 0.6111 | 0.3296 | 65.1163 |
| HSI_macro_companion_soft_overlay | 172 | 7.7318 | -23.3629 | 0.6118 | 0.3309 | 65.1163 |

## 5. 비중 조정 요약

| summary_type | segment | months | adjusted_months | avg_delta_pctp | max_delta_pctp |
|---|---|---:|---:|---:|---:|
| overall | all | 172 | 56 | 0.1875 | 2.5000 |
| by_macro_hsi_overlap_type | both_hsi_and_macro_risk | 26 | 8 | 0.4423 | 2.5000 |
| by_macro_hsi_overlap_type | both_relief_or_neutral | 55 | 0 | 0.0000 | 0.0000 |
| by_macro_hsi_overlap_type | hsi_risk_only | 21 | 0 | 0.0000 | 0.0000 |
| by_macro_hsi_overlap_type | macro_data_unavailable | 22 | 0 | 0.0000 | 0.0000 |
| by_macro_hsi_overlap_type | macro_risk_only | 48 | 48 | 0.4323 | 1.2500 |
| by_hsi_state | accident_zone | 34 | 0 | 0.0000 | 0.0000 |
| by_hsi_state | conflict | 4 | 3 | 0.5625 | 1.2500 |
| by_hsi_state | insufficient_data | 4 | 0 | 0.0000 | 0.0000 |
| by_hsi_state | neutral_watch | 35 | 15 | 0.2643 | 1.2500 |
| by_hsi_state | risk_relief | 81 | 30 | 0.1142 | 0.6250 |
| by_hsi_state | risk_warning | 14 | 8 | 0.8214 | 2.5000 |

## 6. 보고서용 해석 문장

본 프로젝트에서는 macro companion layer를 HSI 상태분류의 대체 신호로 사용하지 않고, HSI baseline 비중 위에 소폭의 방어 보정값을 더하는 soft overlay 방식으로만 사용하였다. 매크로 위험 신호가 HSI 위험상태와 동시에 나타날 때는 보정값을 온전히 반영하고, 매크로 위험 신호만 단독으로 나타나는 경우에는 과잉방어를 피하기 위해 보정 강도를 낮추었다.
