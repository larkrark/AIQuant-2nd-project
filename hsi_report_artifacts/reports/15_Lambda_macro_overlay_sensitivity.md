# 15_Lambda_macro_overlay_sensitivity

## 실험명
**15번 Lambda + Macro Overlay Sensitivity 실험: Lambda 후보 위 macro 보조 신호의 반영 강도 민감도 확인**

## 1. 실험 목적

이 실험의 목적은 최종 후보로 남은 **Lambda 0.1**과 **Lambda 0.3** 위에 macro companion*을 약하게 얹었을 때, MDD를 낮추면서 CAGR과 Turnover를 크게 훼손하지 않는지를 확인하는 것이다.

15번은 새로운 대형 최적화 실험이 아니라, 이미 남은 Lambda 후보 위에 macro 보조 신호를 얹어도 최종 후보가 바뀔 만큼의 개선이 있는지 확인하는 **민감도 진단 실험**이다.

macro companion(설명: HSI 상태분류를 대체하지 않고, 금리·환율 등 외생 거시환경을 이용해 위험자산 비중을 소폭 조정하는 보조 신호이다.)  
MDD(설명: Maximum Drawdown의 약자이다. 투자기간 중 고점 대비 최대 하락폭을 뜻한다.)  
Turnover(설명: 포트폴리오 비중이 얼마나 많이 바뀌었는지를 나타내는 회전율이다. 거래비용 부담과 연결된다.)

---

## 2. 배경과 이유

앞선 실험에서 Lambda 0.1과 Lambda 0.3은 HSI baseline의 과도한 비중 이동 문제를 완화하는 후보로 남았다. 그러나 HSI는 가격 기반 시장상태 번역 신호이므로, 금리와 환율 같은 외생 macro 압력을 약하게 반영했을 때 방어력이 추가로 개선될 가능성이 있었다.

따라서 본 실험에서는 Lambda 후보를 유지한 상태에서 macro overlay 강도만 소수의 사전 설정값으로 바꾸어 보았다. 조합 수는 다음과 같이 제한하였다.

| 구분 | 값 |
|---|---|
| Lambda 후보 | 0.1, 0.3 |
| macro_scale 후보 | 0.00, 0.25, 0.50, 0.75 |
| 전체 조합 수 | 8 |
| 조합 상한 | 24 |

이 설정은 과거 구간에 맞춘 과도한 최적화를 피하고, macro 보조 신호의 강도 변화에 따른 성과 민감도만 확인하기 위한 것이다.

---

## 3. GDP 처리와 macro signal version

초기 macro companion 설계에서는 금리, 환율, GDP를 함께 검토하였다. 그러나 GDP는 분기자료이고, 계절성·기저효과·발표 지연 문제가 있어 월간 ETF 리밸런싱 전략의 직접 신호로 사용하기에는 설명 부담이 크다. 따라서 본 실험에서는 GDP를 직접 위험 조건에서 제외하고, 금리와 환율의 위험형 이탈을 중심으로 macro overlay를 구성하였다.

본 산출물에서 확인된 macro signal version은 다음과 같다.

```text
no_gdp_rate_fx_verified
```

`no_gdp_rate_fx_verified`는 금리·환율 컬럼을 이용해 GDP 제외 신호가 확인된 경우를 의미한다. 이번 산출물에서는 해당 버전이 확인되었으므로, 15번 실험은 GDP를 제외한 금리·환율 중심 macro overlay 민감도 실험으로 해석할 수 있다.

[GDP 제외 해석 placeholder] 최종 보고서에서는 데이터 담당자 검토 의견을 함께 연결하여, GDP를 비교·진단용으로만 두고 최종 비중 조정 신호에서 제외한 이유를 한 문단으로 정리한다.

---

## 4. 사용 데이터

- Lambda 후보 목표비중 및 HSI 상태 데이터: `main_final_baseline_rebalance_weights.csv`
- HSI-macro 결합 월별 데이터: `main_final_hsi_macro_companion_joined_monthly.csv`
- ETF 월간 수익률 데이터: `main_final_monthly_return_decimal.csv`
- 전략별 월별 결과: `main_final_lambda_macro_overlay_sensitivity_timeseries.csv`
- 성과 요약표: `main_final_lambda_macro_overlay_sensitivity_summary.csv`
- 선택 점수 정렬표: `main_final_lambda_macro_overlay_sensitivity_ranked.csv`
- 대시보드용 후보 행: `main_final_lambda_macro_overlay_sensitivity_dashboard_rows.csv`
- Markdown note: `main_final_lambda_macro_overlay_sensitivity_note.md`

전략별 월별 결과는 총 1368행이며, 이는 8개 조합과 월별 백테스트 구간이 결합된 결과이다. `return_month` 기준 고유 월 수는 171개로 확인된다.

---

## 5. 실험 방법

본 실험의 흐름은 다음과 같다.

```text
HSI 상태별 목표비중
→ Lambda 0.1 / 0.3 부분조정 비중 산출
→ 금리·환율 기반 macro 위험 flag 확인
→ macro_scale에 따라 069500 위험자산 비중을 소폭 축소
→ 축소분을 국고채3년 ETF와 단기채권 ETF로 배분
→ 월별 수익률 백테스트
```

macro overlay는 HSI 상태를 대체하지 않는다. HSI는 시장상태 판단을 담당하고, Lambda는 목표비중으로 이동하는 속도를 담당하며, macro companion은 위험자산 비중을 아주 약하게 조정하는 방어 보조 장치로 사용된다.

[macro overlay 규칙 placeholder] 최종 코드 설명서에서는 `macro_overlay_delta`, `overlay_strength_no_gdp`, `macro_defense_addon_no_gdp`의 계산 규칙을 대표 함수 또는 코드 주석과 함께 별도 정리한다.

---

## 6. 주요 결과

### 6.1 전체 조합 성과 요약

| 전략 ID | Lambda | macro_scale | CAGR(%) | MDD(%) | Sharpe | Sortino | Calmar | 평균 Turnover(%) | 20bp 비용 drag(%p) | 조정 월 수 | 평균 macro 조정폭(%p) | 후보 판정 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lambda_0.1_macro_0.00 | 0.100 | 0.000 | 8.692 | -14.744 | 0.787 | 1.555 | 0.590 | 2.455 | 0.064 | 0.000 | 0.000 | lambda_base |
| lambda_0.1_macro_0.25 | 0.100 | 0.250 | 8.671 | -14.722 | 0.787 | 1.553 | 0.589 | 2.501 | 0.065 | 37.000 | 0.086 | diagnostic |
| lambda_0.1_macro_0.50 | 0.100 | 0.500 | 8.650 | -14.700 | 0.787 | 1.551 | 0.588 | 2.552 | 0.066 | 37.000 | 0.172 | diagnostic |
| lambda_0.1_macro_0.75 | 0.100 | 0.750 | 8.629 | -14.678 | 0.787 | 1.548 | 0.588 | 2.609 | 0.068 | 37.000 | 0.258 | diagnostic |
| lambda_0.3_macro_0.00 | 0.300 | 0.000 | 9.148 | -15.220 | 0.779 | 1.407 | 0.601 | 6.886 | 0.180 | 0.000 | 0.000 | lambda_base |
| lambda_0.3_macro_0.25 | 0.300 | 0.250 | 9.126 | -15.198 | 0.779 | 1.405 | 0.600 | 6.933 | 0.181 | 37.000 | 0.086 | diagnostic |
| lambda_0.3_macro_0.50 | 0.300 | 0.500 | 9.105 | -15.175 | 0.779 | 1.403 | 0.600 | 6.984 | 0.182 | 37.000 | 0.172 | diagnostic |
| lambda_0.3_macro_0.75 | 0.300 | 0.750 | 9.083 | -15.153 | 0.779 | 1.400 | 0.599 | 7.039 | 0.184 | 37.000 | 0.258 | diagnostic |

전체 결과를 보면 macro_scale이 커질수록 MDD는 아주 소폭 개선되는 방향을 보였지만, CAGR은 낮아지고 Turnover와 비용 drag는 증가하는 흐름이 나타났다. 즉, macro overlay는 작동하지 않은 것이 아니라 **작동은 했지만 개선 폭이 제한적**이었다.

---

### 6.2 Lambda 단독 대비 macro overlay 차이

| 전략 ID | Lambda | macro_scale | CAGR 차이(%p) | MDD 차이(%p) | Sharpe 차이 | Calmar 차이 | Turnover 차이(%p) | 20bp 비용 차이(%p) | 후보 판정 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lambda_0.1_macro_0.00 | 0.1000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | lambda_base |
| lambda_0.1_macro_0.25 | 0.1000 | 0.2500 | -0.0212 | 0.0222 | 0.0002 | -0.0006 | 0.0455 | 0.0011 | diagnostic |
| lambda_0.1_macro_0.50 | 0.1000 | 0.5000 | -0.0424 | 0.0444 | 0.0004 | -0.0011 | 0.0969 | 0.0024 | diagnostic |
| lambda_0.1_macro_0.75 | 0.1000 | 0.7500 | -0.0637 | 0.0666 | 0.0005 | -0.0017 | 0.1538 | 0.0039 | diagnostic |
| lambda_0.3_macro_0.00 | 0.3000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | lambda_base |
| lambda_0.3_macro_0.25 | 0.3000 | 0.2500 | -0.0215 | 0.0222 | -0.0001 | -0.0005 | 0.0476 | 0.0012 | diagnostic |
| lambda_0.3_macro_0.50 | 0.3000 | 0.5000 | -0.0430 | 0.0444 | -0.0002 | -0.0011 | 0.0981 | 0.0024 | diagnostic |
| lambda_0.3_macro_0.75 | 0.3000 | 0.7500 | -0.0645 | 0.0666 | -0.0003 | -0.0016 | 0.1531 | 0.0038 | diagnostic |

Lambda 0.1 기준으로 macro_scale을 0.75까지 높였을 때의 변화는 다음과 같다.

```text
CAGR -0.0637%p, MDD 0.0666%p, Sharpe 0.0005, Calmar -0.0017, Turnover 0.1538%p
```

Lambda 0.3 기준으로 macro_scale을 0.75까지 높였을 때의 변화는 다음과 같다.

```text
CAGR -0.0645%p, MDD 0.0666%p, Sharpe -0.0003, Calmar -0.0016, Turnover 0.1531%p
```

두 Lambda 계열 모두에서 macro_scale이 커질수록 MDD는 아주 소폭 개선되지만, CAGR과 Calmar는 낮아지고 Turnover는 증가한다. 따라서 macro overlay는 최종 후보를 대체하거나 뒤집는 개선 요인이라기보다, 방어 성향을 조금 더하는 보조 장치에 가깝다.

---

### 6.3 동적 선택 점수 순위

| 전략 ID | 선택 점수 | CAGR(%) | MDD(%) | Sharpe | Calmar | 평균 Turnover(%) | 후보 판정 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lambda_0.1_macro_0.00 | 0.6857 | 8.6924 | -14.7442 | 0.7865 | 0.5895 | 2.4554 | lambda_base |
| lambda_0.1_macro_0.25 | 0.6802 | 8.6712 | -14.7220 | 0.7867 | 0.5890 | 2.5009 | diagnostic |
| lambda_0.1_macro_0.50 | 0.6739 | 8.6500 | -14.6998 | 0.7869 | 0.5884 | 2.5523 | diagnostic |
| lambda_0.1_macro_0.75 | 0.6668 | 8.6287 | -14.6776 | 0.7870 | 0.5879 | 2.6092 | diagnostic |
| lambda_0.3_macro_0.00 | 0.3375 | 9.1475 | -15.2197 | 0.7793 | 0.6010 | 6.8856 | lambda_base |
| lambda_0.3_macro_0.25 | 0.3283 | 9.1261 | -15.1975 | 0.7792 | 0.6005 | 6.9332 | diagnostic |
| lambda_0.3_macro_0.50 | 0.3185 | 9.1046 | -15.1753 | 0.7791 | 0.6000 | 6.9836 | diagnostic |
| lambda_0.3_macro_0.75 | 0.3080 | 9.0830 | -15.1531 | 0.7790 | 0.5994 | 7.0387 | diagnostic |

동적 선택 점수 기준 1순위는 **lambda_0.1_macro_0.00**이다. 이는 macro overlay를 추가하지 않은 Lambda 0.1 단독 조합이다. 따라서 15번 실험은 macro overlay가 최종 후보를 바꾸지 못했다는 결론을 강화한다.

---

### 6.4 후보 판정 분포

| 후보 판정 | 개수 |
| --- | --- |
| diagnostic | 6 |
| lambda_base | 2 |

후보 판정에서도 macro_scale 0.00 조합은 Lambda 단독 기준 후보로 남고, macro overlay가 적용된 조합은 diagnostic으로 분류되었다. 이는 macro overlay가 최종 후보가 아니라 보조 진단 실험이라는 해석과 일치한다.

---

### 6.5 대시보드용 후보 행

| 모델 ID | 계열 | 단계 | 판정 | CAGR | MDD | Sharpe | Calmar | 평균 Turnover | 해석 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Lambda 0.1 | lambda | current | final_candidate | 8.6924 | -14.7442 | 0.7865 | 0.5895 | 2.4554 | macro overlay를 얹지 않은 Lambda 기준 후보입니다. |
| Lambda 0.1 + Macro 0.25 | lambda_macro_overlay | current | diagnostic | 8.6712 | -14.7220 | 0.7867 | 0.5890 | 2.5009 | macro_scale은 최적화 계수가 아니라 macro 보조 신호의 방어 강도 민감도 계수입니다. |
| Lambda 0.1 + Macro 0.50 | lambda_macro_overlay | current | diagnostic | 8.6500 | -14.6998 | 0.7869 | 0.5884 | 2.5523 | macro_scale은 최적화 계수가 아니라 macro 보조 신호의 방어 강도 민감도 계수입니다. |
| Lambda 0.1 + Macro 0.75 | lambda_macro_overlay | current | diagnostic | 8.6287 | -14.6776 | 0.7870 | 0.5879 | 2.6092 | macro_scale은 최적화 계수가 아니라 macro 보조 신호의 방어 강도 민감도 계수입니다. |
| Lambda 0.3 | lambda | current | final_candidate | 9.1475 | -15.2197 | 0.7793 | 0.6010 | 6.8856 | macro overlay를 얹지 않은 Lambda 기준 후보입니다. |
| Lambda 0.3 + Macro 0.25 | lambda_macro_overlay | current | diagnostic | 9.1261 | -15.1975 | 0.7792 | 0.6005 | 6.9332 | macro_scale은 최적화 계수가 아니라 macro 보조 신호의 방어 강도 민감도 계수입니다. |
| Lambda 0.3 + Macro 0.50 | lambda_macro_overlay | current | diagnostic | 9.1046 | -15.1753 | 0.7791 | 0.6000 | 6.9836 | macro_scale은 최적화 계수가 아니라 macro 보조 신호의 방어 강도 민감도 계수입니다. |
| Lambda 0.3 + Macro 0.75 | lambda_macro_overlay | current | diagnostic | 9.0830 | -15.1531 | 0.7790 | 0.5994 | 7.0387 | macro_scale은 최적화 계수가 아니라 macro 보조 신호의 방어 강도 민감도 계수입니다. |

대시보드용 후보 행은 이후 Streamlit 또는 발표용 후보 비교표에 연결하기 위한 요약 형식이다. 본 보고서에서는 숫자 해석을 중심으로 사용하고, 실제 대시보드 반영 여부는 팀의 최종 발표 구성에 맞춰 결정한다.

---

## 7. 성과 귀인과 해석

15번 실험의 핵심은 다음과 같다.

1. **macro overlay는 방어 방향으로 작동했다.**  
   macro_scale이 커질수록 MDD는 아주 소폭 개선되는 흐름이 나타났다.

2. **하지만 개선 폭은 제한적이었다.**  
   MDD 개선 폭은 작았고, 그 대가로 CAGR과 Calmar가 낮아지고 Turnover와 비용 drag가 증가하였다.

3. **최종 후보를 바꿀 정도의 효과는 없었다.**  
   동적 선택 점수 1위는 `lambda_0.1_macro_0.00`으로, macro overlay를 추가하지 않은 Lambda 0.1 단독 조합이었다.

4. **GDP 제외 구조는 확인되었다.**  
   macro signal version이 `no_gdp_rate_fx_verified`로 확인되었으므로, 15번은 GDP가 직접 위험 조건에 들어간 실험이 아니라 금리·환율 중심의 no-GDP macro overlay 실험이다.

따라서 15번 실험은 macro overlay를 최종 후보로 올리는 실험이 아니라, **macro 보조 신호를 최종 전략에서 조심스럽게 제외하거나 diagnostic layer로 낮출 근거**를 제공한다.

---

## 8. 한계와 다음 판단

본 실험은 macro_scale을 0.00, 0.25, 0.50, 0.75의 사전 설정값으로만 비교하였다. 이는 과도한 조합 탐색을 피하기 위한 장점이 있지만, macro overlay의 모든 가능성을 검토한 것은 아니다. 또한 macro 변수는 금리와 환율 중심으로 제한되었기 때문에, 다른 macro 변수 조합에 대한 일반 결론으로 확장해서는 안 된다.

최종 판단은 다음과 같이 정리한다.

| 항목 | 판단 |
|---|---|
| Lambda 0.1 단독 | 저회전·보수형 후보로 유지 |
| Lambda 0.3 단독 | 수익성·Calmar 균형형 후보로 유지 |
| Lambda + macro overlay | 최종 후보가 아니라 diagnostic 보조 실험 |
| GDP | 최종 비중 조정 신호에서 제외. 비교·진단용 |
| macro companion | HSI를 대체하지 않는 약한 방어 보조 layer |

[팀 검토 placeholder] macro overlay를 최종 후보가 아니라 보조 실험으로 분류하는 방향은 현재 수치상 타당하지만, 최종 발표에서는 팀 합의 문구로 정리한다.

[추가 검증 필요] 향후 확장에서는 macro overlay를 비중 조정값으로 직접 얹는 방식보다, HSI 상태별 Lambda 값을 다르게 적용하는 동적 Lambda 구조를 검토할 수 있다.

---

# 별도 첨부 1. 입출력 구조표

| 구분 | 파일명 | 역할 | 주요 컬럼 | 시점 기준 | 단위 |
|---|---|---|---|---|---|
| 입력 | `main_final_baseline_rebalance_weights.csv` | HSI 상태별 목표비중 및 기준 정보 | `year_month`, `hsi_state`, ETF별 목표비중 | 월말 신호 | weight |
| 입력 | `main_final_hsi_macro_companion_joined_monthly.csv` | HSI와 macro companion 결합 월별 데이터 | `year_month`, `rate_z`, `fx_z`, `macro_risk_flag` 등 | 월말 macro | z-score / flag |
| 입력 | `main_final_monthly_return_decimal.csv` | ETF 월간 수익률 | `year_month`, `069500`, `114260`, `153130` | 월별 | decimal |
| 출력 | `main_final_lambda_macro_overlay_sensitivity_timeseries.csv` | 전략별 월별 수익률과 비중 결과 | `strategy_id`, `return_month`, `weight_069500`, `portfolio_return` 등 | 월별 | decimal / weight |
| 출력 | `main_final_lambda_macro_overlay_sensitivity_summary.csv` | 8개 조합 성과 요약 | CAGR, MDD, Sharpe, Sortino, Calmar, Turnover, macro_signal_version | 전체기간 | % / ratio |
| 출력 | `main_final_lambda_macro_overlay_sensitivity_ranked.csv` | 선택 점수 기준 정렬표 | selection_score, candidate_decision | 전체기간 | score |
| 출력 | `main_final_lambda_macro_overlay_sensitivity_dashboard_rows.csv` | 대시보드 반영 후보 행 | model_id, decision, interpretation | 요약 | text / numeric |
| 출력 | `main_final_lambda_macro_overlay_sensitivity_note.md` | 실험 목적과 결론 요약 노트 | purpose, GDP 처리, 보고서 문장 | 요약 | text |

---

# 별도 첨부 2. 입출력 데이터 분류표

| 데이터 분류 | 파일명 | 설명 | 최종 전략 사용 여부 | 보고서 사용 위치 |
|---|---|---|---|---|
| processed | `main_final_baseline_rebalance_weights.csv` | HSI 상태와 목표비중 데이터 | 사용 | Lambda 비중 계산 |
| processed | `main_final_hsi_macro_companion_joined_monthly.csv` | HSI와 macro 결합 데이터 | 사용 | macro risk flag 계산 |
| processed | `main_final_monthly_return_decimal.csv` | ETF 월간 수익률 계산용 데이터 | 사용 | 백테스트 수익률 계산 |
| model_output | `main_final_lambda_macro_overlay_sensitivity_timeseries.csv` | 8개 조합의 월별 수익률과 비중 결과 | 사용 | 성과 계산 원천 |
| report_output | `main_final_lambda_macro_overlay_sensitivity_summary.csv` | 전체 조합 성과표 | 사용 | 본문 표 |
| report_output | `main_final_lambda_macro_overlay_sensitivity_ranked.csv` | 선택 점수 정렬표 | 사용 | 후보 판정 |
| report_output | `main_final_lambda_macro_overlay_sensitivity_dashboard_rows.csv` | 대시보드 후보 행 | 참고 | 발표/대시보드 연결 |
| report_output | `main_final_lambda_macro_overlay_sensitivity_note.md` | 실험 요약 노트 | 사용 | 해석 문장 |

---

# 별도 첨부 3. 보고서용 최종 요약 문장

15번 후속 실험에서는 Lambda 0.1과 Lambda 0.3 후보 위에 macro companion을 직접 비중 보정값으로 얹는 방식을 비교하였다. macro_scale은 성과를 임의로 개선하기 위한 최적화 계수가 아니라, macro 보조 신호의 반영 강도에 따른 민감도를 확인하기 위한 사전 설정 범위로 사용하였다. 실험 결과 macro_scale이 커질수록 MDD는 아주 소폭 개선되었으나, CAGR과 Calmar는 낮아지고 Turnover 및 거래비용 민감도는 증가하였다. 또한 동적 선택 점수 1위는 macro overlay를 적용하지 않은 `lambda_0.1_macro_0.00`이었다. 따라서 macro companion은 최종 후보를 대체하는 독립 전략이 아니라, HSI-Lambda 구조 위에 얹는 diagnostic 보조 실험으로 분류하는 것이 적절하다.
