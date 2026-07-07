# HSI 후보 전략 시각화 해석 메모

## 비교 대상

- EW
- HSI Baseline
- Lambda 0.1
- Lambda 0.3
- Lambda 0.5
- Event Filter

그래프용 시계열은 `23_main_final_report_candidate_timeseries_subset_dedup.csv`를 기준으로 사용했다. 원본 subset 파일에서 `strategy_name`, `year_month` 기준 중복을 제거한 결과, 6개 전략은 각각 172개월 관측치를 가진다.

## 안전한 해석 문구

HSI Baseline은 최종 후보가 아니라 HSI 상태를 즉시 비중으로 연결했을 때의 기준선이다. Lambda 0.1과 Lambda 0.3은 Baseline 대비 MDD와 Turnover를 완화한 후보로 볼 수 있다.

다만 EW는 Sharpe가 가장 높으므로 Lambda 후보가 모든 지표에서 우수하다고 표현하는 것은 피하는 것이 안전하다. Lambda 0.1과 Lambda 0.3은 수익성, Calmar, Turnover, 비용 민감도 측면에서 검토 가치가 있는 후보로 표현하는 것이 적절하다.

## 그래프별 메시지

1. 누적수익률: Lambda 0.1과 Lambda 0.3은 Baseline 대비 누적 성과와 위험 완화 측면에서 검토할 만한 후보임을 보여준다.
2. Drawdown: Baseline은 MDD 부담이 크며, Lambda 0.1과 Lambda 0.3은 손실 구간의 깊이를 완화한다.
3. 성과 요약: EW는 Sharpe 측면에서 강점이 있고, Lambda 후보는 CAGR, Calmar, Turnover 균형 관점에서 비교한다.
4. Calmar-Turnover 산점도: Lambda 0.1은 낮은 Turnover, Lambda 0.3은 수익성과 Calmar 균형을 강조할 수 있다.
5. 비용 민감도: Turnover가 높은 Baseline과 Event Filter는 비용 가정 변화에 더 민감하며, Lambda 후보는 비용 차감 후 성과 방어력이 상대적으로 좋다.
6. 월별 Turnover: 부분조정 Lambda 구조가 즉시비중 방식 대비 거래 회전율을 낮추는 구조적 차이를 확인하는 보조 그래프다.
