# -*- coding: utf-8 -*-
"""
40_rolling_3y_performance_review.py

목적
----
월간 단위 수익률 흐름과 3년 rolling 성과를 확인한다.

실무자가 확인하려는 질문:
1. 어느 연도/월에 수익률이 좋고 나빴는가?
2. 3년씩 rolling했을 때 누적수익률, CAGR, 변동성, MDD, Sharpe가 어떻게 변하는가?
3. rolling 3년 구간에서 음수 누적수익률이 적은 전략은 무엇인가?
4. 전략 1, 2, 3 ... 중 어떤 후보가 더 안정적인가?

생성 산출물
----------
output/tables/main_final_rolling_3y_performance_metrics.csv
output/tables/main_final_rolling_3y_decision_summary.csv

output/figures/main_final_fig_monthly_return_heatmap_dynamic_v1.png
output/figures/main_final_fig_monthly_return_heatmap_dynamic_v1_macro.png
output/figures/main_final_fig_rolling_3y_cagr.png
output/figures/main_final_fig_rolling_3y_mdd.png
output/figures/main_final_fig_rolling_3y_sharpe.png
output/figures/main_final_fig_rolling_3y_negative_window_count.png
"""

import importlib
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
import common as X

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

dyn = importlib.import_module("30_dynamic_lambda_rule_v1")
dyn_macro = importlib.import_module("30_dynamic_lambda_rule_v1_macro")


WINDOW = 36  # 3년 = 36개월


def savefig(fig, filename: str) -> Path:
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    out = C.FIGURE_DIR / filename
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def build_return_series() -> dict:
    """
    기존 백테스트 로직을 사용하여 주요 전략과 BM의 월수익률 series를 생성한다.
    """
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()

    bts = {}

    # 고정 대칭 λ
    bts["lambda_0.1"] = X.run_lambda_backtest(returns, target_w, 0.1, 0.1)
    bts["lambda_0.3"] = X.run_lambda_backtest(returns, target_w, 0.3, 0.3)

    # 대표 비대칭 후보
    bts["asym_up0.1_down0.3"] = X.run_lambda_backtest(returns, target_w, 0.1, 0.3)

    # dynamic_v1
    sv = dyn.build_state_variables(returns, target_w)
    lam_dyn, _ = dyn.assign_lambda(sv)
    lam_dyn = lam_dyn.fillna(C.E30_RULE_V1["lambda_base"])
    bts["dynamic_v1"] = X.run_lambda_backtest(
        returns,
        target_w,
        np.nan,
        np.nan,
        lambda_series=lam_dyn,
    )

    # dynamic_v1_macro
    sv_macro = dyn_macro.build_state_variables_macro(returns, target_w)
    lam_macro, _, _ = dyn_macro.assign_lambda_macro(sv_macro)
    lam_macro = lam_macro.fillna(C.E30_RULE_V1["lambda_base"])
    bts["dynamic_v1_macro"] = X.run_lambda_backtest(
        returns,
        target_w,
        np.nan,
        np.nan,
        lambda_series=lam_macro,
    )

    start = next(iter(bts.values())).index.min()

    series = {name: bt["strategy_return_gross"].dropna() for name, bt in bts.items()}
    series["FixedBM_70_20_10"] = X.run_fixed_weight_backtest(
        returns,
        C.FIXED_BM_WEIGHTS,
        start,
    ).dropna()
    series["EW"] = X.run_fixed_weight_backtest(
        returns,
        C.EW_WEIGHTS,
        start,
    ).dropna()

    return series


def window_metrics(r: pd.Series) -> dict:
    """
    36개월 구간 하나에 대해 성과 5종 세트를 계산한다.
    """
    r = r.dropna()
    if len(r) < WINDOW:
        return {}

    cumulative_return = (1 + r).prod() - 1
    cagr = (1 + cumulative_return) ** (12 / len(r)) - 1
    vol = r.std() * np.sqrt(12)

    wealth = (1 + r).cumprod()
    drawdown = wealth / wealth.cummax() - 1
    mdd = drawdown.min()

    sharpe = (r.mean() * 12) / vol if vol != 0 else np.nan

    return {
        "cumulative_return_pct": cumulative_return * 100,
        "cagr_pct": cagr * 100,
        "vol_pct": vol * 100,
        "mdd_pct": mdd * 100,
        "sharpe": sharpe,
    }


def make_rolling_3y_table(series: dict) -> pd.DataFrame:
    """
    전략별 36개월 rolling 성과표 생성.
    window_end는 해당 36개월 구간의 마지막 월이다.
    """
    rows = []

    for strategy, r in series.items():
        r = r.dropna().sort_index()

        for end_i in range(WINDOW - 1, len(r)):
            window_r = r.iloc[end_i - WINDOW + 1:end_i + 1]
            metrics = window_metrics(window_r)

            if not metrics:
                continue

            row = {
                "strategy": strategy,
                "window_start": window_r.index[0],
                "window_end": window_r.index[-1],
                "months": len(window_r),
            }
            row.update(metrics)
            row["negative_cum_return"] = row["cumulative_return_pct"] < 0
            rows.append(row)

    df = pd.DataFrame(rows)
    return df


def plot_monthly_return_heatmap(series: dict, strategy: str) -> Path:
    """
    연도 x 월 형태의 월수익률 히트맵.
    성과가 좋은 달/나쁜 달을 한눈에 보기 위한 그림.
    """
    r = series[strategy].dropna().copy()
    df = pd.DataFrame({
        "date": r.index,
        "year": r.index.year,
        "month": r.index.month,
        "return_pct": r.values * 100,
    })

    pivot = df.pivot_table(
        index="year",
        columns="month",
        values="return_pct",
        aggfunc="sum",
    ).sort_index()

    pivot = pivot.reindex(columns=list(range(1, 13)))

    fig, ax = plt.subplots(figsize=(11, 6))

    vmax = np.nanpercentile(np.abs(pivot.values), 95)
    vmax = max(vmax, 1.0)
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)

    im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn", norm=norm)

    ax.set_title(f"{strategy} 월별 수익률 히트맵")
    ax.set_xlabel("월")
    ax.set_ylabel("연도")

    ax.set_xticks(np.arange(12))
    ax.set_xticklabels([str(i) for i in range(1, 13)])

    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels([str(y) for y in pivot.index])

    # 셀 안에 월수익률 숫자 표시
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.iloc[i, j]
            if pd.notna(val):
                ax.text(
                    j,
                    i,
                    f"{val:.1f}",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="black",
                )

    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("월수익률 (%)")

    safe_name = strategy.replace(".", "_").replace("/", "_")
    return savefig(fig, f"{C.FINAL_PREFIX}fig_monthly_return_heatmap_{safe_name}.png")


def plot_rolling_metric(rolling_df: pd.DataFrame, metric: str, title: str, ylabel: str, filename: str) -> Path:
    """
    36개월 rolling 성과지표의 전략별 시계열 비교.
    """
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

    for strategy in plot_order:
        sub = rolling_df[rolling_df["strategy"] == strategy].sort_values("window_end")
        if sub.empty:
            continue

        ax.plot(
            pd.to_datetime(sub["window_end"]),
            sub[metric],
            label=strategy,
            linewidth=2.0 if strategy in ("dynamic_v1", "dynamic_v1_macro", "FixedBM_70_20_10") else 1.3,
            linestyle="--" if strategy in ("FixedBM_70_20_10", "EW") else "-",
        )

    ax.axhline(0, linewidth=0.8)
    if hasattr(C, "OOS_START"):
        ax.axvline(pd.to_datetime(C.OOS_START), linestyle="--", linewidth=1.0, alpha=0.7)

    ax.set_title(title)
    ax.set_xlabel("3년 rolling 구간 종료월")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    return savefig(fig, filename)


def make_decision_summary(rolling_df: pd.DataFrame) -> pd.DataFrame:
    """
    전략별 3년 rolling 결과를 요약한다.
    실무 의사결정 관점:
    - 음수 누적수익률 window가 적은가?
    - 평균 CAGR이 양호한가?
    - 평균 MDD가 덜 나쁜가?
    - Sharpe가 안정적인가?
    """
    rows = []

    for strategy, sub in rolling_df.groupby("strategy"):
        sub = sub.copy()

        rows.append({
            "strategy": strategy,
            "num_windows": len(sub),
            "negative_cum_return_windows": int(sub["negative_cum_return"].sum()),
            "negative_cum_return_ratio_pct": sub["negative_cum_return"].mean() * 100,
            "avg_3y_cumulative_return_pct": sub["cumulative_return_pct"].mean(),
            "min_3y_cumulative_return_pct": sub["cumulative_return_pct"].min(),
            "avg_3y_cagr_pct": sub["cagr_pct"].mean(),
            "min_3y_cagr_pct": sub["cagr_pct"].min(),
            "avg_3y_vol_pct": sub["vol_pct"].mean(),
            "avg_3y_mdd_pct": sub["mdd_pct"].mean(),
            "worst_3y_mdd_pct": sub["mdd_pct"].min(),
            "avg_3y_sharpe": sub["sharpe"].mean(),
            "min_3y_sharpe": sub["sharpe"].min(),
        })

    out = pd.DataFrame(rows)

    # 간단한 의사결정용 정렬:
    # 1순위: 음수 누적수익률 window 적은 순
    # 2순위: 평균 3년 Sharpe 높은 순
    # 3순위: 평균 3년 MDD 덜 나쁜 순
    out = out.sort_values(
        ["negative_cum_return_windows", "avg_3y_sharpe", "avg_3y_mdd_pct"],
        ascending=[True, False, False],
    )

    return out


def plot_negative_window_count(summary: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))

    s = summary.sort_values("negative_cum_return_windows", ascending=True)

    ax.barh(s["strategy"], s["negative_cum_return_windows"])
    ax.set_title("전략별 3년 rolling 음수 누적수익률 구간 수")
    ax.set_xlabel("음수 누적수익률 window 수")
    ax.set_ylabel("전략")
    ax.grid(True, axis="x", alpha=0.25)
    ax.invert_yaxis()

    for i, (_, row) in enumerate(s.iterrows()):
        ax.text(
            row["negative_cum_return_windows"] + 0.1,
            i,
            f"{int(row['negative_cum_return_windows'])}개",
            va="center",
            fontsize=9,
        )

    return savefig(fig, f"{C.FINAL_PREFIX}fig_rolling_3y_negative_window_count.png")


def main() -> None:
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    series = build_return_series()

    # ------------------------------------------------------------
    # 1. 월별 수익률 히트맵
    # ------------------------------------------------------------
    heatmap_paths = []
    for strategy in ["dynamic_v1", "dynamic_v1_macro", "FixedBM_70_20_10"]:
        heatmap_paths.append(plot_monthly_return_heatmap(series, strategy))

    # ------------------------------------------------------------
    # 2. 3년 rolling 성과표
    # ------------------------------------------------------------
    rolling_df = make_rolling_3y_table(series)

    rolling_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}rolling_3y_performance_metrics.csv"
    rolling_df.to_csv(rolling_path, index=False, encoding="utf-8-sig")

    # ------------------------------------------------------------
    # 3. 3년 rolling 지표 그림
    # ------------------------------------------------------------
    fig_cum = plot_rolling_metric(
        rolling_df,
        "cumulative_return_pct",
        "3년 Rolling 누적수익률 비교",
        "3년 누적수익률 (%)",
        f"{C.FINAL_PREFIX}fig_rolling_3y_cumulative_return.png",
    )

    fig_cagr = plot_rolling_metric(
        rolling_df,
        "cagr_pct",
        "3년 Rolling CAGR 비교",
        "CAGR (%)",
        f"{C.FINAL_PREFIX}fig_rolling_3y_cagr.png",
    )

    fig_vol = plot_rolling_metric(
        rolling_df,
        "vol_pct",
        "3년 Rolling 연환산 변동성 비교",
        "연환산 변동성 (%)",
        f"{C.FINAL_PREFIX}fig_rolling_3y_vol.png",
    )

    fig_mdd = plot_rolling_metric(
        rolling_df,
        "mdd_pct",
        "3년 Rolling MDD 비교",
        "MDD (%)",
        f"{C.FINAL_PREFIX}fig_rolling_3y_mdd.png",
    )

    fig_sharpe = plot_rolling_metric(
        rolling_df,
        "sharpe",
        "3년 Rolling Sharpe 비교",
        "Sharpe",
        f"{C.FINAL_PREFIX}fig_rolling_3y_sharpe.png",
    )

    # ------------------------------------------------------------
    # 4. 의사결정 요약표
    # ------------------------------------------------------------
    decision = make_decision_summary(rolling_df)
    decision_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}rolling_3y_decision_summary.csv"
    decision.to_csv(decision_path, index=False, encoding="utf-8-sig")

    fig_neg = plot_negative_window_count(decision)

    print("[완료] 40_rolling_3y_performance_review")
    print("[월별 수익률 히트맵]")
    for p in heatmap_paths:
        print(f"- {p}")

    print("[3년 rolling 성과표]")
    print(f"- {rolling_path}")

    print("[3년 rolling 그림]")
    print(f"- {fig_cum}")
    print(f"- {fig_cagr}")
    print(f"- {fig_vol}")
    print(f"- {fig_mdd}")
    print(f"- {fig_sharpe}")
    print(f"- {fig_neg}")

    print("[의사결정 요약표]")
    print(f"- {decision_path}")

    print()
    print(decision.round(3).to_string(index=False))


if __name__ == "__main__":
    main()