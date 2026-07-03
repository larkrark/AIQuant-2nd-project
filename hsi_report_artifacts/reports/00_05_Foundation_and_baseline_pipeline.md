# 00_05_Foundation_and_baseline_pipeline

## 목적

이 문서는 00~05번 초기 파이프라인 보고서의 인덱스이다. 00~05번은 최종 후보를 고르는 단계가 아니라, HSI 기반 ETF Overlay 전략이 실험 가능한 형태로 준비되는 과정을 설명한다.

## 파일 구성

| 번호 | 보고서 | 역할 |
|---:|---|---|
| 00 | `00_Project_config_and_data_check.md` | 프로젝트 기준, 데이터 번들, ETF 유니버스 확인 |
| 01 | `01_Bundle_structure_and_universe.md` | 데이터 번들 입출력 구조 정리 |
| 02 | `02_Event_balance_indicator_design.md` | HSI 내부 사건균형지표 설계 |
| 03 | `03_Monthly_signal_input_preparation.md` | 월말 HSI 신호 입력표 준비와 다음 달 수익률 정렬 |
| 04 | `04_HSI_state5_baseline.md` | HSI 5상태 baseline 생성 |
| 05 | `05_Baseline_allocation_backtest.md` | HSI 상태별 목표비중 baseline 백테스트 |

## 전체 흐름

```text
00 프로젝트 기준 고정
→ 01 데이터 번들 구조화
→ 02 내부 사건균형지표 설계
→ 03 월말 HSI 신호 입력표 준비
→ 04 HSI 5상태 시장상태 분류
→ 05 HSI 상태별 ETF 목표비중 baseline 백테스트
→ 10 Lambda 부분조정으로 baseline의 Turnover/MDD 한계 보완
```

## 핵심 요약

00~05번의 핵심은 HSI를 수익률 예측기가 아니라 시장상태 번역기로 정리한 것이다. HSI 상태는 ETF 목표비중으로 연결될 수 있었지만, 05번 baseline은 목표비중으로 즉시 이동하기 때문에 Turnover와 MDD 부담이 컸다. 따라서 이후 실험의 핵심 개선 방향은 HSI 상태분류 자체를 계속 바꾸는 것이 아니라, HSI 상태가 ETF 비중으로 반영되는 속도를 조절하는 Lambda 구조로 이어진다.

## 주요 산출표

- `00_05_bundle_sheet_summary.csv`
- `00_05_quality_summary.csv`
- `02_event_balance_design_table.csv`
- `03_signal_input_column_summary.csv`
- `04_hsi_state5_distribution_rebuilt.csv`
- `05_baseline_allocation_rule_rebuilt.csv`
- `05_baseline_performance_rebuilt.csv`
- `05_baseline_signal_return_alignment_preview.csv`

## 주요 그림

- `00_05_bundle_sheet_rows.png`
- `00_05_asset_role_risk_level.png`
- `04_hsi_state5_distribution.png`
- `05_baseline_allocation_rule.png`
- `05_baseline_weight_timeline.png`
- `05_baseline_cumulative_return.png`
- `05_baseline_drawdown.png`
