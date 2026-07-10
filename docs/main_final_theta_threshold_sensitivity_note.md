# HSI 5상태 분류 임계값(θ 등) 민감도 분석 노트

04_build_hsi_state5_baseline.py의 THETA_COMMON=0.15 등 4개 임계값은 데이터로부터 산출한 계산식이 아니라 사전에 정한 관행값이다. 본 분석은 HSI baseline(λ=1, 즉시 반영) 성과가 이 값 근처에서 급격히 무너지지 않는지 확인한다.

## 파라미터별 안정 구간 요약

| 파라미터 | baseline | 탐색범위 | 안정범위 | 안정 비율 | 전 구간 안정 |
|---|---:|---|---|---|---|
| THETA_COMMON | 0.15 | [0.1, 0.2] | [nan, nan] | 0/5 | False |
| ACCIDENT_EXTRA | 0.2 | [0.1, 0.3] | [nan, nan] | 0/5 | False |
| DIRECTION_MARGIN | 0.05 | [0.0, 0.1] | [nan, nan] | 0/5 | False |
| CONFLICT_DIRECTION_BAND | 0.2 | [0.1, 0.3] | [nan, nan] | 0/5 | False |

(안정 판정 기준: baseline 대비 CAGR ±1.5%p, MDD ±2.0%p, Calmar ±0.15 이내, HSI baseline λ=1 기준)

## 해석 (초안)

[TODO] 전 구간 안정(full_grid_stable=True)인 파라미터는 θ 등 임계값을 정확히 튜닝하지 않았어도 상태분류 결과가 취약하지 않다는 근거로 제시할 수 있다.
