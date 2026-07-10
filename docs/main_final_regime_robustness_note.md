# 16번 Regime Robustness Check Note

## 1. 실험 목적

16번은 새 후보를 만드는 실험이 아니라, 10·11·20·21·23번 모델 셀렉션에서 남은 Lambda 0.1과 Lambda 0.3 후보를 흔들어 보는 검증 실험이다.

```text
질문: Lambda 후보가 전체 기간에서만 좋아 보인 것인가?
아니면 기간별·HSI 상태별·큰 손실월에서도 나름의 역할을 유지하는가?
```

## 2. 비교 대상

```text
EW Benchmark
HSI baseline
Lambda 0.1
Lambda 0.3
```

## 3. 전체 기간 요약

| strategy_name | CAGR_pct | MDD_pct | Sharpe | Calmar | avg_turnover_pct |
| --- | --- | --- | --- | --- | --- |
| EW Benchmark | 6.5896 | -13.5711 | 0.8343 | 0.4856 | 0.0000 |
| HSI baseline | 7.8274 | -23.4594 | 0.6129 | 0.3337 | 22.0175 |
| Lambda 0.1 | 8.6924 | -14.7442 | 0.7865 | 0.5895 | 2.4554 |
| Lambda 0.3 | 9.1475 | -15.2197 | 0.7793 | 0.6010 | 6.8856 |

전체 기간 Calmar 기준 Lambda 후보 중 우위는 **Lambda 0.3**이다.  
전체 기간 평균 Turnover 기준으로 더 보수적인 후보는 **Lambda 0.1**이다.

## 4. 해석 원칙

상태별 분석은 실제 연속 운용 경로가 아니라, 해당 HSI 상태가 관측된 월만 모아 본 조건부 진단표이다. 따라서 상태별 표에서는 CAGR보다 평균 월수익률, 최악 월수익률, 승률, 평균 Turnover를 중심으로 해석한다.

## 5. 보고서 문장 초안

후속 robustness 검토에서는 최종 후보인 Lambda 0.1과 Lambda 0.3을 기간별·HSI 상태별·큰 손실월 기준으로 나누어 확인하였다. 이는 특정 전체기간 성과에만 의존하지 않고, HSI 상태 변화가 ETF 비중 행동으로 연결될 때 후보가 어느 구간에서 강하고 약한지 확인하기 위한 절차이다. 분석 결과가 모든 구간에서 일관되게 한 후보의 우월성을 보장하지 않더라도, Lambda 부분조정이 HSI baseline의 급격한 비중 전환과 Turnover 부담을 완화하는 구조적 역할을 하는지 확인하는 데 의미가 있다.

## 6. 산출물

```text
output/tables/main_final_regime_robustness_summary.csv
output/tables/main_final_regime_robustness_by_period.csv
output/tables/main_final_regime_robustness_by_hsi_state.csv
output/tables/main_final_regime_robustness_tail_event_summary.csv
output/tables/main_final_regime_robustness_tail_months.csv
output/tables/main_final_regime_robustness_decision_note.csv
```
