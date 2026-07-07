"""
Stage Attribution (RA 요구사항: 성과 기여도 분석).

EW(단순 동일비중)를 기준선으로, λ 전략의 초과수익을 4개 효과로 가법 분해한다.

    초과수익(λ_net − EW) = SAA효과 + 타이밍효과 + λ_smoothing효과 + 비용효과

각 효과(월별, 자산 a 합):
    SAA_t     = Σ (w_BM,a − w_EW,a) · r_a        전략적 70/20/10 선택(vs 단순 EW)
    Timing_t  = Σ (w_base,a − w_BM,a) · r_a       HSI 즉시비중 재배분(vs 전략적) = TAA
    Lambda_t  = Σ (w_lam,a − w_base,a) · r_a       부분조정(vs 즉시비중)
    Cost_t    = − turnover_t · cost_rate           거래비용 드래그

telescoping 합이 R_lam_net − R_EW 로 정확히 맞는다(항등식).

의존성: numpy/pandas. 실제 실행에는 baseline/λ 실현비중 시계열 필요(현재 repo에 없음).
아래 함수는 DataFrame 인자를 받으므로 합성 데이터로 단위 검증 가능.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.config import ASSETS
from common.io_utils import save_table
from common.paths import TABLE_DIR
from pipeline.config import COST_RATE_GRID, FINAL_COST_LABEL, FIXED_BM_WEIGHTS

WEIGHT_COLS = [f"{a}_weight" for a in ASSETS]


def _w(df: pd.DataFrame, assets: list[str]) -> np.ndarray:
    return df[[f"{a}_weight" for a in assets]].to_numpy(dtype=float)


def monthly_attribution(
    returns: pd.DataFrame,
    baseline_weights: pd.DataFrame,
    lambda_weights: pd.DataFrame,
    turnover: pd.Series,
    *,
    cost_rate: float | None = None,
    bm_weights: dict | None = None,
    ew_weights: dict | None = None,
    assets: list[str] | None = None,
) -> pd.DataFrame:
    """월별 4효과 분해표."""
    assets = assets or ASSETS
    cost_rate = COST_RATE_GRID[FINAL_COST_LABEL] if cost_rate is None else cost_rate
    bm = np.array([(bm_weights or FIXED_BM_WEIGHTS)[a] for a in assets], dtype=float)
    ew = (np.array([ew_weights[a] for a in assets], dtype=float)
          if ew_weights else np.full(len(assets), 1.0 / len(assets)))

    base = returns[["Date"]].copy().reset_index(drop=True)
    r = returns[assets].to_numpy(dtype=float)
    w_base = _w(baseline_weights.reset_index(drop=True), assets)
    w_lam = _w(lambda_weights.reset_index(drop=True), assets)
    turn = pd.to_numeric(pd.Series(turnover).reset_index(drop=True), errors="coerce").fillna(0.0).to_numpy()

    R_ew = (ew * r).sum(axis=1)
    R_bm = (bm * r).sum(axis=1)
    R_base = (w_base * r).sum(axis=1)
    R_lam_gross = (w_lam * r).sum(axis=1)
    cost = turn * cost_rate
    R_lam_net = R_lam_gross - cost

    saa = ((bm - ew) * r).sum(axis=1)
    timing = ((w_base - bm) * r).sum(axis=1)
    lam = ((w_lam - w_base) * r).sum(axis=1)
    cost_effect = -cost
    total = R_lam_net - R_ew

    base["R_ew"] = R_ew
    base["R_bm"] = R_bm
    base["R_base_gross"] = R_base
    base["R_lambda_gross"] = R_lam_gross
    base["R_lambda_net"] = R_lam_net
    base["saa_effect"] = saa
    base["timing_effect"] = timing
    base["lambda_effect"] = lam
    base["cost_effect"] = cost_effect
    base["total_excess_vs_ew"] = total
    base["residual_check"] = total - (saa + timing + lam + cost_effect)
    return base


def attribution_summary(monthly: pd.DataFrame) -> pd.DataFrame:
    """4효과의 누적 기여·월평균·연율화·기여비중 요약표."""
    effects = ["saa_effect", "timing_effect", "lambda_effect", "cost_effect"]
    total_sum = monthly["total_excess_vs_ew"].sum()
    rows = []
    for e in effects:
        s = monthly[e].sum()
        rows.append({
            "effect": e.replace("_effect", ""),
            "sum_contribution": s,
            "mean_monthly": monthly[e].mean(),
            "annualized": monthly[e].mean() * 12,
            "share_of_total_pct": (s / total_sum * 100) if total_sum != 0 else np.nan,
        })
    rows.append({
        "effect": "total_excess_vs_ew",
        "sum_contribution": total_sum,
        "mean_monthly": monthly["total_excess_vs_ew"].mean(),
        "annualized": monthly["total_excess_vs_ew"].mean() * 12,
        "share_of_total_pct": 100.0,
    })
    return pd.DataFrame(rows)


def cumulative_attribution(monthly: pd.DataFrame) -> pd.DataFrame:
    """효과별 누적 기여 시계열(누적 막대/영역 그래프용)."""
    out = monthly[["Date"]].copy()
    for e in ["saa_effect", "timing_effect", "lambda_effect", "cost_effect", "total_excess_vs_ew"]:
        out[f"cum_{e}"] = monthly[e].cumsum()
    return out


def run_attribution(
    returns: pd.DataFrame,
    baseline_weights: pd.DataFrame,
    lambda_weights: pd.DataFrame,
    turnover: pd.Series,
    *,
    cost_rate: float | None = None,
    save: bool = False,
) -> dict:
    """월별→요약→누적을 한 번에 계산. save=True면 output/tables에 저장."""
    monthly = monthly_attribution(returns, baseline_weights, lambda_weights, turnover, cost_rate=cost_rate)
    summary = attribution_summary(monthly)
    cumulative = cumulative_attribution(monthly)
    if save:
        save_table(monthly, TABLE_DIR / "attribution_monthly.csv")
        save_table(summary, TABLE_DIR / "attribution_summary.csv")
        save_table(cumulative, TABLE_DIR / "attribution_cumulative.csv")
    return {"monthly": monthly, "summary": summary, "cumulative": cumulative}


if __name__ == "__main__":
    print("stage_attribution: 성과 기여도 분해. run_attribution(returns, baseline_w, lambda_w, turnover) 사용.")
