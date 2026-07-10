# HSI Lambda Follow-up Placement Package

업로드된 `hsi_lambda` 후속 실험 코드를 본 프로젝트에 안전하게 배치하기 위한 패키지입니다.

핵심 변경:
- `src/` 루트가 아니라 `src/lambda_followup/`에 배치
- `config.py`의 `PROJECT_DIR`를 `parents[2]`로 수정
- E30 변동성 조건을 `annualized_volatility_z` 표현으로 반영
- 통합 실행 runner 추가

자세한 내용은 `docs/lambda_followup/PLACEMENT_GUIDE.md`를 확인하세요.
