# main_final 사건균형 보조 필터 백테스트 노트

- 생성 시각: 2026-07-01 00:32:53

## 1. 목적

이 단계는 사건균형지표를 HSI 상태를 대체하는 신호가 아니라, 상태별 목표 비중을 ±5~10%p 범위에서 보정하는 보조 필터로 제한해 실험한다.

## 2. 보조 필터 원칙

- 위험 누적이 강하면 069500에서 153130으로 일부 이동한다.
- 완화 누적이 강하면 153130에서 069500으로 일부 이동한다.
- 사건균형지표는 기본 HSI 상태를 뒤집지 않는다.

## 3. 성과 요약

| strategy | CAGR_pct | MDD_pct | Sharpe | Calmar |
|---|---:|---:|---:|---:|
| EW | 6.5101 | -13.5711 | 0.8318 | 0.4797 |
| HSI_event_balance_filter_overlay | 7.1372 | -23.0356 | 0.6000 | 0.3098 |
| HSI_final_baseline_overlay | 7.7323 | -23.4594 | 0.6111 | 0.3296 |

## 4. 판단

- HSI_event_balance_filter_overlay vs HSI_final_baseline_overlay: candidate — baseline 대비 MDD가 개선되고 평균 Turnover가 증가하지 않음
