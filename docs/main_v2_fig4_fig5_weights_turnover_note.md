# Fig.4~Fig.5 비중 변화 및 Turnover 해석 노트

## 그림의 질문

1. HSI 상태가 실제 ETF 비중 조정으로 연결되었는가?
2. conflict를 관찰로 처리하면 Turnover가 줄어드는가?

## Turnover 비교

| method | main_v2 평균 Turnover | main_v2b 평균 Turnover | 차이 |
|---|---:|---:|---:|
| rank | 0.050195 | 0.037037 | -0.013158 |
| zscore | 0.046686 | 0.041326 | -0.005361 |

## 해석

비중 변화 그림은 HSI 상태가 단순한 설명 라벨에 머무르지 않고 실제 ETF 비중 조정으로 연결되었음을 보여준다.
Turnover 비교 결과는 conflict 상태를 방어전환이 아니라 관찰 상태로 처리했을 때 불필요한 비중 변화가 줄어드는지 확인하는 근거다.
main_v2b의 평균 Turnover가 main_v2보다 낮다면, conflict를 즉시 방어 신호로 사용하는 것보다 관찰 상태로 두는 규칙이 더 안정적인 포트폴리오 행동을 만들 수 있음을 시사한다.
