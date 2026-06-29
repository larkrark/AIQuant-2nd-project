# Fig.1 HSI 5상태 분포 해석 노트

## 그림의 질문

rank와 zscore 방식은 HSI 5상태를 어떻게 다르게 분류하는가?

## 핵심 관찰

- rank 기준 conflict 비중은 약 28.5%이다.
- zscore 기준 conflict 비중은 약 16.3%이다.
- rank 기준 neutral_watch 비중은 약 28.5%이다.
- zscore 기준 neutral_watch 비중은 약 40.7%이다.

## 해석

rank 방식은 상대적 위치를 기준으로 판단하기 때문에 conflict 상태를 더 민감하게 포착하는 경향이 있다.
반면 zscore 방식은 평균과 표준편차 기준으로 극단성을 판단하므로 neutral_watch 상태에 더 오래 머무르는 경향이 있다.
이 차이는 이후 overlay 규칙에서 conflict를 방어 신호로 볼지, 관찰 신호로 볼지 판단하는 근거가 된다.

## 보고서 연결 문장

HSI 5상태 분포를 비교한 결과, rank 방식은 zscore 방식보다 conflict 상태를 더 자주 포착하였다. 이는 rank 기반 분류가 시장 내 상대적 위치 변화에 더 민감하게 반응한다는 점을 시사한다. 따라서 conflict 상태를 즉시 방어전환으로 사용할 경우 불필요한 비중 조정과 Turnover가 증가할 수 있으므로, 후속 실험에서는 conflict를 관찰 상태로 처리하는 완화형 overlay 규칙을 함께 비교하였다.
