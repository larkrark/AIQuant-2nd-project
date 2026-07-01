# Final Candidate Report Pack Note

이 문서는 20번 최종 후보 셀렉 결과를 보고서용 표와 시각화 자료로 정리하기 위한 메모이다.

## 1. 본문에 바로 넣기 좋은 표

1. `main_final_report_candidate_comparison_table.csv`
   - 최종 후보, 보류 후보, benchmark를 한 표에서 비교하는 핵심 표
2. `main_final_report_candidate_cost_pivot.csv`
   - 거래비용률 0.00%, 0.05%, 0.10%, 0.20%에서 후보별 CAGR 변화를 비교하는 표
3. `main_final_report_lambda_family_table.csv`
   - λ 실험 전체를 한 표로 비교하는 보조 표

## 2. 본문 그림 추천 배치

- Fig. 1 `main_final_report_cumulative_comparison.png`
  - EW, HSI baseline, 최종 후보들의 누적 성과 흐름 비교
- Fig. 2 `main_final_report_drawdown_comparison.png`
  - 후보별 최대낙폭과 회복 경로 비교
- Fig. 3 `main_final_report_turnover_comparison.png`
  - 평균/최대 Turnover 비교
- Fig. 4 `main_final_report_cost_drag_comparison.png`
  - 보수적 비용 가정(0.20%)에서 CAGR 훼손 정도 비교
- Fig. 5 `main_final_report_risk_return_scatter.png`
  - 절대 MDD와 CAGR의 위치 비교
- Fig. 6 `main_final_report_lambda_family_comparison.png`
  - λ별 CAGR과 평균 Turnover 비교

## 3. 해석 메모

현재 최종 후보로 분류된 전략은 다음과 같다.

- **Lambda 0.1**: CAGR 8.62%, MDD -14.79%, Sharpe 0.791, Calmar 0.583, 평균 Turnover 2.52%
- **Lambda 0.3**: CAGR 8.99%, MDD -15.33%, Sharpe 0.775, Calmar 0.587, 평균 Turnover 6.95%

## 4. 보고서 문장 예시

최종 후보 선별 결과, 대부분의 baseline·signal combo·theta 전략은 Turnover 기준을 통과하지 못하였다. 반면 λ 부분조정 실험에서 도출된 일부 후보는 Turnover, 거래비용 민감도, MDD, Sharpe, Calmar 기준을 함께 통과하였다. 이는 HSI 상태분류를 목표 비중에 즉시 반영하기보다, 비중 전환 속도를 조절하는 부분조정 구조와 결합할 때 방어형 overlay 전략의 안정성이 개선될 수 있음을 시사한다.

## 5. 생성 파일

- `C:/quant_lec/quant_model/day5/day5_hsi_dynamic_allocation_project/AIQuant-2nd-project/output/tables/main_final_report_candidate_comparison_table.csv`
- `C:/quant_lec/quant_model/day5/day5_hsi_dynamic_allocation_project/AIQuant-2nd-project/output/tables/main_final_report_candidate_shortlist.csv`
- `C:/quant_lec/quant_model/day5/day5_hsi_dynamic_allocation_project/AIQuant-2nd-project/output/tables/main_final_report_candidate_cost_pivot.csv`
- `C:/quant_lec/quant_model/day5/day5_hsi_dynamic_allocation_project/AIQuant-2nd-project/output/tables/main_final_report_lambda_family_table.csv`
- `C:/quant_lec/quant_model/day5/day5_hsi_dynamic_allocation_project/AIQuant-2nd-project/output/tables/main_final_report_candidate_timeseries_subset.csv`
- `C:/quant_lec/quant_model/day5/day5_hsi_dynamic_allocation_project/AIQuant-2nd-project/output/figures/main_final_report_cumulative_comparison.png`
- `C:/quant_lec/quant_model/day5/day5_hsi_dynamic_allocation_project/AIQuant-2nd-project/output/figures/main_final_report_drawdown_comparison.png`
- `C:/quant_lec/quant_model/day5/day5_hsi_dynamic_allocation_project/AIQuant-2nd-project/output/figures/main_final_report_turnover_comparison.png`
- `C:/quant_lec/quant_model/day5/day5_hsi_dynamic_allocation_project/AIQuant-2nd-project/output/figures/main_final_report_cost_drag_comparison.png`
- `C:/quant_lec/quant_model/day5/day5_hsi_dynamic_allocation_project/AIQuant-2nd-project/output/figures/main_final_report_risk_return_scatter.png`
- `C:/quant_lec/quant_model/day5/day5_hsi_dynamic_allocation_project/AIQuant-2nd-project/output/figures/main_final_report_lambda_family_comparison.png`
