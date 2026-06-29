# 03. 앞으로 해야 할 일 체크리스트

- [ ] 아직 안 한 일
- [x] 완료한 일

## A. 현재 완료된 1차 실행 확인

- [x] 예비 ETF 3종 기준으로 가격 데이터를 로드하였다.
- [x] `selected_etf_universe.csv`를 저장하였다.
- [x] `daily_prices.csv`를 저장하였다.
- [x] `monthly_prices.csv`를 저장하였다.
- [x] `monthly_returns.csv`를 저장하였다.
- [x] 분위수 방식 HSI 결과인 `hsi_summary_rank.csv`를 저장하였다.
- [x] z-score 방식 HSI 결과인 `hsi_summary_zscore.csv`를 저장하였다.
- [x] 현재 결과는 전체 전략 성과가 아니라, HSI 입력 데이터 생성 및 신호 산출 예비 실행 결과임을 확인하였다.
- [x] `practice/hsi_indicator_generation_practice.ipynb`가 HSI 원신호와 상태명 설계를 복구하는 참고자료임을 확인하였다.

## B. 데이터 품질 점검

- [ ] ETF 티커 중복 여부를 확인한다.
- [ ] 날짜 컬럼이 정상적으로 정렬되었는지 확인한다.
- [ ] 가격 데이터가 숫자형인지 확인한다.
- [ ] 결측치가 많은 ETF가 있는지 확인한다.
- [ ] ETF별 사용 가능 기간을 표로 정리한다.
- [ ] 자산군별 ETF 수를 표로 정리한다.
- [ ] 위험자산, 안전자산, 방어자산, 현금성 자산이 모두 포함되는지 확인한다.
- [ ] 월말 가격으로 변환했을 때 비어 있는 월이 있는지 확인한다.
- [ ] 월말 가격은 월말 날짜 라벨로 표시되지만, 값은 해당 월의 마지막 관측 가격을 사용한다는 점을 기록한다.

## C. HSI 입력 신호 정리

- [ ] HSI 입력 원신호 목록을 확정한다.
- [ ] `practice/hsi_indicator_generation_practice.ipynb`에서 사용한 기존 HSI 원신호 목록을 확인한다.
- [ ] 이전 HSI 예비 실험의 신호 방향 통일 방식을 현재 프로젝트 기준으로 재검토한다.
- [ ] 각 신호의 계산식을 정리한다.
- [ ] 각 신호의 방향을 정리한다.
- [ ] 각 신호의 window 기준을 정리한다.
- [ ] 각 신호의 결측 처리 기준을 정리한다.
- [ ] 상대강도 기준 ETF를 확정한다.
- [ ] `hsi_signal_inputs_raw.csv` 또는 이에 해당하는 원신호 표를 만든다.
- [ ] 신호별 정의, 계산식, 방향, window를 정리한 `signal_definition_table.csv`를 만든다.
- [ ] 신호별 위험 악화 / 위험 완화 방향을 정리한 `signal_direction_table.csv`를 만든다.

## D. 점수화 방식 비교

- [x] 분위수 방식을 기본 실험 기준으로 둔다.
- [x] z-score 방식을 비교용 보조 실험으로 남긴다.
- [ ] 원자료 vs z-score vs 분위수 3단 시계열 그래프를 만든다.
- [ ] z-score vs 분위수 산점도를 만든다.
- [ ] 입력신호별 Raw / Z-score / Percentile 비교표를 만든다.
- [ ] 입력신호별 heatmap 또는 비교표를 만든다.
- [ ] 필요 시 히스토그램 또는 분포 비교 그래프를 만든다.
- [ ] 발표에서는 z-score를 “얼마나 강하게 튀었는가”, 분위수를 “상대적으로 얼마나 높은 위치인가”로 설명한다.

## E. 일별 HSI와 월별 백테스트 연결

- [ ] 현재 HSI 결과가 일별 신호임을 확인한다.
- [ ] 현재 백테스트용 수익률은 월별 수익률임을 확인한다.
- [ ] 일별 HSI 신호에서 월말 HSI 상태를 추출한다.
- [ ] 월말 HSI 상태를 다음 달 ETF 수익률에 적용하는 구조를 만든다.
- [ ] 월말 신호와 다음 달 수익률 적용 방식이 look-ahead bias를 피하는 구조인지 확인한다.
- [ ] `hsi_monthly_state_rank.csv`를 만든다.
- [ ] 필요 시 `hsi_monthly_state_zscore.csv`도 만든다.

## F. HSI 상태 분류

- [ ] HSI direction, intensity 결과를 상태 분류로 연결한다.
- [ ] 현재 코드의 `buy / watch / caution` 라벨은 1차 계산 라벨로 유지할지 확인한다.
- [ ] `buy / watch / caution`을 프로젝트용 HSI 상태명으로 매핑한다.
- [ ] 위험 완화, 관찰/중립, 충돌, 위험 악화, 강한 위험 악화 상태명을 정의한다.
- [ ] 같은 direction 값이라도 intensity와 conflict에 따라 해석이 달라질 수 있음을 반영한다.
- [ ] 초기 rolling window 부족 구간을 실제 중립으로 볼지, `insufficient_data`로 구분할지 정한다.
- [ ] 상태별 해석 문장을 작성한다.
- [ ] HSI 상태 분포표를 만든다.
- [ ] HSI 상태별 월별 빈도표를 만든다.
- [ ] `hsi_state_table.csv`를 만든다.
- [ ] `hsi_state_definition.csv`를 만든다.

## G. HSI overlay 및 비중 조정

- [ ] 상태별 위험자산, 안전자산, 방어자산 비중 조정 규칙을 정한다.
- [ ] 기본 전략 비중 위에 HSI overlay를 얹는 구조를 확정한다.
- [ ] HSI가 직접 매수·매도 신호가 아니라 비중 조정 보조지표임을 문서에 명시한다.
- [ ] 상태별 비중 조정 규칙을 토론용 초안으로 먼저 만든다.
- [ ] `rebalance_weights.csv` 형태의 비중 결과표를 만든다.
- [ ] 월말 HSI 신호를 다음 달 비중에 적용하는 시점 분리를 확인한다.

## H. 1차 백테스트

- [ ] `monthly_returns.csv`와 `rebalance_weights.csv`를 연결한다.
- [ ] 먼저 Equal Weight 전략을 기준 전략으로 계산한다.
- [ ] Equal Weight + HSI overlay 전략을 계산한다.
- [ ] 전략 월간 수익률을 계산한다.
- [ ] 누적수익률, CAGR, 변동성, MDD, Sharpe를 계산한다.
- [ ] 위험자산 100% 또는 현금성 자산 등 단순 비교군을 함께 둔다.
- [ ] `backtest_timeseries.csv`를 저장한다.
- [ ] `performance_summary.csv`를 저장한다.
- [ ] `strategy_drawdown.csv`를 저장한다.

## I. 성과표 및 기본 시각화

- [ ] 전략별 누적수익률 그래프를 만든다.
- [ ] 전략별 Drawdown 그래프를 만든다.
- [ ] HSI 상태 시계열 그래프를 만든다.
- [ ] HSI 상태 분포 그래프를 만든다.
- [ ] 성과 요약표를 발표용으로 정리한다.
- [ ] 분위수와 z-score 차이를 설명하는 비교 그림을 만든다.
- [ ] EW와 EW+HSI의 차이를 먼저 시각화한다.

## J. 비교전략 확장

- [ ] EW / EW+HSI 결과를 먼저 확인한다.
- [ ] 그다음 Risk Parity 전략으로 확장한다.
- [ ] Risk Parity + HSI overlay 전략을 만든다.
- [ ] 그다음 GMV 전략으로 확장한다.
- [ ] GMV + HSI overlay 전략을 만든다.
- [ ] 그다음 MDP 전략으로 확장한다.
- [ ] MDP + HSI overlay 전략을 만든다.
- [ ] 처음부터 모든 전략을 한꺼번에 연결하지 않고, 단계별로 원인을 확인한다.

## K. Grid Search / Robustness

- [ ] 현재 Grid Search는 예비 점검용임을 명확히 한다.
- [ ] 최종 Grid Search는 CAGR, MDD, Sharpe, Turnover 등 백테스트 성과지표와 연결한다.
- [ ] Grid Search 후보 범위를 너무 넓히지 않는다.
- [ ] 분위수와 z-score 비교는 본 실험의 보조 비교로 관리한다.
- [ ] Robustness 검증 기준을 표로 정리한다.
- [ ] 기간분할 검증을 준비한다.
- [ ] 위기구간 검증을 준비한다.
- [ ] 거래비용 반영 검증을 준비한다.
- [ ] 파라미터 주변값 검증을 준비한다.
- [ ] Grid Search와 Robustness는 기본형 전략 실행 이후 확장 검증 단계로 둔다.

## L. 발표 및 문서화

- [ ] 현재 결과를 “전략 성과 검증 결과”가 아니라 “HSI 입력 데이터 생성 및 분위수/z-score 신호 산출 예비 실행 결과”로 표현한다.
- [ ] 현재 결과가 3개 ETF 예비 유니버스 기준임을 명시한다.
- [ ] ETF 후보군이 최종 확정되기 전까지는 예비 실행 결과로 표현한다.
- [ ] HSI는 미래수익률 예측모델이 아니라 시장상태 판단용 보조지표임을 설명한다.
- [ ] `buy / watch / caution`은 계산 결과 확인용 1차 라벨이며, 보고서에서는 HSI 상태 정의표로 재해석한다고 설명한다.
- [ ] 분위수 방식은 기본 실험 기준, z-score 방식은 보조 비교 실험으로 설명한다.
- [ ] 월말 HSI 상태를 다음 달 수익률에 적용하는 시점 분리 구조를 설명한다.
- [ ] 이전 HSI 예비 실험과 현재 정식 1차 테스트의 관계를 `docs/work_project_report_log.md`에 기록한다.
- [ ] 발표용 그림과 표를 필수 / 선택 / 부록으로 나누어 관리한다.
