# Optional .gitignore additions

아래 항목은 필요할 때만 기존 .gitignore에 추가하세요.

```gitignore
# local temporary packages
*_reports.zip
github_upload_*/
__pycache__/
.ipynb_checkpoints/

# avoid uploading raw/private data unless intentionally versioned
data/raw/
*.xlsx
```

주의: 이번 패키지는 output/tables와 output/figures를 GitHub에 올리는 목적이므로 `output/` 전체를 ignore하면 안 됩니다.
