"""
Stage F (리포트 16): Regime robustness check.

Lambda 0.1/0.3 후보를 기간별·HSI 상태별·큰 손실월 기준으로 흔들어
역할(0.1=방어형, 0.3=균형형)이 유지되는지 검증. 참고: 리포트 16 §요약표.
"""

import pandas as pd


def regime_robustness_check(candidate_backtests: pd.DataFrame, regimes: dict | None = None) -> pd.DataFrame:
    raise NotImplementedError("regime_robustness_check: 구간 정의 확정 후 구현.")
