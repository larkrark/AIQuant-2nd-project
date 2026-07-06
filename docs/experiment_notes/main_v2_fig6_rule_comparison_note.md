# Fig.6 규칙 비교 요약 해석 노트

## 그림의 질문

conflict를 방어로 처리한 main_v2와 conflict를 관찰로 처리한 main_v2b 중 어느 규칙이 더 안정적인가?

## 핵심 비교

| method | experiment | 총수익률 | CAGR | MDD | Sharpe | 평균 Turnover |
|---|---|---:|---:|---:|---:|---:|
| rank | EW | 146.18% | 6.53% | -13.57% | 0.8317 | 0.0000 |
| rank | main_v2_conflict_defense | 105.84% | 5.20% | -13.77% | 0.8140 | 0.0502 |
| rank | main_v2b_conflict_watch | 122.65% | 5.78% | -13.51% | 0.8005 | 0.0370 |
| zscore | EW | 146.18% | 6.53% | -13.57% | 0.8317 | 0.0000 |
| zscore | main_v2_conflict_defense | 101.82% | 5.05% | -13.92% | 0.8071 | 0.0467 |
| zscore | main_v2b_conflict_watch | 116.94% | 5.59% | -13.86% | 0.7968 | 0.0413 |

## 해석

main_v2는 conflict 상태를 소폭 방어로 처리한 규칙이고, main_v2b는 conflict 상태를 관찰 상태로 처리한 규칙이다.
이 비교는 HSI 상태명과 실제 포트폴리오 행동을 분리해서 설계해야 함을 보여준다.
conflict는 위험 악화가 확정된 상태라기보다 위험 완화 신호와 위험 악화 신호가 동시에 나타나는 혼조 상태이므로, 즉시 방어전환하기보다 관찰 상태로 처리하는 규칙이 불필요한 Turnover를 줄일 수 있다.
