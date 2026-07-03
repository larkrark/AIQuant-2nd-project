# HSI ETF Defensive Overlay Report Artifacts

이 폴더는 HSI 기반 ETF 방어형 Overlay 프로젝트의 보고서, 보고서용 표, 그림, note 산출물을 GitHub 업로드용으로 정리한 묶음입니다.

## Folder structure

```text
reports/          # 실험별 Markdown 보고서
notes/            # 짧은 note 파일
output/figures/   # 보고서에서 참조하는 PNG 그림
output/tables/    # 보고서 관련 CSV 표
meta/             # 업로드 manifest
```

## Report flow

```text
00~05: 데이터·HSI 상태분류·baseline
10: Lambda 부분조정
11: Theta 민감도
12~13: Macro companion 진단
14: Macro overlay
15: Lambda + Macro overlay 민감도
16: Regime robustness
17: Benchmark alignment
20~23: Final candidate selection
```

## Important path note

보고서 안의 그림 링크는 대체로 다음 상대경로를 사용합니다.

```text
../output/figures/<figure_name>.png
```

따라서 Markdown 보고서는 repo root의 `reports/` 폴더에 두고, 그림은 repo root의 `output/figures/` 폴더에 두는 것을 권장합니다.
