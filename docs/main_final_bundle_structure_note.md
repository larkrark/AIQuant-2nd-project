# main_final 번들 구조 정리 노트

- 생성 시각: 2026-06-30 18:43:38
- 기준 번들: `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\tables\hsi_data_bundle.xlsx`

## 1. 목적

이 단계는 데이터 담당 최종 산출물인 `hsi_data_bundle.xlsx`를 후속 실험에서 읽기 쉬운 CSV 기준 입력으로 분리하는 단계이다. 이 파일은 데이터를 다시 다운로드하거나 다시 계산하지 않는다.

## 2. 수익률 단위

- `monthly_return_pct`: 사람이 검토하기 쉬운 percent 단위
- `monthly_return_decimal`: 백테스트 계산용 decimal 단위

예시:

```text
2.5% → monthly_return_pct = 2.5
2.5% → monthly_return_decimal = 0.025
```

## 3. 저장된 핵심 CSV

| item | rows | columns | status | output_path |
|---|---:|---:|---|---|
| asset_class | 3 | 15 | OK | `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\data\processed\main_final_asset_class.csv` |
| monthly_price | 172 | 4 | OK | `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\data\processed\main_final_monthly_price.csv` |
| monthly_return_decimal | 171 | 4 | OK | `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\data\processed\main_final_monthly_return_decimal.csv` |
| monthly_return_pct | 171 | 4 | OK | `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\data\processed\main_final_monthly_return_pct.csv` |
| signal_inputs | 10461 | 13 | OK | `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\data\processed\main_final_signal_inputs.csv` |
| hsi_scaled_scores | 3487 | 16 | OK | `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\data\processed\main_final_hsi_scaled_scores.csv` |
| hsi_direction | 3487 | 4 | OK | `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\data\processed\main_final_hsi_direction.csv` |
| hsi_signal | 3487 | 4 | OK | `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\data\processed\main_final_hsi_signal_raw3.csv` |
| signal_direction_map | 5 | 4 | OK | `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\data\processed\main_final_signal_direction_map.csv` |
| return_unit_check | 3 | 8 | OK | `C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\tables\main_final_bundle_return_unit_check.csv` |

## 4. 수익률 단위 점검 결과

| ticker | status | max_abs_decimal | max_abs_diff | note |
|---|---|---:|---:|---|
| 069500 | OK | 0.349432 | 0.0000000000 | pct/100과 decimal이 일치한다. |
| 114260 | OK | 0.019912 | 0.0000000000 | pct/100과 decimal이 일치한다. |
| 153130 | OK | 0.004901 | 0.0000000000 | pct/100과 decimal이 일치한다. |

## 5. 다음 단계

다음 단계인 `02_build_hsi_event_balance_indicator.py`에서는 `main_final_signal_inputs.csv` 또는 `main_final_hsi_scaled_scores.csv`를 이용해 20/80 분위수 기반 사건균형·위험누적지표를 생성한다.
