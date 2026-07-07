"""
Stage D (리포트 10~11): Lambda 부분조정 overlay.

부분조정 규칙(리포트 10 원문):
    이번 달 실제 비중 = 이전 달 실제 비중 + lambda * (이번 달 HSI 목표비중 - 이전 달 실제 비중)
    current = previous + lambda * (target - previous)

lambda=1.0 -> 즉시 목표비중(HSI baseline), lambda 작을수록 느린 조정(저회전).
거래비용은 월별 Turnover * 비용률로 단순 차감(리포트 20~23).

[확장] 동적 lambda: 팩터 위험점수에 따라 lambda 를 조절하는 감마(gamma) 도입.
    lambda_t = clip(lam_min, lam_max, lambda_base + gamma * risk_score_t)
    - gamma 부호는 a priori 고정(위험점수↑ -> lambda↓ 이면 gamma<0).
    - 기본 비활성(config.DYNAMIC_LAMBDA['enabled']=False). OOS 검증 전 실험용.
"""

import numpy as np
import pandas as pd

from common.config import ASSETS

WEIGHT_COLS = [f"{a}_weight" for a in ASSETS]


def apply_lambda_partial_adjustment(target_weights, lam, weight_cols=None, initial=None):
    """
    목표비중 시계열(Date + weight_cols)에 부분조정을 적용해 실현비중을 계산한다.

    lam: 스칼라(고정 lambda) 또는 길이 n 배열(월별 lambda_t, 동적 lambda).
    - 첫 달은 initial(기본: 첫 목표비중)을 그대로 사용.
    - 이후: current = previous + lam_t*(target - previous).
    - lam=1.0 -> 실현==목표(즉시 이동).
    """
    cols = weight_cols or WEIGHT_COLS
    df = target_weights.sort_values("Date").reset_index(drop=True)
    targets = df[cols].to_numpy(dtype=float)
    n = len(df)

    if np.isscalar(lam):
        lam_arr = np.full(n, float(lam))
    else:
        lam_arr = np.asarray(lam, dtype=float)
        if len(lam_arr) != n:
            raise ValueError(f"lam 배열 길이({len(lam_arr)})가 관측수({n})와 다릅니다.")
    if not ((lam_arr > 0) & (lam_arr <= 1)).all():
        raise ValueError("모든 lambda 는 (0, 1] 범위여야 합니다.")

    realized = np.empty_like(targets)
    prev = targets[0].copy() if initial is None else np.asarray(initial, dtype=float)
    for i in range(n):
        cur = prev if i == 0 else prev + lam_arr[i] * (targets[i] - prev)
        realized[i] = cur
        prev = cur

    out = df.copy()
    out[cols] = realized
    return out


def apply_transaction_cost(monthly_return, turnover, cost_rate):
    """비용 차감 월수익률 = 월수익률 - (turnover * cost_rate). cost_rate 예: 0.0010=10bp."""
    return monthly_return - turnover.fillna(0) * cost_rate


def dynamic_lambda_series(risk_score, *, lambda_base, gamma, lam_min, lam_max):
    """
    위험 점수(risk_score, 표준화·룩어헤드 차단된 값; 높을수록 위험) -> 월별 lambda_t.

        lambda_t = clip(lam_min, lam_max, lambda_base + gamma * risk_score_t)

    gamma<0 이면 위험↑ 시 lambda↓(방어적으로 느리게). 부호는 a priori 고정할 것.
    clip 으로 (0<lam_min<=lambda_t<=lam_max<=1) 보장.
    """
    if not (0 < lam_min <= lam_max <= 1):
        raise ValueError("0 < lam_min <= lam_max <= 1 이어야 합니다.")
    z = pd.Series(risk_score).to_numpy(dtype=float)
    lam = lambda_base + gamma * z
    return np.clip(lam, lam_min, lam_max)


def build_lambda_target_from_states(baseline_weights, lambdas):
    """각 lambda 후보에 대해 실현비중 시계열 dict 반환."""
    return {lam: apply_lambda_partial_adjustment(baseline_weights, lam) for lam in lambdas}
