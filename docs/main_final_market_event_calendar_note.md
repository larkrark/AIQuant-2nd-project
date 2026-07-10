# main_final 외부 시장 사건 달력 표준화 노트

- 생성 시각: 2026-06-30 18:44:24

## 1. 목적

이 단계는 외부 시장 사건 달력을 표준 CSV로 변환한다. 시장 사건 달력은 HSI 계산이나 ETF 비중 결정에 직접 사용하지 않고, HSI 상태 산출 이후 주요 시장 사건 구간과 사후적으로 대조하는 해석·검증 자료로 사용한다.

## 2. 원칙

- strategy_input = False
- calendar_role = post_hoc_interpretation_only
- 50번대 파일은 사후 해석·시각화·위기구간 검증 레이어이다.

## 3. 품질 점검

| item | value | status | note |
|---|---|---|---|
| source_file | C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\src\market_event_calendar.py | OK | 외부 사건 달력 원천 파일 |
| source_variable | market_event_calendar | OK | 불러온 사건 달력 변수명 |
| event_rows | 27 | OK | 표준화된 사건 수 |
| missing_start_date | 0 | OK | start_date 누락 여부 |
| strategy_input_false_count | 27 | OK | 시장 사건 달력은 전략 입력이 아니어야 함 |
| data_available_events | 27 | OK | 2012-03-07 이후 사건 수 |

## 4. 사건 수

- 총 사건 수: 27

| event_type | count |
|---|---:|
| market_event | 27 |

## 5. 다음 단계

`51_align_hsi_state_with_market_events.py`에서 HSI 상태표와 월 단위로 대조하고, `52_plot_event_annotated_hsi_timeline.py`에서 사건 주석이 들어간 HSI 타임라인을 만들 수 있다.
