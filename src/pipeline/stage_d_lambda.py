"""
Stage D (리포트 10~11): Lambda 부분조정 overlay.

부분조정 규칙(리포트 10 원문):
    이번 달 실제 비중 = 이전 달 실제 비중 + λ × (이번 달 HSI 목표비중 - 이전 달 실제 비중)
    current = previous + λ * (target - previous)

λ=1.0 → 즉시 목표비중(HSI baseline), λ 작을수록 느린 조정(저회전).
거래비용은 월별 Turnover × 비용률로 단순 차감(리포트 20~23).
"""

import numpy as np
import pandas as pd

from common.config import ASSETS

WEIGHT_COLS = [f"{a}_weight" for a in ASSETS]


def apply_lambda_partial_adjustment(
    target_weights: pd.DataFrame,
    lam: float,
    weight_cols: list[str] | None = None,
    initial: list[float] | None = None,
) -> pd.DataFrame:
    """
    목표비중 시계열(Date + weight_cols)에 부분조정을 적용해 실현비중을 계산한다.

    - 첫 달은 initial(기본: 첫 목표비중)을 그대로 사용.
    - 이후 달: current = previous + lam*(target - previous).
    - lam=1.0 → 실현==목표(즉시 이동).
    """
    if not 0 < lam <= 1:
        raise ValueError(f"lam 은 (0, 1] 범위여야 합니다: {lam}")

    cols = weight_cols or WEIGHT_COLS
    df = target_weights.sort_values("Date").reset_index(drop=True)
    targets = df[cols].to_numpy(dtype=float)
    realized = np.empty_like(targets)

    prev = targets[0].copy() if initial is None else np.asarray(initial, dtype=float)
    for i in range(len(df)):
        cur = prev if i == 0 else prev + lam * (targets[i] - prev)
        realized[i] = cur
        prev = cur

    out = df.copy()
    out[cols] = realized
    return out


def apply_transaction_cost(monthly_return: pd.Series, turnover: pd.Series, cost_rate: float) -> pd.Series:
    """
    비용 차감 월수익률 = 월수익률 - (turnover * cost_rate).
    cost_rate 예: 0.0010 = 0.10% (10bp).
    """
    return monthly_return - turnover.fillna(0) * cost_rate


def build_lambda_target_from_states(baseline_weights: pd.DataFrame, lambdas: list[float]) -> dict:
    """
    각 lambda 후보에 대해 실현비중 시계열을 만든 dict 반환.
    baseline_weights: HSI 상태별 목표비중(Date + weight_cols).
    (백테스트 연결은 stage_selection / common.backtest 에서 수행)
    """
    return {lam: apply_lambda_partial_adjustment(baseline_weights, lam) for lam in lambdas}
