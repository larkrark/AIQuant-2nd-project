# HSI Lambda Follow-up 코드 배치 가이드

## 안전 배치 원칙

본 프로젝트의 기존 `src/` 루트에는 이미 번호 기반 실행 파일이 있으므로, 업로드된 `00, 24, 28~34` 후속 실험 코드는 `src/` 루트에 직접 병합하지 않습니다.

권장 배치:

```text
src/lambda_followup/
docs/lambda_followup/
reports/lambda_followup/
```

## 배치 후 트리

```text
AIQuant-2nd-project/
├─ src/
│  └─ lambda_followup/
│     ├─ config.py
│     ├─ common.py
│     ├─ 00_smoke_test.py
│     ├─ 24_factor_loading_diagnostic.py
│     ├─ 28_lambda_response_curve.py
│     ├─ 29_asymmetric_lambda_grid.py
│     ├─ 30_dynamic_lambda_rule_v1.py
│     ├─ 31_validation.py
│     ├─ 32_candidate_selection.py
│     ├─ 33_report_outputs.py
│     ├─ 34_adoption_decision.py
│     └─ run_lambda_followup_all.py
├─ docs/
│  └─ lambda_followup/
│     ├─ README_lambda_followup_original.md
│     ├─ build_docs_v3.js
│     └─ PLACEMENT_GUIDE.md
└─ reports/
   └─ lambda_followup/
```

## config.py 수정

원본 `hsi_lambda/src/` 구조에서는 `PROJECT_DIR = parents[1]`이 맞지만, 본 프로젝트에서는 `src/lambda_followup/` 아래에 배치하므로 다음처럼 수정했습니다.

```python
PROJECT_DIR = Path(__file__).resolve().parents[2]
```

## 실행

프로젝트 루트에서 실행합니다.

```powershell
cd C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project

.\.venv\Scripts\python.exe .\src\lambda_followup\00_smoke_test.py
.\.venv\Scripts\python.exe .\src\lambda_followup\28_lambda_response_curve.py
.\.venv\Scripts\python.exe .\src\lambda_followup\29_asymmetric_lambda_grid.py
.\.venv\Scripts\python.exe .\src\lambda_followup\30_dynamic_lambda_rule_v1.py
.\.venv\Scripts\python.exe .\src\lambda_followup\31_validation.py
.\.venv\Scripts\python.exe .\src\lambda_followup\32_candidate_selection.py
.\.venv\Scripts\python.exe .\src\lambda_followup\33_report_outputs.py
.\.venv\Scripts\python.exe .\src\lambda_followup\34_adoption_decision.py
.\.venv\Scripts\python.exe .\src\lambda_followup\24_factor_loading_diagnostic.py
```

통합 실행:

```powershell
.\.venv\Scripts\python.exe .\src\lambda_followup\run_lambda_followup_all.py
```

## 입력 파일

필수:

```text
data/processed/main_final_monthly_return_decimal.csv
data/processed/main_final_baseline_rebalance_weights.csv
```

선택:

```text
data/processed/factor_inputs_monthly.csv
```

## Git add

```powershell
git add .\src\lambda_followup
git add .\docs\lambda_followup
git add .\reports\lambda_followup
```


## 추가 패치

연환산 변동성 반영에 맞춰 `30_dynamic_lambda_rule_v1.py`뿐 아니라 `00_smoke_test.py`의 누수 검증 컬럼명도 `annualized_volatility_z`로 맞췄습니다.
