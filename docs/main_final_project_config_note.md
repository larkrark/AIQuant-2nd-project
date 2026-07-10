# main_final 프로젝트 설정 노트

- 생성 시각: 2026-06-30 18:43:35

## 1. 최종 기준 파일

- 데이터 담당 최종 모듈: `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\src\HSI_data_pipeline_0629_5.py`
- 후속 실험 기준 데이터 번들: `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\tables\hsi_data_bundle.xlsx`

이제 후속 실험은 데이터를 다시 수집하기보다, 데이터 담당자 산출물인 `hsi_data_bundle.xlsx`를 기준 입력으로 사용한다.

## 2. 최종 ETF 유니버스

| ticker | name | role |
|---|---|---|
| 069500 | KODEX 200 | 위험자산 |
| 114260 | KODEX 국고채3년 | 방어 채권 |
| 153130 | KODEX 단기채권PLUS | 현금성 방어자산 |

## 3. 수익률 단위 규칙

- `monthly_return_decimal`: 백테스트 계산용 decimal 단위
- `monthly_return_pct`: 사람이 확인하기 위한 percent 단위

예시:

```text
2.5% → monthly_return_pct = 2.5
2.5% → monthly_return_decimal = 0.025
```

## 4. hsi_data_bundle.xlsx 필수 시트 점검

| sheet | status | note |
|---|---|---|
| meta | OK | hsi_data_bundle.xlsx 필수 시트 |
| input_structure | OK | hsi_data_bundle.xlsx 필수 시트 |
| output_structure | OK | hsi_data_bundle.xlsx 필수 시트 |
| etf_info | OK | hsi_data_bundle.xlsx 필수 시트 |
| asset_class | OK | hsi_data_bundle.xlsx 필수 시트 |
| monthly_price | OK | hsi_data_bundle.xlsx 필수 시트 |
| monthly_return_pct | OK | hsi_data_bundle.xlsx 필수 시트 |
| monthly_return_decimal | OK | hsi_data_bundle.xlsx 필수 시트 |
| signal_inputs | OK | hsi_data_bundle.xlsx 필수 시트 |
| hsi_scaled_scores | OK | hsi_data_bundle.xlsx 필수 시트 |
| hsi_direction | OK | hsi_data_bundle.xlsx 필수 시트 |
| hsi_signal | OK | hsi_data_bundle.xlsx 필수 시트 |
| signal_direction_map | OK | hsi_data_bundle.xlsx 필수 시트 |
| snapshot | OK | hsi_data_bundle.xlsx 필수 시트 |
| data_period | OK | hsi_data_bundle.xlsx 필수 시트 |
| missing_summary | OK | hsi_data_bundle.xlsx 필수 시트 |
| liquidity_check | OK | hsi_data_bundle.xlsx 필수 시트 |
| exclusions | OK | hsi_data_bundle.xlsx 필수 시트 |

## 5. 최종 baseline 리밸런싱 규칙

리밸런싱 규칙은 HSI 상태분류 결과를 실제 ETF 목표 비중으로 변환하는 연결 규칙이다. HSI는 미래 수익률을 직접 예측하는 모델이 아니므로, 본 규칙은 시장상태에 따라 위험자산 노출을 확대하거나 축소하는 방어형 자산배분 규칙으로 설계한다.

| HSI 상태 | 해석 | 069500 | 114260 | 153130 |
|---|---|---:|---:|---:|
| risk_relief | 위험 완화 우세 | 70% | 20% | 10% |
| neutral_watch | 중립 관찰 | 50% | 35% | 15% |
| conflict | 신호 충돌 | 35% | 40% | 25% |
| risk_warning | 위험 악화 우세 | 20% | 45% | 35% |
| accident_zone | 강한 위험 구간 | 0% | 30% | 70% |

설계 원칙:

- 단조성: 위험 상태가 강해질수록 위험자산 비중은 감소한다.
- 방어성: 위험 악화 상태에서는 채권·현금성 자산 비중을 높인다.
- 비예측성: HSI 상태를 미래수익률 예측값으로 보지 않는다.
- 시점 정합성: 월말 HSI 상태를 다음 달 수익률에 적용한다.
- 과잉매매 제한: Turnover가 과도하게 커지지 않도록 λ 또는 turnover cap을 검토한다.
- 해석 가능성: 상태별 비중 변화가 사람이 이해 가능한 구조여야 한다.

## 6. 후속 실험의 역할 구분

- 사건균형지표: HSI 사건균형지표는 외부 사건 달력이 아니라, HSI 입력 신호의 과거 분포를 기준으로 위험 사건과 완화 사건의 반복 정도를 계산한 내부 보조지표이다. 위험 사건은 과거 80분위수 이상, 완화 사건은 과거 20분위수 이하로 정의한다.
- 상대속도 실험: 상대속도 실험은 선행/후행 예측 실험이 아니라, 빠른 신호와 느린 신호가 위험 악화 또는 위험 완화 방향으로 움직이는 속도 차이를 진단하는 실험이다.
- θ 실험: θ 실험은 최고 CAGR을 찾는 최적화가 아니라, HSI 상태분류 민감도 변화에도 상태분포, MDD, Turnover, Sharpe, Calmar가 안정적으로 유지되는지 확인하는 민감도 검증이다.
- λ 실험: λ 실험은 목표 비중으로 한 번에 이동할지 일부만 이동할지 결정하는 포트폴리오 관성 실험이다. Turnover와 방어 성과 사이의 균형을 확인한다.
- 외부 사건 달력: 시장 사건 달력은 HSI 계산이나 비중 결정에 직접 사용하지 않는다. HSI 상태와 백테스트 결과를 먼저 산출한 뒤, 주요 시장 사건 구간과 사후적으로 대조하는 해석·검증·시각화 보조 자료로 사용한다.

## 7. 최종 실행 흐름

```text
00_final_project_config_check.py  # 최종 기준 파일·번들·시트·단위·역할 확인
01_load_bundle_and_make_structure_tables.py  # hsi_data_bundle.xlsx 로드 및 입력·출력 구조표 생성
02_build_hsi_event_balance_indicator.py  # 20/80 분위수 기반 사건균형·위험누적지표 생성
03_prepare_monthly_signal_inputs.py  # 일별 HSI 신호를 월말 기준으로 정리
04_build_hsi_state5_baseline.py  # HSI 5상태 기준선 생성
05_backtest_baseline_allocation_rule.py  # 최종 상태별 목표 비중표 기준 baseline 백테스트
06_build_relative_speed_diagnostics.py  # 빠른 신호·느린 신호·상대속도 진단
07_run_signal_combo_backtests.py  # 기본 신호·확장 신호·상대속도 보조 조합 비교
08_event_balance_state_diagnostic.py  # HSI 5상태와 사건균형지표 정합성 확인
09_event_balance_filter_backtest.py  # 사건균형지표를 보조 필터로 넣은 전략 실험
10_inertia_lambda_experiment.py  # λ 기반 부분 조정·Turnover·거래비용 실험
11_theta_sensitivity_experiment.py  # θ 민감도 검증

50_build_market_event_calendar_table.py  # 외부 사건 달력을 표준 CSV로 변환
51_align_hsi_state_with_market_events.py  # HSI 상태와 시장 사건 구간을 사후 대조
52_plot_event_annotated_hsi_timeline.py  # 사건 주석 HSI 타임라인 생성
```

## 8. 현재 발견된 번들 시트

```text
meta
input_structure
output_structure
etf_info
asset_class
monthly_price
monthly_return_pct
monthly_return_decimal
signal_inputs
hsi_scaled_scores
hsi_direction
hsi_signal
signal_direction_map
snapshot
data_period
missing_summary
liquidity_check
exclusions
```
