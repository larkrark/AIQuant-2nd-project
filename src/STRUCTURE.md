# src 구조 안내 (STRUCTURE)

```
src/
├── common/     # 공통 모듈 (경로/설정/IO/시각화/성과지표/백테스트)
├── pipeline/   # 새 파이프라인 (hsi_report_artifacts 리포트 00~17·20~23 반영)
├── dashboard/  # Streamlit 대시보드
├── legacy/     # 과거·중간 파이프라인 (00~30, portfolio_optimizer) — 복구용 보존
└── tests/      # pytest
```

최상위에 남은 20~23_* 스크립트는 조원이 merge한 최종 리포트/선별 스크립트 원본이며,
그 로직은 pipeline/ 으로 이식되었습니다(원본은 참조용 유지).

## pipeline (리포트 기반 새 파이프라인)

| 모듈 | 리포트 | 상태 |
|---|---|---|
| stage_a_data | 00~01 | 스텁 |
| stage_b_hsi | 02~05 | 스텁 |
| stage_c_diagnostics | 06~09 | 스텁 |
| stage_d_lambda | 10~11 | 구현(부분조정 + 거래비용) |
| stage_e_macro | 12~15 | 스텁 |
| stage_f_robustness | 16 | 스텁 |
| stage_g_benchmark | 17 | 구현(Fixed 70/20/10 BM) |
| stage_selection | 20~23 | 구현(비용·Turnover·최종 판단, 조원 20_select 이식) |

- 지도: cd src && python3 -m pipeline.run
- 확정 로직(lambda/cost/benchmark/selection)은 구현·테스트됨.
- 데이터·HSI 분류 등은 리포트가 참조하는 main_final_* 입력(현재 repo에 없음)이 필요해 스텁으로 두고,
  legacy 코드와 리포트를 참고해 채우도록 표시.

## legacy (복구용)
merge로 되돌아온 옛 00~30 + portfolio_optimizer를 이동. 경로 깊이만 보정(parents[2]).
_backups/src_*/ 에도 시점별 스냅샷 보관.

## tests
- tests/test_pipeline.py — common + pipeline 로직 검증
- 실행: cd src && python3 -m pytest tests/ -q

주의: 이 샌드박스에서는 git 커밋이 불가하고 파일 도구가 간헐적으로 파일을 손상시킵니다.
변경분은 PC에서 검증·커밋하세요. (docs/git_복구_및_커밋_안전장치_2026-07-03.md 참고)
