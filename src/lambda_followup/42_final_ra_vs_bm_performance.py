# -*- coding: utf-8 -*-
"""
42_final_ra_vs_bm_performance.py

목적
----
선정과정을 거친 이후의 최종 추천 RA 가상 포트폴리오와 BM 성과를 비교한다.

비교 대상
--------
1. Final_RA_dynamic_v1
   - 최종 추천 RA 가상 포트폴리오
   - dynamic_v1을 기본 후보로 사용

2. FixedBM_70_20_10
   - 메인 BM

3. EW
   - 보조 BM

생성 산출물
----------
output/figures/main_final_fig_final_ra_vs_bm_cumret.png
output/figures/main_final_fig_final_ra_vs_bm_drawdown.png
output/tables/main_final_final_ra_vs_bm_performance_table.csv
"""

import importlib
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
import common as X

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

dyn = importlib.import_module("30_dynamic_lambda_rule_v1")


FINAL_RA_NAME = "Final_RA_dynamic_v1"


def savefig(fig, filename: str) -> Path:
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    out = C.FIGURE_DIR / filename
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def cumulative_index(r: pd.Series) -> pd.Series:
    r = r.dropna()
    return (1.0 + r).cumprod()


def drawdown_series(r: pd.Series) -> pd.Series:
    idx = cumulative_index(r)
    return idx / idx.cummax() - 1.0


def perf_metrics(r: pd.Series, turnover: pd.Series | None = None) -> dict:
    """
    월수익률 기준 성과지표 계산.
    무위험수익률은 0으로 가정한다.
    """
    r = r.dropna().sort_index()

    if len(r) == 0:
        return {
            "months": 0,
            "cumulative_return_pct": np.nan,
            "cagr_pct": np.nan,
            "ann_vol_pct": np.nan,
            "mdd_pct": np.nan,
            "sharpe": np.nan,
            "calmar": np.nan,
            "avg_monthly_turnover_pct": np.nan,
            "ann_avg_turnover_pct": np.nan,
        }

    cumulative_return = (1.0 + r).prod() - 1.0
    years = len(r) / 12.0
    cagr = (1.0 + cumulative_return) ** (1.0 / years) - 1.0 if years > 0 else np.nan

    ann_vol = r.std() * np.sqrt(12.0)
    dd = drawdown_series(r)
    mdd = dd.min()

    sharpe = (r.mean() * 12.0) / ann_vol if ann_vol and ann_vol != 0 else np.nan
    calmar = cagr / abs(mdd) if mdd and mdd != 0 else np.nan

    if turnover is not None:
        to = turnover.reindex(r.index).fillna(0.0)
        avg_monthly_turnover = to.mean()
        ann_avg_turnover = avg_monthly_turnover * 12.0
    else:
        avg_monthly_turnover = 0.0
        ann_avg_turnover = 0.0

    return {
        "months": len(r),
        "cumulative_return_pct": cumulative_return * 100,
        "cagr_pct": cagr * 100,
        "ann_vol_pct": ann_vol * 100,
        "mdd_pct": mdd * 100,
        "sharpe": sharpe,
        "calmar": calmar,
        "avg_monthly_turnover_pct": avg_monthly_turnover * 100,
        "ann_avg_turnover_pct": ann_avg_turnover * 100,
    }


def get_period_masks(index: pd.DatetimeIndex) -> dict:
    """
    IS/OOS/FULL 구간을 만든다.
    config에 OOS_START가 있으면 그것을 사용한다.
    """
    idx = pd.to_datetime(index)

    periods = {
        "FULL": pd.Series(True, index=idx),
    }

    if hasattr(C, "OOS_START"):
        oos_start = pd.to_datetime(C.OOS_START)

        periods["IS"] = pd.Series(idx < oos_start, index=idx)
        periods["OOS"] = pd.Series(idx >= oos_start, index=idx)

    return periods


def build_final_ra_and_bm() -> tuple[dict, dict]:
    """
    최종 추천 RA 포트폴리오와 BM 월수익률을 생성한다.
    """
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()

    # Final RA = dynamic_v1
    state_vars = dyn.build_state_variables(returns, target_w)
    lambda_t, condition = dyn.assign_lambda(state_vars)
    lambda_t = lambda_t.fillna(C.E30_RULE_V1["lambda_base"])

    final_ra_bt = X.run_lambda_backtest(
        returns,
        target_w,
        np.nan,
        np.nan,
        lambda_series=lambda_t,
    )

    start = final_ra_bt.index.min()

    fixed_bm_r = X.run_fixed_weight_backtest(
        returns,
        C.FIXED_BM_WEIGHTS,
        start,
    ).dropna()

    ew_r = X.run_fixed_weight_backtest(
        returns,
        C.EW_WEIGHTS,
        start,
    ).dropna()

    series = {
        FINAL_RA_NAME: final_ra_bt["strategy_return_gross"].dropna(),
        "FixedBM_70_20_10": fixed_bm_r,
        "EW": ew_r,
    }

    turnovers = {
        FINAL_RA_NAME: final_ra_bt["turnover"].dropna(),
        "FixedBM_70_20_10": pd.Series(0.0, index=fixed_bm_r.index),
        "EW": pd.Series(0.0, index=ew_r.index),
    }

    return series, turnovers


def make_performance_table(series: dict, turnovers: dict) -> pd.DataFrame:
    """
    전략별 IS/OOS/FULL 성과지표 표 생성.
    """
    common_index = None

    for r in series.values():
        idx = pd.to_datetime(r.index)
        common_index = idx if common_index is None else common_index.intersection(idx)

    common_index = common_index.sort_values()
    periods = get_period_masks(common_index)

    rows = []

    for strategy, r in series.items():
        r = r.reindex(common_index).dropna()
        turnover = turnovers[strategy].reindex(common_index).fillna(0.0)

        for period_name, mask in periods.items():
            mask = mask.reindex(common_index).fillna(False)
            r_sub = r.loc[mask.values]
            to_sub = turnover.loc[mask.values]

            m = perf_metrics(r_sub, to_sub)

            row = {
                "strategy": strategy,
                "period": period_name,
                "start": r_sub.index.min() if len(r_sub) else pd.NaT,
                "end": r_sub.index.max() if len(r_sub) else pd.NaT,
            }
            row.update(m)
            rows.append(row)

    out = pd.DataFrame(rows)

    # 보기 좋은 순서
    period_order = {"IS": 0, "OOS": 1, "FULL": 2}
    strategy_order = {
        FINAL_RA_NAME: 0,
        "FixedBM_70_20_10": 1,
        "EW": 2,
    }

    out["strategy_order"] = out["strategy"].map(strategy_order)
    out["period_order"] = out["period"].map(period_order).fillna(99)

    out = (
        out.sort_values(["period_order", "strategy_order"])
        .drop(columns=["strategy_order", "period_order"])
        .reset_index(drop=True)
    )

    return out


def plot_cumulative(series: dict) -> Path:
    fig, ax = plt.subplots(figsize=(11.5, 5.8))

    for name, r in series.items():
        idx = cumulative_index(r)
        ax.plot(
            idx.index,
            idx.values,
            label=name,
            linewidth=2.4 if name == FINAL_RA_NAME else 1.8,
            linestyle="-" if name == FINAL_RA_NAME else "--",
        )

    if hasattr(C, "OOS_START"):
        ax.axvline(
            pd.to_datetime(C.OOS_START),
            linestyle="--",
            linewidth=1.0,
            alpha=0.8,
        )

    ax.axhline(1.0, linewidth=0.8)
    ax.set_title("최종 추천 RA 가상 포트폴리오와 BM 누적수익률 비교")
    ax.set_xlabel("월")
    ax.set_ylabel("누적성과지수")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=9)

    return savefig(fig, f"{C.FINAL_PREFIX}fig_final_ra_vs_bm_cumret.png")


def plot_drawdown(series: dict) -> Path:
    fig, ax = plt.subplots(figsize=(11.5, 5.8))

    for name, r in series.items():
        dd = drawdown_series(r)
        ax.plot(
            dd.index,
            dd.values * 100,
            label=name,
            linewidth=2.4 if name == FINAL_RA_NAME else 1.8,
            linestyle="-" if name == FINAL_RA_NAME else "--",
        )

    if hasattr(C, "OOS_START"):
        ax.axvline(
            pd.to_datetime(C.OOS_START),
            linestyle="--",
            linewidth=1.0,
            alpha=0.8,
        )

    ax.axhline(0.0, linewidth=0.8)
    ax.set_title("최종 추천 RA 가상 포트폴리오와 BM Drawdown 비교")
    ax.set_xlabel("월")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=9)

    return savefig(fig, f"{C.FINAL_PREFIX}fig_final_ra_vs_bm_drawdown.png")


def main() -> None:
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    series, turnovers = build_final_ra_and_bm()

    table = make_performance_table(series, turnovers)
    table_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}final_ra_vs_bm_performance_table.csv"
    table.to_csv(table_path, index=False, encoding="utf-8-sig")

    fig_cum = plot_cumulative(series)
    fig_dd = plot_drawdown(series)

    print("[완료] 42_final_ra_vs_bm_performance")
    print(f"- table: {table_path}")
    print(f"- fig cumulative: {fig_cum}")
    print(f"- fig drawdown: {fig_dd}")
    print()
    print(table.round(3).to_string(index=False))


if __name__ == "__main__":
    main()