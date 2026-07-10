# -*- coding: utf-8 -*-
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

SCRIPTS = [
    "00_smoke_test.py",
    "28_lambda_response_curve.py",
    "29_asymmetric_lambda_grid.py",
    "30_dynamic_lambda_rule_v1.py",
    "31_validation.py",
    "32_candidate_selection.py",
    "33_report_outputs.py",
    "34_adoption_decision.py",
    "24_factor_loading_diagnostic.py",
]

def main():
    print("=" * 80)
    print("HSI Lambda follow-up 통합 실행 시작")
    print(f"ROOT = {ROOT}")
    print("=" * 80)

    for script in SCRIPTS:
        print("\n" + "=" * 80)
        print(f"[RUN] {script}")
        print("=" * 80)
        result = subprocess.run([sys.executable, str(HERE / script)], cwd=str(ROOT), text=True)
        if result.returncode != 0:
            print(f"[STOP] {script} 실패 또는 입력 부족. returncode={result.returncode}")
            print("필수 입력 CSV 배치 후 해당 단계부터 다시 실행하세요.")
            break

    print("\n" + "=" * 80)
    print("HSI Lambda follow-up 통합 실행 종료")
    print("=" * 80)

if __name__ == "__main__":
    main()
