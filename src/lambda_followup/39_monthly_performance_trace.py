# -*- coding: utf-8 -*-
"""
39_monthly_performance_trace.py

목적
----
실무자가 월간 단위로 포트폴리오 성과 추이를 확인할 수 있도록
전략별 월수익률, 누적수익률, 누적 CAGR, Drawdown, Rolling Vol,
Rolling Sharpe를 생성한다.

생성 산출물
----------
output/tables/main_final_monthly_performance_trace.csv
output/figures/main_final_fig_monthly_cumulative_performance.png
output/figures/main_final_fig_monthly_drawdown_trace.png
output/figures/main_final_fig_monthly_rolling_risk_metrics.png
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
dyn_macro = importlib.import_module("30_dynamic_lambda_rule_v1_macro")


def savefig(fig, filename: str) -> Path:
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    out = C.FIGURE_DIR / filename
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def annualized_cagr_from_start(r: pd.Series) -> pd.Series:
    """
    각 월 시점까지 누적된 성과를 연환산 CAGR로 변환한다.
    첫 12개월 미만은 해석 안정성이 낮으므로 NaN 처리한다.
    """
    r = r.dropna()
    cum = (1 + r).cumprod()
    months = np.arange(1, len(cum) + 1)
    years = months / 12.0
    cagr = cum.values ** (1 / years) - 1
    out = pd.Series(cagr, index=cum.index)
    out.iloc[:11] = np.nan
    return out


def drawdown_series(r: pd.Series) -> pd.Series:
    """
    누적성과지수 기준 월별 drawdown.
    """
    idx = (1 + r.dropna()).cumprod()
    return idx / idx.cummax() - 1


def rolling_cagr(r: pd.Series, window: int = 12) -> pd.Series:
    """
    최근 window개월 누적수익률을 연환산.
    12개월이면 최근 1년 CAGR과 같은 의미.
    """
    return (1 + r).rolling(window).apply(np.prod, raw=True) ** (12 / window) - 1


def rolling_vol(r: pd.Series, window: int = 12) -> pd.Series:
    """
    최근 window개월 수익률의 연환산 변동성.
    """
    return r.rolling(window).std() * np.sqrt(12)


def rolling_sharpe(r: pd.Series, window: int = 12) -> pd.Series:
    """
    무위험수익률 0 가정의 최근 window개월 rolling Sharpe.
    """
    mean = r.rolling(window).mean() * 12
    vol = r.rolling(window).std() * np.sqrt(12)
    return mean / vol.replace(0, np.nan)


def build_backtests() -> dict:
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()

    bts = {}

    # 대칭 λ
    bts["lambda_0.1"] = X.run_lambda_backtest(returns, target_w, 0.1, 0.1)
    bts["lambda_0.3"] = X.run_lambda_backtest(returns, target_w, 0.3, 0.3)

    # 대표 비대칭 후보
    bts["asym_up0.1_down0.3"] = X.run_lambda_backtest(returns, target_w, 0.1, 0.3)

    # dynamic_v1
    sv = dyn.build_state_variables(returns, target_w)
    lam_t, cond = dyn.assign_lambda(sv)
    lam_t = lam_t.fillna(C.E30_RULE_V1["lambda_base"])
    bts["dynamic_v1"] = X.run_lambda_backtest(
        returns,
        target_w,
        np.nan,
        np.nan,
        lambda_series=lam_t,
    )

    # dynamic_v1_macro
    sv_macro = dyn_macro.build_state_variables_macro(returns, target_w)
    lam_macro, cond_macro, reason_macro = dyn_macro.assign_lambda_macro(sv_macro)
    lam_macro = lam_macro.fillna(C.E30_RULE_V1["lambda_base"])
    bts["dynamic_v1_macro"] = X.run_lambda_backtest(
        returns,
        target_w,
        np.nan,
        np.nan,
        lambda_series=lam_macro,
    )

    # BM
    start = next(iter(bts.values())).index.min()
    fixed = X.run_fixed_weight_backtest(returns, C.FIXED_BM_WEIGHTS, start)
    ew = X.run_fixed_weight_backtest(returns, C.EW_WEIGHTS, start)

    series = {k: v["strategy_return_gross"] for k, v in bts.items()}
    series["FixedBM_70_20_10"] = fixed
    series["EW"] = ew

    return bts, series


def main() -> None:
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    bts, series = build_backtests()

    # ------------------------------------------------------------
    # 1. 월간 성과 추이 테이블 생성
    # ------------------------------------------------------------
    rows = []

    for name, r in series.items():
        r = r.dropna().copy()

        cum_index = (1 + r).cumprod()
        cum_return = cum_index - 1
        cagr_to_date = annualized_cagr_from_start(r)
        dd = drawdown_series(r)
        roll_12m_cagr = rolling_cagr(r, 12)
        roll_12m_vol = rolling_vol(r, 12)
        roll_12m_sharpe = rolling_sharpe(r, 12)

        if name in bts:
            turnover = bts[name]["turnover"].reindex(r.index)
        else:
            turnover = pd.Series(0.0, index=r.index)

        temp = pd.DataFrame({
            "date": r.index,
            "strategy": name,
            "monthly_return_pct": r.values * 100,
            "cumulative_index": cum_index.values,
            "cumulative_return_pct": cum_return.values * 100,
            "cagr_to_date_pct": cagr_to_date.reindex(r.index).values * 100,
            "drawdown_pct": dd.reindex(r.index).values * 100,
            "rolling_12m_cagr_pct": roll_12m_cagr.reindex(r.index).values * 100,
            "rolling_12m_vol_pct": roll_12m_vol.reindex(r.index).values * 100,
            "rolling_12m_sharpe": roll_12m_sharpe.reindex(r.index).values,
            "monthly_turnover_pct": turnover.values * 100,
        })

        rows.append(temp)

    out_df = pd.concat(rows, ignore_index=True)
    out_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}monthly_performance_trace.csv"
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    # ------------------------------------------------------------
    # 2. 월간 누적성과 그림
    # ------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 5.5))

    plot_order = [
        "lambda_0.1",
        "lambda_0.3",
        "asym_up0.1_down0.3",
        "dynamic_v1",
        "dynamic_v1_macro",
        "FixedBM_70_20_10",
        "EW",
    ]

    for name in plot_order:
        if name not in series:
            continue
        r = series[name].dropna()
        ax.plot(
            r.index,
            (1 + r).cumprod(),
            label=name,
            linewidth=2.0 if name in ("dynamic_v1", "dynamic_v1_macro", "FixedBM_70_20_10") else 1.3,
            linestyle="--" if name in ("FixedBM_70_20_10", "EW") else "-",
        )

    if hasattr(C, "OOS_START"):
        ax.axvline(pd.to_datetime(C.OOS_START), linestyle="--", linewidth=1.0, alpha=0.7)

    ax.axhline(1.0, linewidth=0.8)
    ax.set_title("월간 누적성과 추이")
    ax.set_xlabel("월")
    ax.set_ylabel("누적성과지수")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    fig1 = savefig(fig, f"{C.FINAL_PREFIX}fig_monthly_cumulative_performance.png")

    # ------------------------------------------------------------
    # 3. 월간 Drawdown 그림
    # ------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 5.5))

    for name in plot_order:
        if name not in series:
            continue
        r = series[name].dropna()
        dd = drawdown_series(r)
        ax.plot(
            dd.index,
            dd * 100,
            label=name,
            linewidth=2.0 if name in ("dynamic_v1", "dynamic_v1_macro", "FixedBM_70_20_10") else 1.3,
            linestyle="--" if name in ("FixedBM_70_20_10", "EW") else "-",
        )

    if hasattr(C, "OOS_START"):
        ax.axvline(pd.to_datetime(C.OOS_START), linestyle="--", linewidth=1.0, alpha=0.7)

    ax.axhline(0.0, linewidth=0.8)
    ax.set_title("월간 Drawdown 추이")
    ax.set_xlabel("월")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    fig2 = savefig(fig, f"{C.FINAL_PREFIX}fig_monthly_drawdown_trace.png")

    # ------------------------------------------------------------
    # 4. Rolling 12개월 위험지표 그림
    #    너무 많은 전략을 한 번에 넣으면 복잡하므로 핵심 후보 중심
    # ------------------------------------------------------------
    core = ["dynamic_v1", "dynamic_v1_macro", "FixedBM_70_20_10", "EW"]

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)

    for name in core:
        if name not in series:
            continue
        r = series[name].dropna()

        axes[0].plot(r.index, rolling_12m_cagr(r) * 100, label=name)
        axes[1].plot(r.index, rolling_12m_vol(r) * 100, label=name)
        axes[2].plot(r.index, rolling_12m_sharpe(r), label=name)

    if hasattr(C, "OOS_START"):
        for ax in axes:
            ax.axvline(pd.to_datetime(C.OOS_START), linestyle="--", linewidth=1.0, alpha=0.7)

    axes[0].set_title("Rolling 12개월 CAGR")
    axes[0].set_ylabel("CAGR (%)")
    axes[0].grid(True, alpha=0.25)

    axes[1].set_title("Rolling 12개월 연환산 변동성")
    axes[1].set_ylabel("Vol (%)")
    axes[1].grid(True, alpha=0.25)

    axes[2].set_title("Rolling 12개월 Sharpe")
    axes[2].set_ylabel("Sharpe")
    axes[2].set_xlabel("월")
    axes[2].grid(True, alpha=0.25)

    axes[0].legend(fontsize=8)

    fig3 = savefig(fig, f"{C.FINAL_PREFIX}fig_monthly_rolling_risk_metrics.png")

    print("[완료] 39_monthly_performance_trace")
    print(f"- table: {out_path}")
    print(f"- fig cumulative: {fig1}")
    print(f"- fig drawdown: {fig2}")
    print(f"- fig rolling metrics: {fig3}")


if __name__ == "__main__":
    main()