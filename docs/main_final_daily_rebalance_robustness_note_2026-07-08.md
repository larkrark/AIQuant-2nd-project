# 일일 ETF 수익 상세표 및 Robustness 4가지 검증 정리 (2026-07-08)

## 1. 산출 목적

강사님 피드백 중 "RA가 생성한 포트폴리오 구성내역의 추이와 그 성과 결과, 그 성과 결과를 만든 원인과 개선 방법"을 더 촘촘하게 설명하기 위한 보완 산출물이다. 이 문서는 기존 최종보고서의 핵심 결론을 바꾸기보다, 다음 두 가지를 추가로 뒷받침한다.

- 월별 리밸런싱 및 turnover가 실제 ETF 일별 수익률 구간과 어떻게 연결되는지 확인한다.
- robustness를 네 가지 축으로 분해해 dynamic_v1 결론이 특정 표 하나에만 의존하지 않음을 설명한다.

## 2. 일일 리밸런싱 및 ETF 수익 상세 표

새로 만든 표는 다음 두 개다.

| 파일 | 역할 |
|---|---|
| `output/tables/main_final_daily_rebalance_etf_return_detail.csv` | 전략-월-일자 단위의 일별 ETF 가격, 일별 수익률, 월중 누적수익률, 해당 월 turnover 연결 표 |
| `output/tables/main_final_monthly_rebalance_etf_return_summary.csv` | 전략-월 단위의 ETF 월수익률, 일별 변동성, 최악/최고 일수익률, 해당 월 turnover 요약 표 |

해석상 주의할 점은 이 전략이 매일 목표비중을 바꾸는 전략이 아니라는 점이다. 리밸런싱 판단은 월말 HSI 상태와 lambda 규칙을 기준으로 하며, 위 daily table은 그 월의 ETF 일별 수익 경로를 촘촘하게 붙여 "그 리밸런싱 월에 어떤 ETF 수익 환경이 있었는지"를 설명하기 위한 보조 표다.

## 3. Robustness 4가지 검증 축

| # | 검증 축 | 사용 표 | 확인 질문 |
|---|---|---|---|
| 1 | IS/OOS 분리 | `main_final_is_oos_performance_table.csv` | OOS에서도 성과와 낙폭 통제가 유지되는가? |
| 2 | Walk-forward | `main_final_walk_forward_results.csv` | 60개월 관찰 후 12개월 평가를 굴려도 결과가 유지되는가? |
| 3 | Rolling 3년 window | `main_final_rolling_3y_decision_summary.csv` | 특정 기간 하나에만 성과가 의존하지 않는가? |
| 4 | 비용·Turnover 민감도 | `main_final_turnover_cost_by_cost_bp.csv`, `main_final_annual_buy_sell_turnover_summary.csv` | 비용을 차감하고 회전율을 봐도 결론이 유지되는가? |

정리표는 다음 파일에 저장했다.

- `output/tables/main_final_robustness_4check_overview.csv`
- `output/tables/main_final_robustness_4check_by_strategy.csv`

## 4. 핵심 후보 dynamic_v1 요약

| 항목 | 값 | 해석 |
|---|---:|---|
| OOS Calmar | 1.476 | OOS에서도 위험조정 성과가 유지됨 |
| OOS MDD | -12.63% | -20% 기준 이내 |
| Walk-forward Calmar | 0.765 | 이동 평가창에서도 양호 |
| Rolling 3Y 음수 window 비율 | 3.68% | 10% 기준 이내 |
| Rolling 3Y worst MDD | -12.63% | FixedBM 대비 낙폭 방어 우위 |
| 10bp 비용차감 Calmar | 0.766 | 비용차감 후에도 기준 유지 |
| 평균 연환산 one-way Turnover | 56.59% | 100% 기준 이내 |
| 최대 연간 one-way Turnover | 90.34% | 200% 기준 이내 |

따라서 dynamic_v1은 초과수익률 알파를 주장하기 위한 후보라기보다, OOS, walk-forward, rolling window, 비용/turnover 네 축에서 낙폭 통제와 위험조정 성과가 유지되는 방어형 Overlay 후보로 정리하는 것이 적절하다.

## 5. dynamic_v1_macro와 lambda_0.3 비교 포인트

| 전략 | OOS Calmar | Rolling 3Y 음수 window 비율 | 10bp Calmar | 평균 연환산 Turnover | 해석 |
|---|---:|---:|---:|---:|---|
| dynamic_v1 | 1.476 | 3.68% | 0.766 | 56.59% | 기본 시변 lambda 후보 |
| dynamic_v1_macro | 1.429 | 3.68% | 0.748 | 50.75% | 저회전·보수 확장안 |
| lambda_0.3 | 1.087 | 6.62% | 0.587 | 78.50% | 성과는 양호하나 일부 연도 turnover 주의 |

## 6. 보고서 문장 제안

> 본 전략은 일별 매매 전략이 아니라 월말 HSI 상태와 lambda 실행속도에 따라 다음 월 목표비중으로 이동하는 방어형 Overlay 전략이다. 보완 표에서는 각 리밸런싱 월에 대해 069500, 114260, 153130의 일별 수익률 경로와 월별 매수·매도 turnover를 연결해, 포트폴리오 성과가 어떤 ETF 수익 환경에서 발생했는지 확인하였다. Robustness는 IS/OOS, walk-forward, rolling 3년 window, 비용·turnover 민감도 네 축으로 점검하였다. dynamic_v1은 네 검증 축을 모두 통과했으며, FixedBM 대비 초과수익률 알파를 주장하기보다는 낙폭 통제와 위험조정 성과 개선이 반복적으로 확인된 방어형 후보로 해석한다.
