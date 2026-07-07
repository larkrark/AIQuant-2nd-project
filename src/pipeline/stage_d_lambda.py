"""
Stage D (리포트 10~11): Lambda 부분조정 overlay.

부분조정 규칙(리포트 10 원문):
    이번 달 실제 비중 = 이전 달 실제 비중 + lambda * (이번 달 HSI 목표비중 - 이전 달 실제 비중)
    current = previous + lambda * (target - previous)

lambda=1.0 -> 즉시 목표비중(HSI baseline), lambda 작을수록 느린 조정(저회전).

동적 lambda 두 가지
- dynamic_lambda_series : 연속형(감마) lambda_t = clip(base + gamma*risk_score). (실험용)
- rule_based_dynamic_lambda : E30-M 규칙형. 기본 0.3 + 고위험/안정완화 예외.
  값은 E28에서 확인된 후보(0.1/0.3/0.5)에서만 가져온다(과적합 방지, optimizer 아님).
"""

import numpy as np
import pandas as pd

from common.config import ASSETS

WEIGHT_COLS = [f"{a}_weight" for a in ASSETS]


def apply_lambda_partial_adjustment(target_weights, lam, weight_cols=None, initial=None):
    """
    목표비중 시계열(Date + weight_cols)에 부분조정을 적용해 실현비중을 계산한다.

    lam: 스칼라(고정 lambda) 또는 길이 n 배열(월별 lambda_t, 동적 lambda).
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
    """연속형 동적 lambda: lambda_t = clip(lam_min, lam_max, lambda_base + gamma*risk_score)."""
    if not (0 < lam_min <= lam_max <= 1):
        raise ValueError("0 < lam_min <= lam_max <= 1 이어야 합니다.")
    z = pd.Series(risk_score).to_numpy(dtype=float)
    lam = lambda_base + gamma * z
    return np.clip(lam, lam_min, lam_max)


def _relief_persistence(states) -> np.ndarray:
    """risk_relief 연속 지속 개월 수(현재 월 포함)."""
    s = list(states)
    out = np.zeros(len(s), dtype=int)
    c = 0
    for i, v in enumerate(s):
        c = c + 1 if v == "risk_relief" else 0
        out[i] = c
    return out


def rule_based_dynamic_lambda(
    conditions: pd.DataFrame,
    *,
    lam_default: float = 0.3,
    lam_high_risk: float = 0.1,
    lam_easing: float = 0.5,
    vol_z_high: float = 1.0,
    drawdown_low: float = -0.10,
    macro_risk_high: int = 2,
    relief_persist_months: int = 3,
):
    """
    E30-M 규칙 기반 동적 lambda (기본 lam_default + 고위험/안정완화 예외).

    conditions 컬럼(월별, 룩어헤드 차단된 값):
      volatility_z, rolling_drawdown, macro_risk_score, hsi_state, momentum_z

    규칙(우선순위: 고위험 > 안정완화 > 기본)
      - 고위험: volatility_z > vol_z_high  또는  rolling_drawdown < drawdown_low
                또는  macro_risk_score >= macro_risk_high        -> lam_high_risk (0.1)
      - 안정완화: risk_relief >= relief_persist_months 지속 &
                 volatility_z < 0 & momentum_z > 0                -> lam_easing (0.5)
      - 그 외:                                                     -> lam_default (0.3)

    dynamic_v1_macro는 여기서 macro_risk_score(=rate_up_flag+fx_up_flag)를 고위험 조건에 포함한 형태.
    macro 데이터가 없으면 macro_risk_score=0으로 두면 dynamic_v1(비-macro)과 동일해진다.

    반환: (lambda_t: np.ndarray, labels: np.ndarray[str])  labels ∈ {high_risk, easing, default}
    """
    df = conditions.reset_index(drop=True)
    n = len(df)
    vol_z = pd.to_numeric(df.get("volatility_z", pd.Series([np.nan] * n)), errors="coerce").to_numpy()
    dd = pd.to_numeric(df.get("rolling_drawdown", pd.Series([np.nan] * n)), errors="coerce").to_numpy()
    macro = pd.to_numeric(df.get("macro_risk_score", pd.Series([0] * n)), errors="coerce").fillna(0).to_numpy()
    mom_z = pd.to_numeric(df.get("momentum_z", pd.Series([np.nan] * n)), errors="coerce").to_numpy()
    persist = _relief_persistence(df.get("hsi_state", pd.Series([""] * n)))

    # NaN 비교는 False -> 해당 조건 미발동(기본으로 귀결). 룩어헤드 차단.
    high_risk = (vol_z > vol_z_high) | (dd < drawdown_low) | (macro >= macro_risk_high)
    easing = (persist >= relief_persist_months) & (vol_z < 0) & (mom_z > 0)

    lam = np.full(n, lam_default, dtype=float)
    labels = np.full(n, "default", dtype=object)
    # 안정완화 먼저 칠하고, 고위험이 덮어써 우선순위(고위험 > 안정완화)를 보장
    lam[easing] = lam_easing
    labels[easing] = "easing"
    lam[high_risk] = lam_high_risk
    labels[high_risk] = "high_risk"
    return lam, labels


def build_lambda_target_from_states(baseline_weights, lambdas):
    """각 lambda 후보에 대해 실현비중 시계열 dict 반환."""
    return {lam: apply_lambda_partial_adjustment(baseline_weights, lam) for lam in lambdas}


def apply_asymmetric_lambda(target_weights, lam_up, lam_down, *,
                            risk_asset=None, weight_cols=None, initial=None):
    """
    비대칭 λ (보고서 E29): 위험자산(기본 069500) 목표비중이 이전 실현비중 대비
    줄어드는 달(de-risking)엔 lam_down, 늘어나는(또는 유지) 달(re-risking)엔 lam_up.
    그 달 세 자산에 같은 λ_dir을 적용해 비중 합=1 유지.

        Δ = target_위험자산,t − 이전_실현_위험자산
        λ_dir = lam_down if Δ < 0 else lam_up
        w_t = w_{t-1} + λ_dir × (target_t − w_{t-1})
    """
    cols = weight_cols or WEIGHT_COLS
    risk_col = f"{risk_asset or ASSETS[0]}_weight"
    if not (0 < lam_up <= 1 and 0 < lam_down <= 1):
        raise ValueError("lam_up, lam_down 은 (0, 1] 범위여야 합니다.")
    df = target_weights.sort_values("Date").reset_index(drop=True)
    targets = df[cols].to_numpy(dtype=float)
    ri = cols.index(risk_col)
    n = len(df)

    realized = np.empty_like(targets)
    labels = np.empty(n, dtype=object)
    prev = targets[0].copy() if initial is None else np.asarray(initial, dtype=float)
    for i in range(n):
        if i == 0:
            cur = prev
            labels[i] = "init"
        else:
            delta = targets[i, ri] - prev[ri]
            lam = lam_down if delta < 0 else lam_up
            labels[i] = "down" if delta < 0 else "up"
            cur = prev + lam * (targets[i] - prev)
        realized[i] = cur
        prev = cur

    out = df.copy()
    out[cols] = realized
    out["dir_label"] = labels
    return out
