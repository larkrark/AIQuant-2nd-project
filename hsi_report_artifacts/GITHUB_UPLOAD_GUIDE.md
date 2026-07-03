# GitHub Upload Guide

## 1. 권장 업로드 위치

이 패키지 안의 폴더를 GitHub repository root에 그대로 복사합니다.

```text
<repo-root>/
├─ reports/
├─ notes/
├─ output/
│  ├─ figures/
│  └─ tables/
├─ meta/
└─ README_HSI_REPORT_ARTIFACTS.md
```

## 2. PowerShell 예시

아래 명령은 repository root에서 실행하는 예시입니다.

```powershell
git status
git add reports/ notes/ output/figures/ output/tables/ meta/ README_HSI_REPORT_ARTIFACTS.md GITHUB_UPLOAD_GUIDE.md
git commit -m "Add HSI final report artifacts"
git push
```

## 3. 먼저 확인할 것

```powershell
git status
git diff --stat
```

## 4. 커밋 메시지 후보

```text
Add HSI final experiment reports and figures
```

또는

```text
Add HSI overlay final report artifacts
```

## 5. 주의

- 원본 데이터나 너무 큰 zip 파일은 꼭 필요한 경우가 아니면 올리지 않습니다.
- 보고서 링크를 유지하려면 `reports/`와 `output/figures/`의 상대 위치를 바꾸지 않는 것이 안전합니다.
- GitHub에서 Markdown 그림이 안 보이면 보고서 파일 위치와 `../output/figures/` 경로를 먼저 확인합니다.
