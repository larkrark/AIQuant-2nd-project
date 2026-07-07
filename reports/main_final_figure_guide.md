# HSI Overlay 프로젝트 — 보고서용 시각화 안내문

본 문서는 35_visual_report_pack.py가 생성한 그림을 최종 보고서에 삽입할 때 사용할 소개·분석·해석 초안이다.  
각 그림은 단순 장식이 아니라 강사님 피드백의 핵심 항목인 리밸런싱 구성, IS/OOS 성과, BM 비교, 변동성, MDD, Sharpe, factor loading, adoption decision을 설명하기 위한 근거 자료이다.

---

## 1. 리밸런싱 일자별 포트폴리오 구성 비중 — dynamic_v1

파일: `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\figures\main_final_fig_weights_dynamic_v1.png`

### 그림 소개
이 그림은 dynamic_v1 전략이 각 리밸런싱 적용월에 069500, 114260, 153130에 어떤 비중을 배분했는지 보여준다. 069500은 위험자산, 114260은 채권형 방어자산, 153130은 현금성 방어자산으로 해석한다.

### 분석
dynamic_v1은 HSI 상태별 목표비중을 바로 따라가는 전략이 아니라, annualized volatility, rolling drawdown, risk_relief 지속 조건에 따라 목표비중 반영 속도 λ를 조정한다. 따라서 동일한 HSI 상태 변화가 있더라도 실제 포트폴리오 비중은 λ에 의해 완만하게 이동한다.

### 해석
이 그림은 본 전략이 고정비중 포트폴리오가 아니라 월별 시장상태와 위험조건에 따라 실제 비중을 조정하는 방어형 Overlay임을 보여준다. 다만 이 결과는 수익률 예측이 아니라 상태 해석과 실행속도 조절의 결과로 해석해야 한다.

---

## 2. 리밸런싱 일자별 포트폴리오 구성 비중 — dynamic_v1_macro

파일: `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\figures\main_final_fig_weights_dynamic_v1_macro.png`

### 그림 소개
이 그림은 MacroRisk 조건을 추가한 dynamic_v1_macro 전략의 월별 포트폴리오 구성 비중을 보여준다.

### 분석
dynamic_v1_macro는 기존 dynamic_v1 조건에 MacroRisk >= 2 조건을 추가하였다. MacroRisk는 rate_up_flag와 fx_up_flag의 단순 합이며, MacroRisk >= 2는 금리 상승 압력과 환율 상승 압력이 동시에 관찰되는 달을 의미한다.

### 해석
dynamic_v1_macro는 macro 조건을 실제로 반영했지만, 검증 결과 기존 dynamic_v1 대비 CAGR, MDD, Calmar를 명확히 개선하지는 못했다. 대신 평균 Turnover와 연환산 변동성을 소폭 낮추는 효과가 있었다. 따라서 기본 시변 λ 후보는 dynamic_v1로 유지하고, dynamic_v1_macro는 macro-aware 저회전·보수 확장안으로 해석한다.

---

## 3. 전략별 성과-위험 요약 — FULL 구간

파일: `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\figures\main_final_fig_performance_risk_summary_FULL.png`

### 그림 소개
이 그림은 Fixed 70/20/10 BM, EW, lambda_0.1, lambda_0.3, asym, dynamic_v1, dynamic_v1_macro의 FULL 구간 성과-위험 지표를 비교한다. 지표는 CAGR, 연환산 변동성, MDD, Calmar로 구성했다.

### 분석
Fixed 70/20/10 BM은 CAGR이 가장 높지만 MDD도 가장 크다. 반면 dynamic_v1과 dynamic_v1_macro는 CAGR은 FixedBM보다 낮지만 MDD와 Calmar 측면에서 더 안정적인 성과-위험 균형을 보인다.

### 해석
따라서 본 전략의 핵심은 BM 대비 단순 수익률 우위가 아니라 낙폭 통제와 위험조정 성과 개선이다. 이 프로젝트의 알파는 순수 수익률 알파가 아니라 가격 기반 시장상태 해석을 통한 방어형 낙폭 통제 엣지로 해석한다.

---

## 4. Adoption decision 요약 — OOS, 10bp 비용차감

파일: `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\figures\main_final_fig_adoption_decision_summary.png`

### 그림 소개
이 그림은 OOS 구간에서 10bp 거래비용을 차감한 뒤, 시변 layer 후보들의 Calmar, MDD, tail-month 평균수익, 평균 Turnover를 비교한다.

### 분석
dynamic_v1과 dynamic_v1_macro는 모두 사전등록 비열등 기준을 통과했다. dynamic_v1_macro는 dynamic_v1보다 Turnover가 낮지만, Calmar, MDD, tail-month 방어력은 소폭 낮았다.

### 해석
따라서 dynamic_v1은 기본 시변 λ 후보로 유지하고, dynamic_v1_macro는 MacroRisk 조건을 반영한 보수적 확장안으로 제시한다. 이 결론은 성과가 좋아 보이는 후보를 사후적으로 선택한 것이 아니라, 사전등록한 비열등 조건을 기준으로 판정한 결과이다.

---

## 5. 36개월 Rolling Factor Exposure

파일: `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\figures\main_final_fig_rolling_factor_exposure_core.png`

### 그림 소개
이 그림은 주요 후보의 36개월 rolling factor loading 변화를 보여준다. Market, Bond, Volatility, MacroRisk 노출이 시간에 따라 어떻게 달라졌는지 확인하기 위한 진단 자료이다.

### 분석
rolling factor exposure는 후보를 새로 고르기 위한 최적화 기준이 아니라, 최종 후보가 어떤 팩터 노출을 통해 성과를 만들었는지 설명하기 위한 사후 진단이다.

### 해석
이 그림은 전략의 성과가 단순히 한 구간의 우연한 결과인지, 또는 시장·채권·변동성·거시위험 노출 변화와 연결되어 있는지를 설명하는 데 사용한다. 다만 factor loading은 예측모형이 아니라 설명 도구이므로, 이를 근거로 새로운 λ 후보를 사후 선택하지 않는다.

---

## 6. 이미 생성된 기본 성과 시계열 차트

33_report_outputs.py에서 이미 생성된 기본 차트:

- `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\figures\main_final_fig_cumret_IS.png`
- `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\figures\main_final_fig_cumret_OOS.png`
- `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\figures\main_final_fig_cumret_FULL.png`
- `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\figures\main_final_fig_drawdown_FULL.png`

### 보고서 해석 방향
IS/OOS/FULL 누적수익률 차트는 전략이 특정 전체기간에만 의존하는지 확인하기 위한 자료이다. Drawdown 차트는 본 프로젝트의 핵심이 수익률 극대화가 아니라 낙폭 통제형 방어 Overlay임을 보여주는 핵심 그림이다.

---

## 최종 보고서 문장 요약

본 프로젝트는 동일한 3개 ETF 유니버스 안에서 FixedBM, EW, HSI baseline, 대칭 λ, 비대칭 λ, dynamic λ 후보를 비교하였다. 백테스트 결과를 그대로 신뢰하지 않고 가격-수익률 재현성 검증, factor input 원칙 감사, IS/OOS 분리, walk-forward 평가, 누수 audit, 비용 민감도, adoption decision을 순차적으로 수행하였다.

FixedBM은 CAGR이 가장 높았지만 MDD도 가장 컸다. HSI 기반 λ 전략은 수익률 극대화 전략이 아니라 낙폭 통제형 방어 Overlay로 해석하는 것이 적절하다. dynamic_v1은 OOS와 walk-forward에서 성과-위험 균형이 유지되었고, dynamic_v1_macro는 MacroRisk 조건을 실제로 반영했지만 기존 dynamic_v1을 명확히 개선하지는 못했다. 다만 Turnover와 연환산 변동성을 낮추는 효과가 있어 macro-aware 보수 확장안으로 제시한다.
