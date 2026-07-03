"""
Stage E (리포트 12~15): Macro companion 진단 및 soft overlay.

금리·환율 중심 macro risk 진단(HSI 대체 아님), HSI baseline 위 약한 방어 보정,
Lambda 0.1/0.3 × macro_scale(0.25/0.50/0.75) 민감도. GDP는 직접 입력 제외.
결론: MDD 소폭 개선하나 CAGR·Calmar·Turnover 비용으로 최종 후보를 대체 못 함(보조).
"""

import pandas as pd

from pipeline.config import MACRO_SCALES


def macro_risk_diagnostic(macro_data: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("macro_risk_diagnostic: macro 데이터 소스 확정 후 구현.")


def macro_soft_overlay(baseline_weights: pd.DataFrame, macro_state: pd.DataFrame, scale: float) -> pd.DataFrame:
    raise NotImplementedError("macro_soft_overlay: 보정 규칙 구현 필요.")


def lambda_macro_sensitivity(lambda_weights: dict, macro_state: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError(f"lambda_macro_sensitivity: macro_scale={MACRO_SCALES} 조합 구현 필요.")
