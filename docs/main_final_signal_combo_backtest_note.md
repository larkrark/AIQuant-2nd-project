# main_final 신호 조합 백테스트 노트

- 생성 시각: 2026-06-30 18:43:59

## 1. 목적

이 단계는 HSI 상태분류에 사용하는 신호 조합을 바꾸었을 때 성과, MDD, Turnover, 상태분포가 어떻게 달라지는지 비교한다.

## 2. 주의

상대속도는 미래 수익률을 예측하기 위한 선행지표가 아니라, HSI 내부 신호가 전체 중심 흐름보다 위험 악화 또는 완화 방향으로 빠르게 움직이는지 보는 진단 신호이다.

## 3. 성과 요약

| strategy | CAGR_pct | MDD_pct | Sharpe | Calmar |
|---|---:|---:|---:|---:|
| EW | 6.5101 | -13.5711 | 0.8318 | 0.4797 |
| combo_00_core5 | 7.7323 | -23.4594 | 0.6111 | 0.3296 |
| combo_01_core4_no_rs | 7.7323 | -23.4594 | 0.6111 | 0.3296 |
| combo_02_trend_only | 8.5451 | -20.9010 | 0.6680 | 0.4088 |
| combo_03_risk_damage_focus | 6.5215 | -26.7243 | 0.5285 | 0.2440 |
| combo_04_core5_plus_relative_speed | 7.6987 | -19.8645 | 0.6179 | 0.3876 |

## 4. 후보 판단

| strategy | decision | reason |
|---|---|---|
| EW | benchmark | 동일가중 비교 기준 |
| combo_00_core5 | revise_or_exclude | Turnover 기준 또는 위험관리 기준 재검토 필요 |
| combo_01_core4_no_rs | revise_or_exclude | Turnover 기준 또는 위험관리 기준 재검토 필요 |
| combo_02_trend_only | revise_or_exclude | Turnover 기준 또는 위험관리 기준 재검토 필요 |
| combo_03_risk_damage_focus | revise_or_exclude | Turnover 기준 또는 위험관리 기준 재검토 필요 |
| combo_04_core5_plus_relative_speed | revise_or_exclude | Turnover 기준 또는 위험관리 기준 재검토 필요 |
