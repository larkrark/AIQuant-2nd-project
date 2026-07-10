# HSI 기반 ETF 방어형 Overlay 전략 최종 통합 보고서  
## Fixed 70/20/10 BM을 포함한 최종 후보 선정 및 해석

**작성 목적:** 최종 제출·발표용 통합 보고서 초안  
**작성 기준:** 00~23번 실험 산출물 및 `_with_fixed_bm` 보완판  
**분석 대상 ETF:** 069500, 114260, 153130  
**최종 후보:** Lambda 0.1, Lambda 0.3  
**메인 BM:** Fixed 70/20/10 BM  
**보조 BM:** EW Benchmark  
**주의:** 본 보고서는 수업 및 프로젝트 실험용이며, 특정 ETF에 대한 투자 권유가 아니다.

---

## 1. 핵심 요약

본 프로젝트는 HSI를 미래수익률 예측 모델로 사용하는 것이 아니라, 가격 기반 신호를 시장상태 언어로 번역하고 이를 ETF 비중 조절에 연결하는 방어형 Overlay 전략을 실험하였다. HSI 상태는 위험 완화, 중립 관찰, 신호 충돌, 위험 경고, 강한 위험 구간으로 구분되며, 각 상태는 069500, 114260, 153130의 목표비중으로 연결된다.

최종 결론은 다음과 같다.

| 구분 | 최종 판단 |
|---|---|
| 메인 BM | Fixed 70/20/10 BM |
| 보조 BM | EW Benchmark |
| 내부 기준선 | HSI baseline |
| 최종 후보 1 | Lambda 0.1: 저회전·보수형 후보 |
| 최종 후보 2 | Lambda 0.3: 수익성·Calmar 균형형 후보 |
| 보조 진단 | Signal combo, Event balance, Theta, Macro companion |

Fixed 70/20/10 BM은 CAGR이 가장 높지만 MDD도 크다. Lambda 0.1과 Lambda 0.3은 Fixed BM을 모든 지표에서 이기는 전략이 아니라, Fixed BM 대비 낙폭을 줄이고 EW 대비 성장성과 Calmar를 개선하는 방어형 ETF RA 후보로 해석한다.

CAGR*(설명: 연평균 복리수익률이다. 전체 기간 동안 연평균 어느 정도 성장했는지 보여준다.)  
MDD*(설명: Maximum Drawdown의 약자이다. 투자기간 중 고점 대비 최대 하락폭을 뜻한다.)  
Calmar*(설명: CAGR을 MDD 절댓값으로 나눈 지표이다. 낙폭 대비 수익률을 보는 데 사용한다.)  
Turnover*(설명: 포트폴리오 비중이 얼마나 많이 바뀌었는지를 나타내는 회전율이다. 거래비용 부담과 연결된다.)

---

## 2. 연구 질문

본 프로젝트의 핵심 질문은 다음 네 가지이다.

1. HSI 상태분류를 ETF 비중 조절에 연결할 수 있는가?  
2. HSI baseline은 방어형 자산배분의 기준선으로 작동하는가?  
3. 목표비중으로 이동하는 속도를 조절하는 Lambda 구조가 Turnover와 MDD 부담을 줄이는가?  
4. Fixed 70/20/10 BM과 EW Benchmark를 함께 비교했을 때 최종 후보의 성격은 무엇인가?

---

## 3. 전략 구조

전략 구조는 다음과 같다.

```text
가격 데이터
→ HSI 입력 신호 계산
→ HSI 5상태 분류
→ 상태별 ETF 목표비중 연결
→ t월 말 신호를 t+1월 수익률에 적용
→ Lambda 부분조정으로 목표비중 이동 속도 조절
→ BM, HSI baseline, Lambda 후보 비교
```

본 프로젝트에서 HSI는 예측값이 아니라 **시장상태 번역기**이다. 따라서 HSI 자체가 “다음 달 수익률이 오른다/내린다”를 직접 예측한다고 말하지 않는다. 더 안전한 표현은 다음과 같다.

> HSI는 가격 기반 신호를 종합하여 현재 시장상태를 위험 완화, 중립, 충돌, 위험 경고, 강한 위험 구간으로 번역하고, 이 상태에 따라 ETF 목표비중을 조정하는 데 사용하였다.

---

## 4. ETF 유니버스와 BM 정의

ETF 유니버스는 다음 세 자산으로 구성된다.

| 티커 | ETF 역할 | 전략 내 의미 |
|---|---|---|
| 069500 | 위험자산 | KODEX 200, 국내 주식시장 노출 |
| 114260 | 방어자산 | KODEX 국고채3년, 금리·채권 방어 축 |
| 153130 | 현금성 방어자산 | KODEX 단기채권PLUS, 낮은 변동성 축 |

비교 기준은 다음과 같이 정리한다.

| 구분 | 전략 | 역할 |
|---|---|---|
| 메인 BM | Fixed 70/20/10 BM | 069500 70%, 114260 20%, 153130 10% 고정 |
| 보조 BM | EW Benchmark | 세 ETF 동일비중 |
| 내부 기준선 | HSI baseline | HSI 상태를 목표비중에 즉시 반영 |
| 최종 후보 | Lambda 0.1 / Lambda 0.3 | 목표비중 이동 속도를 완화 |

BM*(설명: Benchmark의 약자이다. 전략 성과를 평가하기 위한 비교 기준이다.)

---

## 5. 실험 흐름

최종 보고서 흐름은 다음 순서로 정리한다.

| 순서 | 보고서 파일 | 역할 |
| --- | --- | --- |
| 1 | 00_05_Project_foundation_and_HSI_baseline.md | 00~05 초반 데이터·HSI baseline 구조 |
| 2 | 06_09_Signal_combo_and_event_balance_diagnostic.md | 06~09 신호조합·event balance 보조진단 |
| 3 | 10_Inertia_lambda_experiment.md | 10 Lambda 부분조정 실험 |
| 4 | 11_Theta_sensitivity_experiment.md | 11 Theta 민감도 실험 |
| 5 | 12_13_Macro_companion_diagnostic.md | 12~13 Macro companion 진단 |
| 6 | 14_Macro_companion_overlay.md | 14 Macro soft overlay 실험 |
| 7 | 15_Lambda_macro_overlay_sensitivity.md | 15 Lambda+macro 민감도 |
| 8 | 16_Regime_robustness_with_fixed_bm.md | 16 Robustness 보완판, Fixed BM 포함 |
| 9 | 17_Benchmark_alignment.md | 17 Benchmark alignment |
| 10 | 20_23_Final_candidate_selection_with_fixed_bm.md | 20~23 최종 후보 선정, Fixed BM 포함 |

---

## 6. 전체 성과 비교

| 전략 | 역할 | CAGR(%) | 연환산 변동성(%) | MDD(%) | Sharpe | Calmar | WinRate(%) | 평균 Turnover(%) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fixed 70/20/10 BM | benchmark | 11.055 | 16.580 | -25.674 | 0.710 | 0.431 | 58.480 | 0.000 |
| EW Benchmark | benchmark | 6.590 | 7.994 | -13.571 | 0.834 | 0.486 | 60.819 | 0.000 |
| HSI baseline | baseline | 7.827 | 13.705 | -23.459 | 0.613 | 0.334 | 65.497 | 22.018 |
| Lambda 0.1 | candidate | 8.692 | 11.352 | -14.744 | 0.787 | 0.590 | 59.649 | 2.455 |
| Lambda 0.3 | candidate | 9.148 | 12.102 | -15.220 | 0.779 | 0.601 | 60.819 | 6.886 |

전체 성과를 보면 Fixed 70/20/10 BM은 CAGR 11.05%로 가장 높다. 그러나 MDD도 -25.67%로 가장 크다. HSI baseline은 상태분류를 ETF 비중으로 연결하는 기준선 역할을 했지만 평균 Turnover가 22.02%로 높고, MDD도 -23.46%로 부담이 컸다.

Lambda 0.1은 CAGR 8.69%, MDD -14.74%, 평균 Turnover 2.46%를 보였다. Lambda 0.3은 CAGR 9.15%, MDD -15.22%, 평균 Turnover 6.89%를 보였다.

따라서 Lambda 후보의 핵심 개선은 수익률 1등이 아니라, **HSI baseline의 즉시 비중 이동 문제를 완화하고 Fixed BM 대비 낙폭을 줄인 것**이다.

![Fixed BM 포함 최종 후보 누적수익률](../output/figures/main_final_candidate_cumulative_return_selected_with_fixed_bm.png)

![Fixed BM 포함 최종 후보 Drawdown](../output/figures/main_final_candidate_drawdown_selected_with_fixed_bm.png)

---

## 7. 거래비용 민감도

| 전략 | 0bp CAGR(%) | 5bp CAGR(%) | 10bp CAGR(%) | 20bp CAGR(%) |
| --- | --- | --- | --- | --- |
| Fixed 70/20/10 BM | 10.918 | 10.918 | 10.918 | 10.918 |
| EW (Benchmark) | 6.510 | 6.510 | 6.510 | 6.510 |
| Lambda 0.1 | 8.655 | 8.639 | 8.623 | 8.590 |
| Lambda 0.3 | 9.085 | 9.040 | 8.995 | 8.905 |

거래비용 민감도에서는 Lambda 0.1이 Lambda 0.3보다 비용 drag가 작다. Lambda 0.3은 더 높은 CAGR과 Calmar를 보이지만 Turnover가 더 높아 비용 증가에 더 민감하다. 따라서 두 후보는 하나의 우열 순위로 정리하기보다 다음처럼 역할을 나누는 것이 적절하다.

| 후보 | 해석 |
|---|---|
| Lambda 0.1 | 낮은 Turnover와 비용 민감도가 장점인 저회전·보수형 후보 |
| Lambda 0.3 | 더 높은 CAGR과 Calmar를 추구하는 수익성·균형형 후보 |

![Fixed BM 포함 비용 민감도](../output/figures/main_final_candidate_cost_sensitivity_with_fixed_bm.png)

---

## 8. 손실월 방어 진단

069500 하위 10% 손실월에서 각 전략의 평균 수익률은 다음과 같다.

| 전략 | 손실월 수 | 069500 하위 10%월 평균수익률(%) | 최악 월 수익률(%) | 평균 069500 비중(%) |
| --- | --- | --- | --- | --- |
| Fixed 70/20/10 BM | 18.000 | -5.861 | -14.130 | 70.000 |
| EW Benchmark | 18.000 | -2.754 | -6.985 | 33.333 |
| HSI baseline | 18.000 | -4.075 | -14.130 | 44.444 |
| Lambda 0.1 | 18.000 | -3.685 | -10.911 | 45.157 |
| Lambda 0.3 | 18.000 | -3.833 | -12.553 | 45.413 |

Fixed 70/20/10 BM은 주식형 ETF 70%를 고정 보유하기 때문에 069500 큰 손실월에서 손실폭이 크다. EW Benchmark는 069500 비중이 약 33.3%라 손실월에서 안정적으로 보일 수 있다. Lambda 후보는 Fixed BM 대비 손실월 방어를 개선하지만, EW보다 항상 더 방어적이라고 단정하지 않는다.

이 해석은 최종 발표에서 중요하다. 전략의 장점은 “모든 지표에서 압도”가 아니라, **Fixed BM의 낙폭 부담과 EW의 성장성 한계 사이에서 방어형 균형을 찾은 것**이다.

![Fixed BM 포함 tail event](../output/figures/main_final_regime_robustness_tail_event_with_fixed_bm.png)

---

## 9. 보조 실험의 역할

### 9.1 Signal combo와 Event balance

06~09번 실험에서는 확장 신호, 상대속도, 신호 조합, 사건균형 필터를 검토하였다.

| 번호 | 실험명 | 역할 | 최종 사용 | 판단 |
| --- | --- | --- | --- | --- |
| 6.000 | extended signal inputs | 신호 후보 확장 | 보조 진단 | 최종 후보를 직접 만들기보다 07번 조합 실험의 입력으로 사용 |
| 6.000 | relative speed diagnostics | HSI 내부 반응속도 진단 | 보조 진단 | 선행/후행 예측값이 아니라 신호별 반응속도 비교용 |
| 7.000 | signal combo backtests | 신호 조합 민감도 확인 | 보조 진단 | 일부 조합 성과는 개선되지만 Turnover와 위험지표 기준으로 최종 후보는 아님 |
| 8.000 | event balance state diagnostic | 사건균형지표와 HSI 상태 정합성 확인 | 해석 보조 | HSI 상태를 대체하지 않고 상태 해석 보조로 제한 |
| 9.000 | event balance filter backtest | ±5~10%p 보조 비중 조정 실험 | 보조 필터 | 최종 후보를 바꿀 정도의 개선은 확인되지 않음 |

이 실험들의 결론은 최종 후보를 바꾼 것이 아니라, HSI 구조의 해석 안정성을 점검했다는 점이다. 일부 신호 조합은 성과 개선 가능성을 보였지만 Turnover와 위험조정지표 기준에서 최종 후보로 남지 않았다. Event balance도 HSI 상태 해석 보조에는 유용했지만, HSI를 대체하는 신호로 쓰기에는 제한적이었다.

### 9.2 Theta

Theta 실험은 HSI 상태분류의 민감도를 확인하기 위한 실험이다. Theta 값에 따라 상태분포와 성과가 일부 달라지지만, Turnover를 직접 줄이는 장치는 아니다. 따라서 최종 개선 장치로는 Lambda가 더 직접적이었다.

### 9.3 Macro companion

Macro companion은 HSI와 일부 겹치지만 완전히 같은 신호는 아니었다. Macro 데이터가 사용 가능한 월은 150개월로 전체의 87.21%였고, HSI 위험월 48개월 중 macro risk가 함께 확인된 비율은 54.17%였다.

따라서 macro companion은 최종 전략 신호가 아니라, HSI가 포착하지 않는 외생 거시 압력을 설명하는 보조 진단 layer로 두는 것이 적절하다.

![HSI Macro Risk Timeline](../output/figures/main_final_hsi_macro_risk_timeline.png)

---

## 10. 최종 후보 판단

최종 후보 판단은 다음과 같다.

| 전략 | 최종 역할 | 판단 |
|---|---|---|
| Fixed 70/20/10 BM | 메인 BM | CAGR은 높지만 MDD가 큼 |
| EW Benchmark | 보조 BM | 안정적이나 성장성이 제한적 |
| HSI baseline | 내부 기준선 | 상태와 비중 연결은 가능하지만 Turnover와 MDD 부담 |
| Lambda 0.1 | 최종 후보 | 저회전·보수형 |
| Lambda 0.3 | 최종 후보 | 수익성·Calmar 균형형 |
| Signal combo | 보조 진단 | 신호 조합 민감도 확인 |
| Event balance | 보조 진단 | HSI 상태 해석 보조 |
| Theta | 보조 진단 | 상태분류 민감도 확인 |
| Macro companion | 보조 진단 | 거시 압력 보조 설명 |

최종 후보를 하나만 고르기보다, 투자 성향별로 두 후보를 제시하는 것이 가장 안전하다.

- 보수형 관점: Lambda 0.1  
- 수익성과 반응성을 조금 더 원하는 관점: Lambda 0.3  

---

## 11. 한계

본 실험은 과거 데이터 기반 백테스트이며 실제 운용 성과를 보장하지 않는다. 또한 거래비용은 단순화된 가정으로 반영했으며, 실제 ETF 체결비용, 세금, 슬리피지, 시장충격비용까지 완전히 포함하지 않는다. Macro companion도 데이터 가용성과 공시 지연 문제가 있어 최종 active signal이 아니라 보조 진단으로만 사용하였다.

또한 Fixed BM과 Lambda 후보의 성격이 다르므로, CAGR만으로 전략 우열을 단정하면 안 된다. 본 전략의 목적은 상승장 수익률 극대화가 아니라 방어형 ETF RA 구조를 만드는 것이다.

---

## 12. 최종 결론

본 프로젝트는 HSI를 미래수익률 예측기가 아니라 가격 기반 시장상태 번역기로 사용하고, 이를 ETF 비중 조절에 연결하였다. HSI baseline은 상태분류와 비중조절의 연결 가능성을 보여주었지만, 목표비중으로 즉시 이동하는 구조 때문에 Turnover와 MDD 부담이 컸다.

후속 실험 중 가장 중요한 개선은 Lambda 부분조정이었다. Lambda 0.1과 Lambda 0.3은 HSI 상태분류는 유지하되 목표비중으로 이동하는 속도를 완화하여, Fixed 70/20/10 BM 대비 낙폭을 줄이고 EW Benchmark 대비 성장성과 Calmar를 개선하는 방어형 후보로 남았다.

최종 보고서 문장은 다음과 같이 정리한다.

> Fixed 70/20/10 BM은 CAGR이 가장 높지만 MDD가 크고, EW Benchmark는 안정성이 높다. Lambda 0.1과 Lambda 0.3은 두 BM을 모든 지표에서 압도하는 전략이 아니라, Fixed BM 대비 낙폭을 줄이고 EW 대비 성장성과 Calmar를 개선하는 방어형 ETF RA 후보로 해석한다.

---

# 부록 1. 최종 보고서에 우선 사용할 개별 보고서

| 순서 | 보고서 파일 | 역할 |
| --- | --- | --- |
| 1 | 00_05_Project_foundation_and_HSI_baseline.md | 00~05 초반 데이터·HSI baseline 구조 |
| 2 | 06_09_Signal_combo_and_event_balance_diagnostic.md | 06~09 신호조합·event balance 보조진단 |
| 3 | 10_Inertia_lambda_experiment.md | 10 Lambda 부분조정 실험 |
| 4 | 11_Theta_sensitivity_experiment.md | 11 Theta 민감도 실험 |
| 5 | 12_13_Macro_companion_diagnostic.md | 12~13 Macro companion 진단 |
| 6 | 14_Macro_companion_overlay.md | 14 Macro soft overlay 실험 |
| 7 | 15_Lambda_macro_overlay_sensitivity.md | 15 Lambda+macro 민감도 |
| 8 | 16_Regime_robustness_with_fixed_bm.md | 16 Robustness 보완판, Fixed BM 포함 |
| 9 | 17_Benchmark_alignment.md | 17 Benchmark alignment |
| 10 | 20_23_Final_candidate_selection_with_fixed_bm.md | 20~23 최종 후보 선정, Fixed BM 포함 |

---

# 부록 2. 최종 저장 위치 요약

| 산출물 종류 | 저장 위치 |
|---|---|
| 보고서 `.md` | `docs/` |
| 요약표 `.csv` | `output/tables/` |
| 그림 `.png` | `output/figures/` |
| 가공 시계열 `.csv` | `data/processed/` |

특히 다음 두 파일은 기존 보완 전 파일보다 우선 사용한다.

```text
16_Regime_robustness_with_fixed_bm.md
20_23_Final_candidate_selection_with_fixed_bm.md
```

---

# 새로 생성된 산출물 저장 위치 정리

## docs/ 로 옮길 보고서 md 파일

```text
main_final_hsi_overlay_result_report_with_fixed_bm_final.md
```

## output/tables/ 로 옮길 csv 표 파일

```text
없음
```

## output/figures/ 로 옮길 png 그림 파일

```text
없음
```

## data/processed/ 로 옮길 파일

```text
없음
```

이번 작업은 최종 통합 보고서를 최신 BM 기준으로 갱신하는 작업이므로, 새 그림이나 새 가공 시계열은 만들지 않았다.
