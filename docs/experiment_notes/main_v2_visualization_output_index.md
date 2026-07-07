# main_v2 HSI 5상태 Overlay 시각화 산출물 인덱스

- 생성 시각: 2026-06-29 06:25:06
- 준비 완료: 6 / 6

## 1. 보고서 삽입 권장 순서

| 순서 | Figure | 이름 | 답하는 질문 | 준비 상태 |
|---:|---|---|---|---|
| 1 | Fig.1 | HSI 5상태 분포 | rank와 zscore 방식은 HSI 5상태를 어떻게 다르게 분류하는가? | OK |
| 2 | Fig.2 | 누적수익률 비교 | EW, main_v2, main_v2b의 누적성과 흐름은 어떻게 다른가? | OK |
| 3 | Fig.3 | Drawdown 비교 | HSI overlay는 낙폭을 줄였는가? | OK |
| 4 | Fig.4 | HSI 상태별 포트폴리오 비중 변화 | HSI 상태가 실제 ETF 비중 조정으로 연결되었는가? | OK |
| 5 | Fig.5 | Turnover 비교 | conflict를 관찰로 처리하면 Turnover가 줄어드는가? | OK |
| 6 | Fig.6 | main_v2 vs main_v2b 규칙 비교 요약 | conflict 방어 처리와 conflict 관찰 처리 중 어느 쪽이 더 안정적인가? | OK |

## 2. 해석 흐름

1. Fig.1에서 HSI 5상태가 rank와 zscore에서 어떻게 분포하는지 확인한다.
2. Fig.2에서 EW, main_v2, main_v2b의 장기 누적성과 흐름을 비교한다.
3. Fig.3에서 Drawdown과 MDD를 비교해 방어 효과를 확인한다.
4. Fig.4에서 HSI 상태가 실제 ETF 비중 변화로 연결되었는지 확인한다.
5. Fig.5에서 conflict 처리 방식이 Turnover에 미친 영향을 확인한다.
6. Fig.6에서 main_v2와 main_v2b 규칙 차이를 종합 요약한다.

## 3. 산출물 상태

- 모든 본문용 시각화 산출물이 준비되어 있다.

## 4. 보고서 연결 문장

본 시각화 묶음은 HSI 5상태 체계가 단순한 상태 라벨에 그치지 않고, 포트폴리오 비중 조정과 성과 차이로 이어지는지를 확인하기 위해 구성하였다. 특히 conflict 상태를 방어 신호로 처리한 main_v2와 관찰 신호로 처리한 main_v2b를 비교함으로써, HSI 상태명과 실제 포트폴리오 행동을 분리해 설계할 필요가 있음을 확인하였다.
