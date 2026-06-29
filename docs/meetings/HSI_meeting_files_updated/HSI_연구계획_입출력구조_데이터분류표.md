# HSI 기반 ETF 방어형 Overlay 연구계획 및 입출력 구조표

## 1. 연구 배경

본 프로젝트는 ETF 자산배분 전략에서 시장상태를 어떻게 해석하고, 그 해석을 포트폴리오 비중 조정으로 연결할 수 있는지 확인하기 위한 실험이다. HSI는 개별 ETF의 단순 매수·매도 신호가 아니라, 가격 기반 시장환경신호를 이용해 위험 완화, 관찰, 충돌, 위험 악화, 강한 위험 악화 상태를 분류하는 시장상태 판단 보조지표이다.

프로젝트의 핵심 흐름은 다음과 같다.

```text
ETF 가격 데이터
→ 시장환경신호 생성
→ HSI 방향 및 강도 계산
→ HSI 5상태 분류
→ ETF 비중 조정 규칙 적용
→ 백테스트 및 성과평가
→ Grid Search 및 Robustness 검증
```

---

## 2. 연구문제

| 번호 | 연구문제 | 확인 방법 |
|---:|---|---|
| 1 | HSI 5상태 체계는 `buy / watch / caution`보다 시장상태를 더 설명력 있게 분류할 수 있는가? | HSI 5상태 분포, 상태별 성과, 시각화 비교 |
| 2 | `conflict` 상태는 즉시 방어전환 신호인가, 관찰 상태인가? | main_v2와 main_v2b 비교 |
| 3 | 기존 HSI 5지표에 추세, 위험강도, 손상도, 상대강도 지표를 추가하면 상태분류가 개선되는가? | main_v3a~v3d 신호 조합 실험 |
| 4 | 위험 악화 상태에서 위험자산 비중을 어느 정도 줄이는 것이 적절한가? | 제한된 비중 Grid Search |
| 5 | 선택된 overlay 규칙은 기간, 비용률, 위기구간, 주변 파라미터 변화에도 유지되는가? | Robustness 검증 |

---

## 3. 기준선 정의

### 3-1. 기준 비중 규칙: main_v2b

후속 실험의 기준 비중 규칙은 `main_v2b`이다. `main_v2b`는 `conflict`를 위험 악화 확정 상태로 보지 않고 관찰 상태로 처리한 규칙이다. 앞선 main_v2와 main_v2b 비교에서 main_v2b는 main_v2 대비 평균 Turnover를 줄였고, rank 기준에서는 EW 대비 MDD도 소폭 개선하였다. 따라서 후속 신호 조합 실험에서는 비중 규칙을 `main_v2b`로 고정한다.

| HSI 상태 | 의미 | 069500 위험자산 비중 | 114260 비중 | 153130 비중 | 행동 |
|---|---|---:|---:|---:|---|
| `risk_relief` | 위험 완화 우세 | 0.3333 | 0.3333 | 0.3334 | 기본 유지 |
| `neutral_watch` | 관찰·중립 | 0.3333 | 0.3333 | 0.3334 | 기본 유지 |
| `conflict` | 충돌 상태 | 0.3333 | 0.3333 | 0.3334 | 관찰 처리 |
| `risk_warning` | 위험 악화 우세 | 0.20 | 0.40 | 0.40 | 방어 강화 |
| `accident_zone` | 강한 위험 악화 | 0.10 | 0.45 | 0.45 | 강한 방어전환 |

---

### 3-2. 기준 신호 조합: 기존 HSI 5지표

기존 HSI 5지표는 초기 HSI 체계의 기준 신호 조합이다.

| 번호 | 신호 | 역할 | 방향 처리 |
|---:|---|---|---|
| 1 | 최근 1개월 수익률 | 단기 수익 흐름 | 안정 신호 → 부호 반전 |
| 2 | 13612W 모멘텀 | 중장기 추세 | 안정 신호 → 부호 반전 |
| 3 | 10개월 SMA 대비 위치 | 장기 추세 위치 | 안정 신호 → 부호 반전 |
| 4 | 최근 3개월 변동성 | 위험 흔들림 | 위험 신호 → 그대로 사용 |
| 5 | 현금성 자산 대비 상대강도 | 위험자산과 현금성 자산의 상대 우위 | 안정 신호 → 부호 반전 |

HSI 방향 해석은 다음과 같이 통일한다.

```text
HSI 방향 점수 > 0  → 위험 악화
HSI 방향 점수 < 0  → 위험 완화
```

이 기준 조합을 유지한 상태에서 추가 지표를 역할별로 더해보아야 성과 변화의 원인을 해석할 수 있다.

---

## 4. 데이터 담당자 입출력 구조

### 4-1. 데이터 담당자 입력 데이터

| 분류 | 입력 데이터 | 설명 |
|---|---|---|
| 원천 가격 | `data/raw/korea_etf.csv` | ETF 원천 가격 데이터 |
| 참고 자료 | `data/raw/sample_30stocks.xlsx` | 필요 시 참고용 종목 또는 샘플 데이터 |
| 이벤트 자료 | `data/reference/event_calendar_us_kr.csv` | HSI 상태와 시장 이벤트 비교용 |
| ETF 분류 | ETF 티커, 이름, 자산군 | 위험자산, 채권형, 현금성 구분 |

### 4-2. 데이터 담당자 출력 데이터

| 분류 | 출력 파일 | 설명 |
|---|---|---|
| 정제 가격 | `data/processed/daily_prices.csv` | ETF 일별 가격 |
| 월말 가격 | `data/processed/monthly_prices.csv` | ETF 월말 가격 |
| 월간 수익률 | `data/processed/monthly_returns.csv` | ETF 월간 수익률 |
| ETF 유니버스 | `output/tables/selected_etf_universe.csv` | 사용 ETF 목록 및 역할 |
| 데이터 품질 | `output/tables/flex_data_quality_summary.csv` | 결측치, 기간, 기본 품질 확인 |
| 확장 신호 입력 | `data/processed/hsi_signal_inputs_extended.csv` | 기존 HSI 5지표 및 추가 지표 후보 |

### 4-3. 확장 신호 입력 데이터 분류표

| 분류 | 컬럼 예시 | 설명 |
|---|---|---|
| 기준일 | `Date` | 일별 또는 월말 기준일 |
| 기존 수익 신호 | `ret_1m` | 최근 1개월 수익률 |
| 기존 추세 신호 | `momentum_13612w`, `sma10_gap` | 중장기 모멘텀과 SMA 대비 위치 |
| 기존 위험 신호 | `vol_3m` | 최근 3개월 변동성 |
| 기존 상대강도 | `relative_strength_cash` | 현금성 자산 대비 상대강도 |
| 추가 추세 신호 | `ma20_gap`, `ma60_gap` | 단기·중기 이동평균 대비 위치 |
| 추가 위험강도 | `vol20`, `drawdown_60` | 단기 변동성 및 60일 고점 대비 하락률 |
| 추가 상대강도 | `risk_vs_cash_ret20` | 위험자산 20일 수익률 - 현금성 자산 20일 수익률 |

---

## 5. 사용자/전략 담당 입출력 구조

### 5-1. 전략 담당 입력 데이터

| 분류 | 입력 파일 | 설명 |
|---|---|---|
| 월간 수익률 | `data/processed/monthly_returns.csv` | 백테스트 수익률 입력 |
| 확장 신호 입력 | `data/processed/hsi_signal_inputs_extended.csv` | HSI 상태 분류 입력 |
| 기준 상태표 | `output/tables/main_v2_hsi_state5_table_rank.csv` | rank 기준 기존 HSI 5상태 |
| 기준 상태표 | `output/tables/main_v2_hsi_state5_table_zscore.csv` | zscore 기준 기존 HSI 5상태 |
| 기준 비중 규칙 | `output/tables/main_v2b_allocation_rule_table.csv` | main_v2b 기준 비중 |
| 상태 정의표 | `output/tables/main_v2_hsi_state5_definition.csv` | HSI 5상태 의미 |

### 5-2. 전략 담당 출력 데이터

| 분류 | 출력 파일 | 설명 |
|---|---|---|
| 신호 조합별 상태표 | `output/tables/main_v3_hsi_state_table_*.csv` | 신호 조합별 HSI 5상태 |
| 백테스트 시계열 | `output/tables/main_v3_backtest_timeseries_*.csv` | 월간 수익률, 누적수익률, Drawdown |
| 전략 비중표 | `output/tables/main_v3_strategy_weights_*.csv` | 월별 ETF 비중 |
| 성과 요약표 | `output/tables/main_v3_performance_summary_*.csv` | CAGR, Sharpe, MDD, Calmar 등 |
| Grid Search 전체 결과 | `output/tables/main_v3_grid_search_results.csv` | 전체 후보 성과 |
| Turnover 필터 결과 | `output/tables/main_v3_grid_filtered_candidates.csv` | Turnover 상한 통과 후보 |
| 탈락 사유표 | `output/tables/main_v3_grid_exclusion_reason_table.csv` | 제외된 후보와 이유 |
| Robustness 결과 | `output/tables/main_v3_robustness_results.csv` | 기간, 비용, 위기구간 검증 |
| 최종 판단표 | `output/tables/main_v3_final_candidate_judgement.csv` | 최종 후보 선정 근거 |

---

## 6. 후속 실험 설계

### 6-1. 신호 조합 실험

신호 조합 실험에서는 비중 규칙을 `main_v2b`로 고정하고, 신호 조합만 바꾼다.

| 실험명 | 신호 조합 | 고정 조건 | 질문 |
|---|---|---|---|
| `main_v3_baseline` | 기존 HSI 5지표 | main_v2b 비중 규칙 | 기준 성과 확인 |
| `main_v3a_trend` | 기존 5지표 + `ma20_gap`, `ma60_gap` | main_v2b 비중 규칙 | 추세 보강 효과 확인 |
| `main_v3b_risk_damage` | 기존 5지표 + `vol20`, `drawdown_60` | main_v2b 비중 규칙 | 위험강도 보강 효과 확인 |
| `main_v3c_relative_strength` | 기존 5지표 + `risk_vs_cash_ret20` | main_v2b 비중 규칙 | 상대강도 보강 효과 확인 |
| `main_v3d_core_signal_enhanced` | 기존 5지표 + 추가 5지표 전체 | main_v2b 비중 규칙 | 통합 보강형 효과 확인 |

### 6-2. 제한된 비중 Grid Search

신호 조합 실험에서 해석 가능한 후보가 확인된 뒤에만 비중 Grid Search를 수행한다.

| 상태 | 위험자산 비중 후보 |
|---|---:|
| `risk_relief` | 0.3333 또는 0.40 |
| `neutral_watch` | 0.3333 |
| `conflict` | 0.3333 또는 0.30 |
| `risk_warning` | 0.25, 0.20, 0.15 |
| `accident_zone` | 0.15, 0.10, 0.05 |

조건:

- HSI 상태가 나빠질수록 위험자산 비중이 커지지 않는다.
- 위험자산 비중을 줄인 만큼 114260과 153130에 균등 배분한다.
- 수익률 1등 조합이 아니라 MDD, Calmar, Sharpe, Turnover를 함께 본다.

---

## 7. Turnover 및 거래비용 처리

본 프로젝트에서는 실제 ETF 거래비용을 정밀 추정하기보다, 백테스트 평가 방식으로서 합리적인 단순화 가정을 적용한다. 거래비용은 원천 가격 데이터처럼 외부에서 반드시 받아와야 하는 입력값이 아니라, HSI overlay 전략이 만들어낸 비중 변화와 Turnover에 따라 사후적으로 발생하는 평가 조건으로 처리한다.

Turnover*(설명: 리밸런싱할 때 자산 비중이 얼마나 바뀌었는지를 나타내는 값이다. Turnover가 크면 그만큼 매매가 많이 일어난 것으로 해석할 수 있다.)*

거래비용은 팀 합의에 따라 단순 비용률 시나리오로 설정한다. 예를 들어 비용률을 0.05%, 0.10%, 0.20% 등으로 둘 수 있으나, 이는 실제 비용을 정확히 추정했다는 의미가 아니라 비용 부담을 반영한 민감도 검증 조건이다.

Turnover 상한 예비 기준은 다음과 같다.

```text
avg_turnover <= 0.05
max_turnover <= 0.25
```

Turnover 상한을 적용하지 않은 전체 결과표도 보고서에 제시한다. 이 표는 모든 후보의 순수 성과와 위험 특성을 확인하기 위한 1차 비교표이다. 이후 Turnover 상한을 적용한 후보표를 별도로 제시하여, 성과는 좋아 보이지만 과도한 매매를 유발하는 후보를 제외하거나 후순위로 둔다.

---

## 8. Robustness 검증

Robustness 검증은 선택된 후보가 특정 기간이나 특정 파라미터에만 우연히 잘 맞은 것이 아닌지 확인하는 절차이다.

| 검증 | 질문 |
|---|---|
| 기간 분할 | 초반, 중반, 후반에서도 결과가 유지되는가? |
| 위기구간 | 큰 하락 구간에서 방어 효과가 있는가? |
| 거래비용 | 비용률을 반영해도 결과가 크게 무너지지 않는가? |
| 주변 파라미터 | 인접 비중 후보에서도 결과가 급격히 나빠지지 않는가? |
| rank / zscore | 특정 점수화 방식에서만 우연히 좋은 결과는 아닌가? |

---

## 9. 최종 판단 논리

최종 후보는 수익률이 가장 높은 조합이 아니라 다음 조건을 함께 만족하는 조합으로 판단한다.

| 기준 | 해석 |
|---|---|
| HSI 상태 해석 | 상태 분류가 논리적으로 설명 가능한가? |
| MDD | EW 대비 낙폭이 개선되거나 최소한 악화되지 않는가? |
| Drawdown | 큰 하락 구간에서 방어 효과가 있는가? |
| Sharpe / Calmar | 위험 대비 성과가 과도하게 훼손되지 않는가? |
| Turnover | 과도한 매매를 유발하지 않는가? |
| Robustness | 기간, 비용, 위기구간, 주변 파라미터 변화에도 유지되는가? |

본 프로젝트의 후속 최적화는 “성과가 가장 높은 조합 찾기”가 아니라, “HSI 상태 해석이 유지되고, 위험관리 효과가 있으며, 과도한 매매 없이 실제 운용 가능성이 있는 방어형 overlay 규칙 찾기”로 정의한다.