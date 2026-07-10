# main_v3 추가 지표 입력표 생성 노트

- 생성 시각: 2026-06-29 23:16:45

## 1. 목적

이 파일은 main_v3 추가 지표 후보를 생성하기 위한 연결 단계이다. 백테스트, 비중 규칙 변경, 최종 후보 선정은 아직 수행하지 않았다.

## 2. 추가 지표 후보

| signal_name | family | speed_group | expected_role | caution |
|---|---|---|---|---|
| ma20_gap | trend | fast | 단기 추세 개선 또는 악화 감지 | 단기 잡음에 민감할 수 있음 |
| ma60_gap | trend | slow | 중기 추세 구조 확인 | 반응이 늦을 수 있음 |
| vol20 | risk_damage | fast | 단기 변동성 확대 감지 | 급등락 이후 일시적으로 높게 유지될 수 있음 |
| drawdown_60 | risk_damage | slow | 누적 손상 정도 확인 | 회복 초기에 후행할 수 있음 |
| risk_vs_cash_ret20 | relative_strength | fast | 위험자산이 현금성 자산 대비 강한지 확인 | 현금성 ETF와 비교하므로 시장 국면에 따라 해석 필요 |

## 3. 방향 통일

모든 추가 지표는 HSI 방향 기준으로 변환하였다. 양수는 위험 악화 방향, 음수는 위험 완화 방향을 의미한다.

## 4. 점수화 방식

각 추가 지표는 rolling z-score를 사용해 표준화한 뒤 -10에서 +10 사이로 제한하였다. rolling mean과 rolling standard deviation은 shift(1)을 적용해 현재 값을 기준분포 계산에 포함하지 않았다.

## 5. 품질 점검

| check_item | result | status | note |
|---|---|---|---|
| base_monthly_long_shape | 516 rows x 18 columns | OK | 32번 월말 신호 입력표 |
| monthly_extended_wide_shape | 172 rows x 15 columns | OK | 추가 지표 월말 wide table |
| extended_long_shape | 516 rows x 20 columns | OK | 기존 월말 long table에 추가 지표 병합 |
| ma20_gap_availability | non_null=504, missing=12, missing_ratio=0.0233 | OK | rolling 계산 초기 구간에는 결측이 자연스럽게 발생 |
| ma60_gap_availability | non_null=501, missing=15, missing_ratio=0.0291 | OK | rolling 계산 초기 구간에는 결측이 자연스럽게 발생 |
| vol20_availability | non_null=504, missing=12, missing_ratio=0.0233 | OK | rolling 계산 초기 구간에는 결측이 자연스럽게 발생 |
| drawdown_60_availability | non_null=501, missing=15, missing_ratio=0.0291 | OK | rolling 계산 초기 구간에는 결측이 자연스럽게 발생 |
| risk_vs_cash_ret20_availability | non_null=336, missing=180, missing_ratio=0.3488 | OK | rolling 계산 초기 구간에는 결측이 자연스럽게 발생 |
| score_direction_rule | positive=risk_worsening, negative=risk_relief | OK | 기존 HSI 방향 기준과 동일하게 통일 |
| use_in_strategy | not_yet | INFO | 이번 파일은 추가 지표 입력표 생성 단계이며 백테스트는 다음 단계에서 수행 |

## 6. 다음 단계

다음 단계에서는 기본 HSI 신호와 추가 지표 조합을 비교하는 실험을 수행한다. main_v2b 비중 규칙은 고정하고, 신호 조합만 바꾸어 성과 차이를 확인한다.
