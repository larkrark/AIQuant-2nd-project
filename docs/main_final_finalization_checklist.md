# Main Final Report Finalization Checklist

## 목적

이 문서는 최종 통합 보고서 갱신 후 제출 전 확인해야 할 항목을 정리한다.

## 1. 이번 작업 결과

| 항목 | 결과 |
|---|---|
| 최종 통합 보고서 | `main_final_hsi_overlay_result_report_with_fixed_bm_final.md` 생성 |
| BM 기준 | Fixed 70/20/10 BM = 메인 BM, EW Benchmark = 보조 BM |
| 최종 후보 | Lambda 0.1, Lambda 0.3 |
| placeholder audit | `main_final_placeholder_audit.csv` 생성 |
| audit hit 수 | 24개 |

## 2. 최종 제출 전 확인 순서

1. `main_final_hsi_overlay_result_report_with_fixed_bm_final.md`를 `docs/`에 저장한다.
2. 기존 통합 보고서 대신 이 파일을 최종 기준으로 사용한다.
3. `main_final_placeholder_audit.csv`를 열어 placeholder 문장을 확인한다.
4. 최종 제출본에서는 placeholder 문장을 삭제하거나 실제 문장으로 바꾼다.
5. Markdown에서 참조한 그림 파일이 모두 `output/figures/`에 있는지 확인한다.
6. `_with_fixed_bm` 보완판을 16번, 20~23번의 우선 사용 파일로 둔다.
7. 최종 zip 또는 Git 업로드 전 `main_final_artifact_save_plan.md`와 manifest를 함께 확인한다.

## 3. 최종 비교 체계

```text
메인 BM = Fixed 70/20/10 BM
보조 BM = EW Benchmark
내부 기준선 = HSI baseline
최종 후보 = Lambda 0.1 / Lambda 0.3
```

## 4. 제출용 핵심 문장

> Fixed 70/20/10 BM은 CAGR이 가장 높지만 MDD가 크고, EW Benchmark는 안정성이 높다. Lambda 0.1과 Lambda 0.3은 두 BM을 모든 지표에서 압도하는 전략이 아니라, Fixed BM 대비 낙폭을 줄이고 EW 대비 성장성과 Calmar를 개선하는 방어형 ETF RA 후보로 해석한다.

---

# 새로 생성된 산출물 저장 위치 정리

## docs/ 로 옮길 보고서 md 파일

```text
main_final_finalization_checklist.md
```

## output/tables/ 로 옮길 csv 표 파일

```text
main_final_placeholder_audit.csv
```

## output/figures/ 로 옮길 png 그림 파일

```text
없음
```

## data/processed/ 로 옮길 파일

```text
없음
```
