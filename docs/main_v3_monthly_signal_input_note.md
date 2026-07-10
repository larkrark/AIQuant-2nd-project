# main_v3 월말 신호 입력표 생성 노트

- 생성 시각: 2026-06-29 23:16:29

## 1. 목적

31번에서 생성된 일별 HSI 원점수(`hsi_raw_scores.csv`)를 월말 기준 신호 입력표로 변환하였다. 이 파일은 main_v3 신호 조합 실험과 HSI 상태분류로 넘어가기 위한 중간 연결 고리이다.

## 2. 생성 파일

- `data/processed/main_v3_monthly_signal_inputs_wide.csv`
- `data/processed/main_v3_monthly_signal_inputs_long.csv`
- `data/processed/main_v3_monthly_signal_return_alignment_preview.csv`
- `output/tables/main_v3_signal_input_column_map.csv`
- `output/tables/main_v3_signal_input_availability_check.csv`
- `output/tables/main_v3_signal_input_quality_summary.csv`

## 3. 크기 요약

- 월말 신호 wide: `172 rows × 15 columns`
- 월말 신호 long: `516 rows × 18 columns`
- 월간 수익률: `171 rows × 3 columns`
- 신호-다음달 수익률 연결 preview: `513 rows × 12 columns`

## 4. 기본 신호와 확장 신호

기본 신호는 다음 5개이다.

- `return`
- `ma_pos`
- `momentum`
- `vol`
- `rs`

main_v3 확장 후보 신호는 다음 5개이다.

- `ma20_gap`
- `ma60_gap`
- `vol20`
- `drawdown_60`
- `risk_vs_cash_ret20`

현재 데이터 담당 파이프라인의 기본 산출물에는 기본 HSI 5신호가 중심으로 들어 있으며, 확장 후보 신호는 아직 없을 수 있다. 확장 후보 신호는 후속 파일 수령 또는 별도 계산으로 보강한다.

## 5. benchmark rs 처리

`069500`은 상대강도 계산의 기준자산이므로, 자기 자신과의 `rs`는 정보량이 없다. 따라서 `score_rs`가 NaN이어도 계산 오류로 보지 않고, `benchmark_rs_note`에 `benchmark_self_comparison`으로 표시하였다.

## 6. 시점 정합성

이번 단계에서는 월말 신호를 다음 달 수익률에 연결할 수 있는지 preview만 만들었다. 실제 백테스트에서는 `signal_month`의 HSI 상태를 `return_month`의 수익률에 적용한다.

## 7. 품질 점검 요약

| check_item | result | status | note |
|---|---|---|---|
| monthly_signal_wide_shape | 172 rows x 15 columns | OK | 일별 HSI 원점수의 월말 변환 결과 |
| monthly_signal_long_shape | 516 rows x 18 columns | OK | 월별·ETF별 long format 변환 결과 |
| monthly_returns_shape | 171 rows x 3 columns | OK | 다음 단계에서 월말 신호와 연결할 수익률표 |
| basic_signal_available_count | 15 | OK | 3개 ETF × 5개 기본 신호 중 benchmark rs는 NaN 허용 |
| extended_signal_available_count | 0 | INFO | 확장 후보 신호는 현재 파일에 없을 수 있음. 후속 파일 또는 추가 계산 필요. |
| score_method_source | zscore_from_data_pipeline | INFO | 우리 프로젝트 최종 실험에서는 rank 기본, zscore 보조 비교로 유지 |

## 8. 다음 단계

다음 단계에서는 이 월말 신호 입력표를 사용해 HSI 5상태 분류표를 재생성하고, `main_v2b` 기준 비중 규칙과 연결한다.
