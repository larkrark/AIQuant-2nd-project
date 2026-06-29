# Fig.3 Drawdown 비교 해석 노트

## 그림의 질문

HSI 5상태 overlay는 단순 동일비중 대비 낙폭을 줄였는가?

## MDD 요약

| method | 전략 | MDD | MDD(%) |
|---|---|---:|---:|
| rank | EW | -0.135711 | -13.57% |
| rank | main_v2: conflict 방어 | -0.137657 | -13.77% |
| rank | main_v2b: conflict 관찰 | -0.135120 | -13.51% |
| zscore | EW | -0.135711 | -13.57% |
| zscore | main_v2: conflict 방어 | -0.139193 | -13.92% |
| zscore | main_v2b: conflict 관찰 | -0.138555 | -13.86% |

## 해석

Drawdown은 누적수익률이 이전 고점 대비 얼마나 하락했는지를 보여주는 지표이다.
방어형 overlay 전략에서는 최종 누적수익률뿐 아니라 Drawdown과 MDD를 함께 확인해야 한다.
main_v2와 main_v2b의 차이는 conflict 상태를 방어로 처리할지, 관찰로 처리할지에 있다.
main_v2b의 MDD가 main_v2보다 개선된다면, conflict를 즉시 방어전환으로 처리하기보다 관찰 상태로 두는 것이 낙폭 관리 측면에서도 더 자연스러울 수 있다.
