# src/common 공통 모듈 리팩터링 요약 (2026-07-02)

작업 브랜치: `refactor/common-module`
범위: 개선방향 4.1(공통 모듈 통합)만. 동작(산출물)은 보존하는 것을 원칙으로 함.

## 1. 새로 만든 공통 패키지 `src/common/`

| 모듈 | 내용 |
|---|---|
| `paths.py` | `PROJECT_ROOT`, `TABLE_DIR`, `FIGURE_DIR`, `DOCS_DIR`, `DATA_DIR`, `PROCESSED_DIR` 등 경로 상수 |
| `config.py` | `ASSETS`, `BENCHMARK_TICKER`, `WEIGHT_COLS`, `INITIAL_CAPITAL` |
| `io_utils.py` | `read_csv_with_date(require_date, parse_signal_date)` — 기존 엄격형/관대형 로더 통합, `save_table` |
| `viz.py` | `set_korean_font()`, `STRATEGY_LABEL_MAP` |
| `metrics.py` | `calculate_performance_metrics`(정본), `make_performance_summary`, `add_diff_vs_ew` |
| `backtest.py` | `align_state_with_next_returns`, `calculate_turnover`, `make_turnover_summary`, `make_alignment_check` |

## 2. 리팩터링한 스크립트

- 백테스트: `17`(main_v2), `19`(main_v2b) — 경로/설정/로더/정렬·turnover·정렬점검 헬퍼를 common 사용. 각 스크립트 고유의 `build_backtest_for_method`/비중규칙은 로컬 유지.
- 평가: `18`, `21` — 로더/성과지표/EW차이 계산을 common 사용.
- 비교: `20` — 로더/성과지표를 common 사용.
- 시각화: `24`, `25`, `26`, `27`, `28` — `set_korean_font`/로더/경로를 common 사용.
  (`27`의 `STRATEGY_LABEL_MAP`은 EW 키가 없어 의도적으로 로컬 유지)

## 3. 버그 수정 (통합 과정에서)

`20`에 복제돼 있던 성과지표 함수는 `Sortino`와 `months==0` 가드가 누락된 채 원본과 어긋나 있었음. 정본(`common.metrics`)으로 교체하여, 규칙 비교표(`main_v2_rule_comparison_summary.csv`)의 main_v2b 행에서 비어 있던 `sortino`/`std_monthly_return` 값이 정상 계산되도록 수정됨.

## 4. 검증 결과

- 컴파일: 대상 스크립트 + common 전부 통과.
- 회귀(샌드박스 동일 pandas 기준): 재실행 산출물 **84/86 CSV byte-identical**. 나머지 2건(`main_v2_rule_comparison_summary`, `main_v2_fig6_rule_comparison_plot_data`)은 위 버그 수정으로 `sortino`/`std_monthly_return` 값만 변경(그 외 컬럼·수치 동일). 해석 노트(md) 5종 전부 동일.
- 단위테스트: `src/tests/test_common_pipeline.py` 8건 통과 (정렬 look-ahead, turnover 계산, 성과지표, 17/19 build 로직 포함).
  - 실행: `cd src && python3 -m pytest tests/test_common_pipeline.py -q`
- 참고: `17`/`19` end-to-end 실행은 `data/processed/monthly_returns.csv`가 로컬에 없어 불가하여, build 로직을 합성 데이터 단위테스트로 검증함.

## 5. 남은 조치 (사용자 환경에서)

샌드박스에서 `.git`이 읽기전용이라 커밋을 완료하지 못했습니다. 사용자 PC에서:

1. `refactor/common-module` 브랜치에 변경 파일이 있음(작업트리 저장 완료).
2. 만약 커밋이 막히면 `.git/index.lock` 파일을 수동 삭제 후 진행.
3. 검토 후 커밋/병합.

변경 파일: `src/common/*`, `src/tests/test_common_pipeline.py`, `src/{17,18,19,20,21,24,25,26,27,28}_*.py`

향후(별도 범위): `make_alignment_check`의 `alignment_flag`는 현재 리터럴 "OK" 동작을 유지했습니다(로드맵 4.4에서 실제 계산으로 개선 예정).
