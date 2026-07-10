# Main Final Generated Artifact Manifest and Save Plan

## 목적

이 문서는 지금까지 생성한 보고서, 표, 그림, 가공 시계열을 로컬 프로젝트 폴더 어디에 저장해야 하는지 정리한 최종 저장 계획표이다.

프로젝트 기준 폴더는 다음 위치로 본다.

```text
C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project
```

---

## 1. 최종 보고서 사용 순서

| order | filename | recommended_folder | report_group | note |
| --- | --- | --- | --- | --- |
| 1 | 00_05_Project_foundation_and_HSI_baseline.md | docs | 최종 사용 | 00~05 초반 데이터·HSI baseline 구조 |
| 2 | 06_09_Signal_combo_and_event_balance_diagnostic.md | docs | 최종 사용 | 06~09 신호조합·event balance 보조진단 |
| 3 | 10_Inertia_lambda_experiment.md | docs | 최종 사용 | 10 Lambda 부분조정 실험 |
| 4 | 11_Theta_sensitivity_experiment.md | docs | 최종 사용 | 11 Theta 민감도 실험 |
| 5 | 12_13_Macro_companion_diagnostic.md | docs | 최종 사용 | 12~13 Macro companion 진단 |
| 6 | 14_Macro_companion_overlay.md | docs | 최종 사용 | 14 Macro soft overlay 실험 |
| 7 | 15_Lambda_macro_overlay_sensitivity.md | docs | 최종 사용 | 15 Lambda+macro 민감도 |
| 8 | 16_Regime_robustness_with_fixed_bm.md | docs | 최종 사용: 기존 16번 대신 우선 | 16 Robustness 보완판, Fixed BM 포함 |
| 9 | 17_Benchmark_alignment.md | docs | 최종 사용 | 17 Benchmark alignment |
| 10 | 20_23_Final_candidate_selection_with_fixed_bm.md | docs | 최종 사용: 기존 20~23번 대신 우선 | 20~23 최종 후보 선정, Fixed BM 포함 |

위 순서가 최종 보고서 작업 흐름이다. 특히 `16_Regime_robustness_with_fixed_bm.md`와 `20_23_Final_candidate_selection_with_fixed_bm.md`는 기존 보완 전 파일보다 우선 사용한다.

---

## 2. 산출물 개수 요약

| artifact_type | recommended_folder | count |
| --- | --- | --- |
| figure_png | output/figures | 36 |
| note_md | docs | 2 |
| processed_csv | data/processed | 1 |
| report_md | docs | 10 |
| table_csv | output/tables | 23 |

---

## 3. 저장 위치 원칙

| 산출물 종류 | 저장 위치 | 설명 |
|---|---|---|
| `.md` 보고서 | `docs/` | 실험별 보고서와 note |
| `.csv` 요약표 | `output/tables/` | 보고서에 들어가는 요약표·진단표 |
| `.png` 그림 | `output/figures/` | Markdown 보고서에서 참조하는 그림 |
| 가공 시계열 `.csv` | `data/processed/` | 후속 그림 재생성이나 추가 분석에 쓰는 월별 시계열 |

---

## 4. 반드시 우선 사용할 보완판

| 기존 파일 | 우선 사용할 파일 | 이유 |
|---|---|---|
| `16_Regime_robustness.md` | `16_Regime_robustness_with_fixed_bm.md` | Fixed 70/20/10 메인 BM 포함 |
| `20_23_Final_candidate_selection.md` | `20_23_Final_candidate_selection_with_fixed_bm.md` | 최종 후보 비교에 Fixed BM 포함 |

기존 파일은 삭제하지 않고 보존해도 된다. 다만 최종 발표와 최종 보고서에서는 `_with_fixed_bm` 버전을 우선 사용한다.

---

## 5. 누락 확인

없음

---

## 6. 저장 후 확인할 것

1. `docs/`에 md 보고서가 모두 들어갔는지 확인한다.  
2. md 파일 안의 그림 경로가 `../output/figures/...` 형식이므로, png 파일은 반드시 `output/figures/`에 넣는다.  
3. 새로 생성된 csv 요약표는 `output/tables/`에 넣는다.  
4. `main_final_report_candidate_timeseries_with_fixed_bm.csv`는 가공 시계열이므로 `data/processed/`에 넣는다.  
5. 최종 비교 체계는 아래처럼 통일한다.

```text
메인 BM = Fixed 70/20/10 BM
보조 BM = EW Benchmark
내부 기준선 = HSI baseline
최종 후보 = Lambda 0.1 / Lambda 0.3
```

---

## 7. 생성된 manifest 파일

이 문서와 함께 생성된 CSV manifest는 다음 파일이다.

```text
main_final_generated_artifact_manifest.csv
```

이 파일은 각 산출물의 파일명, 권장 저장 위치, 보고서 그룹, 파일 존재 여부, 크기를 정리한다.

---

# 새로 생성된 산출물 저장 위치 정리

## docs/ 로 옮길 보고서 md 파일

```text
main_final_artifact_save_plan.md
```

## output/tables/ 로 옮길 csv 표 파일

```text
main_final_generated_artifact_manifest.csv
```

## output/figures/ 로 옮길 png 그림 파일

```text
없음
```

## data/processed/ 로 옮길 파일

```text
없음
```

이번 작업은 저장 위치를 정리하는 manifest 작업이므로, 새 그림이나 새 가공 시계열은 생성하지 않았다.
