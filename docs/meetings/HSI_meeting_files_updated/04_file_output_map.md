# 04. 파일 및 산출물 위치 정리

## A. 코드 파일

| 파일 | 위치 | 역할 | 상태 |
|---|---|---|---|
| `10_build_hsi_signal_inputs.py` | `src/` | ETF 선정, 가격 로드, HSI 계산, 결과 저장 | 실행 확인 |
| `05_hsi_state_classifier.py` | `src/` | HSI 상태 분류 | 연결 예정 |
| `portfolio_optimizer.py` | `src/` | 포트폴리오 최적화 또는 비교전략 | 연결 예정 |

## B. 입력 데이터

| 파일 | 위치 | 역할 | 상태 |
|---|---|---|---|
| `korea_etf.csv` | `data/raw/` | 원천 ETF 데이터 | 기존 보유 |
| `korea_etf_price_clean.csv` | `data/processed/` | 전처리된 ETF 가격 데이터 | 기존 보유 |
| `event_calendar_us_kr.csv` | `data/reference/` | 사건 달력 | 기존 보유 |

## C. 새로 저장된 가격 데이터

| 파일 | 위치 | 역할 | 상태 |
|---|---|---|---|
| `daily_prices.csv` | `data/processed/` | yfinance 기준 일별 가격 | 저장 완료 |
| `monthly_prices.csv` | `data/processed/` | 월말 라벨 기준 마지막 관측 가격 | 저장 완료 |
| `monthly_returns.csv` | `data/processed/` | 월말 가격 기준 월간 수익률 | 저장 완료 |

## D. 새로 저장된 HSI 결과

| 파일 | 위치 | 역할 | 상태 |
|---|---|---|---|
| `selected_etf_universe.csv` | `output/tables/` | 코드 기준 선정 ETF 목록 | 저장 완료 |
| `hsi_summary_rank.csv` | `output/tables/` | 분위수 방식 일별 HSI 전체 결과 | 저장 완료 |
| `hsi_latest_snapshot_rank.csv` | `output/tables/` | 분위수 방식 최근 HSI 스냅샷 | 저장 완료 |
| `hsi_summary_zscore.csv` | `output/tables/` | z-score 방식 일별 HSI 전체 결과 | 저장 완료 |
| `hsi_latest_snapshot_zscore.csv` | `output/tables/` | z-score 방식 최근 HSI 스냅샷 | 저장 완료 |

## E. 다음 단계에서 만들 파일

| 파일 | 위치 | 역할 | 우선순위 |
|---|---|---|---|
| `data_quality_summary.csv` | `output/tables/` | 데이터 품질 점검 요약 | 높음 |
| `missing_value_check.csv` | `output/tables/` | 결측치 점검표 | 높음 |
| `available_period_check.csv` | `output/tables/` | ETF별 사용 가능 기간 점검 | 높음 |
| `asset_group_count.csv` | `output/tables/` | 자산군별 ETF 수 요약 | 높음 |
| `hsi_signal_inputs_raw.csv` | `data/processed/` | HSI 입력 원신호 | 높음 |
| `signal_definition_table.csv` | `output/tables/` | 신호 정의, 계산식, window 기준 | 높음 |
| `signal_direction_table.csv` | `output/tables/` | 신호별 위험 악화 / 위험 완화 방향 정의 | 높음 |
| `hsi_monthly_state_rank.csv` | `output/tables/` | 분위수 방식 월말 HSI 상태 | 높음 |
| `hsi_monthly_state_zscore.csv` | `output/tables/` | z-score 방식 월말 HSI 상태 | 중간 |
| `hsi_state_table.csv` | `output/tables/` | HSI 상태 분류 결과 | 높음 |
| `hsi_state_definition.csv` | `output/tables/` | HSI 상태 정의표. `buy / watch / caution`과 프로젝트용 HSI 상태명 매핑 포함 | 높음 |
| `allocation_rule_table.csv` | `output/tables/` | HSI 상태별 위험자산·안전자산·방어자산 비중 조정 규칙 | 높음 |
| `rebalance_weights.csv` | `output/tables/` | 상태별 비중 결과 | 높음 |
| `backtest_timeseries.csv` | `output/tables/` | 백테스트 시계열 | 높음 |
| `strategy_drawdown.csv` | `output/tables/` | 전략별 Drawdown 시계열 | 높음 |
| `performance_summary.csv` | `output/tables/` | 성과 요약표 | 높음 |
| `grid_search_summary_preliminary.csv` | `output/tables/` | 예비 Grid Search 결과 | 중간 |
| `robustness_period_check.csv` | `output/tables/` | 기간별 안정성 검증 | 후순위 |
| `work_project_report_log.md` | `docs/` | 이전 HSI 예비 실험과 현재 정식 1차 테스트의 관계, 결정사항, 한계 기록 | 높음 |

## F. Practice / 예비 실험 참고자료

| 파일 | 위치 | 역할 | 상태 |
|---|---|---|---|
| `hsi_indicator_generation_practice.ipynb` | `practice/` | HSI 원신호, 상태명, 사건지표를 실험한 예비 노트북. 정식 실행 코드가 아니라 HSI 분류체계와 상태 해석 복구 참고자료 | 참고자료 |
| `report_HSI_dynamic_allocation_김근형.md` | `docs/` 또는 별도 보관 | 이전 HSI 예비 실험 보고서. HSI 구조와 방어형 동적자산배분 흐름 설명 참고 | 참고자료 |

## G. 파일 관리 시 주의사항

- 현재 저장된 결과는 전체 ETF 유니버스 기준이 아니라 예비 ETF 3종 기준이다.
- `monthly_prices.csv`는 월말 날짜 라벨을 사용하지만, 값은 해당 월의 마지막 관측 가격이다.
- `hsi_summary_rank.csv`와 `hsi_summary_zscore.csv`는 일별 HSI 신호이다.
- 월별 백테스트에 연결하려면 일별 HSI에서 월말 HSI 상태를 추출해야 한다.
- 월말 HSI 상태는 다음 달 ETF 월간 수익률에 적용해야 한다.
- `buy / watch / caution`은 계산 결과 확인용 1차 라벨로 관리하고, 보고서용 상태명은 `hsi_state_definition.csv`에서 별도로 정의한다.
- Grid Search 결과는 현재 예비 점검용으로 관리하고, 최종 전략 선정 기준으로 바로 해석하지 않는다.
