# main_v2 HSI 5상태 Overlay 실험 로그

- 생성 시각: 2026-06-29 05:29:55
- 목적: HSI 5상태 체계를 이용한 방어형 overlay 전략 실험 산출물 정리

## 1. 실험 흐름

| 단계 | 파일 | 역할 |
|---|---|---|
| 16 | `main_v2_hsi_state5_table_rank.csv` | rank 기준 HSI 5상태 월별 분류표 (생성 완료) |
| 16 | `main_v2_hsi_state5_table_zscore.csv` | zscore 기준 HSI 5상태 월별 분류표 (생성 완료) |
| 16 | `main_v2_hsi_state5_definition.csv` | HSI 5상태 정의표 (생성 완료) |
| 16 | `main_v2_allocation_rule_table.csv` | main_v2 상태별 overlay 비중 규칙 (생성 완료) |
| 16 | `main_v2_hsi_state5_distribution.csv` | HSI 5상태 분포 요약 (생성 완료) |
| 17 | `main_v2_backtest_timeseries_rank.csv` | main_v2 rank 기준 백테스트 시계열 (생성 완료) |
| 17 | `main_v2_backtest_timeseries_zscore.csv` | main_v2 zscore 기준 백테스트 시계열 (생성 완료) |
| 17 | `main_v2_strategy_weights_rank.csv` | main_v2 rank 기준 월별 전략 비중 (생성 완료) |
| 17 | `main_v2_strategy_weights_zscore.csv` | main_v2 zscore 기준 월별 전략 비중 (생성 완료) |
| 18 | `main_v2_performance_summary.csv` | main_v2 정식 성과평가표 (생성 완료) |
| 19 | `main_v2b_backtest_timeseries_rank.csv` | main_v2b rank 기준 백테스트 시계열 (생성 완료) |
| 19 | `main_v2b_backtest_timeseries_zscore.csv` | main_v2b zscore 기준 백테스트 시계열 (생성 완료) |
| 19 | `main_v2b_strategy_weights_rank.csv` | main_v2b rank 기준 월별 전략 비중 (생성 완료) |
| 19 | `main_v2b_strategy_weights_zscore.csv` | main_v2b zscore 기준 월별 전략 비중 (생성 완료) |
| 19 | `main_v2b_allocation_rule_table.csv` | main_v2b 상태별 overlay 비중 규칙 (생성 완료) |
| 20 | `main_v2_rule_comparison_summary.csv` | main_v2와 main_v2b 규칙 비교표 (생성 완료) |
| 20 | `main_v2_rule_comparison_comment.csv` | main_v2와 main_v2b 비교 해석 코멘트 (생성 완료) |
| 21 | `main_v2b_performance_summary.csv` | main_v2b 정식 성과평가표 (생성 완료) |
| 21 | `main_v2b_drawdown_timeseries.csv` | main_v2b Drawdown 시계열 (생성 완료) |
| 21 | `main_v2b_cumulative_return_timeseries.csv` | main_v2b 누적수익률 시계열 (생성 완료) |
| 21 | `main_v2b_performance_comment.csv` | main_v2b 성과 해석 코멘트 (생성 완료) |

## 2. 실험 구분

| 실험 | 설명 |
|---|---|
| main_v2 | conflict 상태를 소폭 방어로 처리한 HSI 5상태 overlay |
| main_v2b | conflict 상태를 관찰 상태로 처리한 완화형 HSI 5상태 overlay |

## 3. 현재 산출물 상태

- 생성 완료 파일 수: 21
- 미생성 파일 수: 0

## 4. 작업 메모

- HSI 5상태는 `risk_relief`, `neutral_watch`, `conflict`, `risk_warning`, `accident_zone`으로 구성하였다.
- main_v2에서는 `conflict`를 소폭 방어 상태로 처리하였다.
- main_v2b에서는 `conflict`를 위험 악화 확정 상태가 아니라 관찰 상태로 처리하였다.
- 월말 HSI 상태는 다음 달 월간 수익률에 적용하여 look-ahead bias를 피하는 구조로 정렬하였다.
