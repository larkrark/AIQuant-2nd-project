# 16번 Benchmark Alignment Check Note

## 1. 실험 목적

17번은 강사님 RA 개발 기준에 맞춰 메인 BM인 Fixed 70/20/10 BM을 비교표에 추가하고, EW Benchmark·HSI baseline·Lambda 후보와 같은 기준으로 정렬하는 검증 실험이다.

```text
질문: Fixed 70/20/10 BM과 EW Benchmark를 함께 놓았을 때, Lambda 후보의 개선이 ETF 선택 효과인지 동적 비중조절 효과인지 구분되는가?
```

## 2. 비교 대상

```text
Fixed 70/20/10 BM
EW Benchmark
HSI baseline
Lambda 0.1
Lambda 0.3
```

## 3. 전체 기간 요약

| strategy_name | CAGR_pct | MDD_pct | Sharpe | Calmar | avg_turnover_pct |
| --- | --- | --- | --- | --- | --- |
| Fixed 70/20/10 BM | 11.0545 | -25.6742 | 0.7096 | 0.4306 | 0.0000 |
| EW Benchmark | 6.5896 | -13.5711 | 0.8343 | 0.4856 | 0.0000 |
| HSI baseline | 7.8274 | -23.4594 | 0.6129 | 0.3337 | 22.0175 |
| Lambda 0.1 | 8.6924 | -14.7442 | 0.7865 | 0.5895 | 2.4554 |
| Lambda 0.3 | 9.1475 | -15.2197 | 0.7793 | 0.6010 | 6.8856 |

전체 기간 Calmar 기준 Lambda 후보 중 우위는 **Lambda 0.3**이다.  
전체 기간 평균 Turnover 기준으로 더 보수적인 후보는 **Lambda 0.1**이다.

## 4. 해석 원칙

상태별 분석은 실제 연속 운용 경로가 아니라, 해당 HSI 상태가 관측된 월만 모아 본 조건부 진단표이다. 따라서 상태별 표에서는 CAGR보다 평균 월수익률, 최악 월수익률, 승률, 평균 Turnover를 중심으로 해석한다.

## 5. 보고서 문장 초안

BM 정렬 검토에서는 메인 BM인 Fixed 70/20/10 BM, 보조 BM인 EW Benchmark, 내부 기준선인 HSI baseline, 최종 후보인 Lambda 0.1과 Lambda 0.3을 같은 표에서 비교하였다. 이는 전략 성과가 ETF 유니버스 선택 자체에서 나온 것인지, HSI와 Lambda를 이용한 동적 비중조절에서 나온 것인지 구분하기 위한 절차이다. 분석 결과가 모든 지표에서 한 후보의 절대적 우월성을 보장하지 않더라도, Lambda 부분조정이 HSI baseline의 급격한 비중 전환과 Turnover 부담을 완화하는 구조적 역할을 하는지 확인하는 데 의미가 있다.

## 6. 산출물

```text
output/tables/main_final_benchmark_alignment_summary.csv
output/tables/main_final_benchmark_alignment_by_period.csv
output/tables/main_final_benchmark_alignment_by_hsi_state.csv
output/tables/main_final_benchmark_alignment_tail_event_summary.csv
output/tables/main_final_benchmark_alignment_tail_months.csv
output/tables/main_final_benchmark_alignment_decision_note.csv
```
