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

[v2 대안 분해 — 2026-07-08 추가]
기존 분해는 70/20/10 앵커 탓에 HSI의 평균 방어적 비중(익스포저 격차)이
timing 항에 계상되는 착시가 있다(실측: timing −0.963 중 −0.883이 정적 격차).
v2는 앵커를 "HSI 목표비중의 시간평균 w̄_base"로 바꿔 셔플 검정과 일관된 구조로 분해한다.

    초과수익(λ_net − EW) = 익스포저효과 + 순수타이밍효과 + λ_smoothing효과 + 비용효과

    Exposure_t    = Σ (w̄_base,a − w_EW,a) · r_a    HSI가 만드는 평균 방어적 비중(vs EW)
    PureTiming_t  = Σ (w_base,t,a − w̄_base,a) · r_a  시점선택(공분산) — 블록 셔플이 파괴하는 부분
    Lambda_t, Cost_t 는 기존과 동일.

근거: docs/experiment_notes/셔플_대조군_MC_결과해석_2026-07-08.md

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


def monthly_attribution_v2(
    returns: pd.DataFrame,
    baseline_weights: pd.DataFrame,
    lambda_weights: pd.DataFrame,
    turnover: pd.Series,
    *,
    cost_rate: float | None = None,
    ew_weights: dict | None = None,
    assets: list[str] | None = None,
) -> pd.DataFrame:
    """월별 4효과 분해표 (v2: 앵커 = HSI 목표비중 시간평균 w̄_base).

    exposure_effect  = (w̄_base − EW)·r   평균 방어적 비중의 기회비용/편익
    pure_timing_effect = (w_base − w̄_base)·r   순수 시점선택(공분산) 항
    lambda_effect, cost_effect 는 기존 정의와 동일. telescoping 항등식 유지.
    """
    assets = assets or ASSETS
    cost_rate = COST_RATE_GRID[FINAL_COST_LABEL] if cost_rate is None else cost_rate
    ew = (np.array([ew_weights[a] for a in assets], dtype=float)
          if ew_weights else np.full(len(assets), 1.0 / len(assets)))

    base = returns[["Date"]].copy().reset_index(drop=True)
    r = returns[assets].to_numpy(dtype=float)
    w_base = _w(baseline_weights.reset_index(drop=True), assets)
    w_lam = _w(lambda_weights.reset_index(drop=True), assets)
    turn = pd.to_numeric(pd.Series(turnover).reset_index(drop=True), errors="coerce").fillna(0.0).to_numpy()
    w_avg = w_base.mean(axis=0)

    R_ew = (ew * r).sum(axis=1)
    cost = turn * cost_rate
    R_lam_net = (w_lam * r).sum(axis=1) - cost

    exposure = ((w_avg - ew) * r).sum(axis=1)
    pure_timing = ((w_base - w_avg) * r).sum(axis=1)
    lam = ((w_lam - w_base) * r).sum(axis=1)
    cost_effect = -cost
    total = R_lam_net - R_ew

    base["R_ew"] = R_ew
    base["R_lambda_net"] = R_lam_net
    base["exposure_effect"] = exposure
    base["pure_timing_effect"] = pure_timing
    base["lambda_effect"] = lam
    base["cost_effect"] = cost_effect
    base["total_excess_vs_ew"] = total
    base["residual_check"] = total - (exposure + pure_timing + lam + cost_effect)
    for a, wv in zip(assets, w_avg):
        base.attrs[f"avg_weight_{a}"] = float(wv)
    return base


EFFECTS_V1 = ["saa_effect", "timing_effect", "lambda_effect", "cost_effect"]
EFFECTS_V2 = ["exposure_effect", "pure_timing_effect", "lambda_effect", "cost_effect"]


def attribution_summary(monthly: pd.DataFrame, effects: list[str] | None = None) -> pd.DataFrame:
    """4효과의 누적 기여·월평균·연율화·기여비중 요약표."""
    effects = effects or EFFECTS_V1
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


def cumulative_attribution(monthly: pd.DataFrame, effects: list[str] | None = None) -> pd.DataFrame:
    """효과별 누적 기여 시계열(누적 막대/영역 그래프용)."""
    effects = effects or EFFECTS_V1
    out = monthly[["Date"]].copy()
    for e in effects + ["total_excess_vs_ew"]:
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
    """월별→요약→누적을 한 번에 계산 (v1 기존 + v2 대안 분해). save=True면 output/tables에 저장."""
    monthly = monthly_attribution(returns, baseline_weights, lambda_weights, turnover, cost_rate=cost_rate)
    summary = attribution_summary(monthly)
    cumulative = cumulative_attribution(monthly)
    monthly_v2 = monthly_attribution_v2(returns, baseline_weights, lambda_weights, turnover, cost_rate=cost_rate)
    summary_v2 = attribution_summary(monthly_v2, EFFECTS_V2)
    cumulative_v2 = cumulative_attribution(monthly_v2, EFFECTS_V2)
    if save:
        save_table(monthly, TABLE_DIR / "attribution_monthly.csv")
        save_table(summary, TABLE_DIR / "attribution_summary.csv")
        save_table(cumulative, TABLE_DIR / "attribution_cumulative.csv")
        save_table(monthly_v2, TABLE_DIR / "attribution_monthly_v2.csv")
        save_table(summary_v2, TABLE_DIR / "attribution_summary_v2.csv")
        save_table(cumulative_v2, TABLE_DIR / "attribution_cumulative_v2.csv")
    return {"monthly": monthly, "summary": summary, "cumulative": cumulative,
            "monthly_v2": monthly_v2, "summary_v2": summary_v2, "cumulative_v2": cumulative_v2}


if __name__ == "__main__":
    print("stage_attribution: 성과 기여도 분해. run_attribution(returns, baseline_w, lambda_w, turnover) 사용.")
