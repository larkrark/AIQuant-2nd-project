# -*- coding: utf-8 -*-
"""
29_asymmetric_lambda_grid.py — E29 비대칭 λ_up/λ_down grid search (핵심 실험)

수행 (v2 §3.6):
- λ_up, λ_down ∈ {0.1, 0.2, 0.3, 0.5} 16셀 전량 백테스트 (게이트 ② full-grid: 필터 전 전량 기록)
- 대각선(λ_up=λ_down)은 대칭 참조 → E28과 반드시 일치 (엔진 동일성 검산)
- 판단 지표: Calmar·MDD·Turnover·비용차감 성과 (단일 점수 금지)
- 인접 셀 안정성: 각 셀에 대해 인접 셀 Calmar 최저치를 함께 기록 (고립 최고점 배제 근거)
- tail-month 방어(069500 하위 10% 손실월) 기록 (H2 검증 근거)

출력:
  output/tables/main_final_asymmetric_lambda_grid.csv
  output/figures/main_final_fig_e29_heatmap.png
"""

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


def neighbor_min(df: pd.DataFrame, ups, downs, col: str) -> pd.Series:
    """각 (λ_up, λ_down) 셀의 상하좌우 인접 셀 중 col 최저값."""
    grid = df.pivot(index="lambda_down", columns="lambda_up", values=col)
    vals = {}
    for i, d in enumerate(downs):
        for j, u in enumerate(ups):
            neigh = []
            if i > 0: neigh.append(grid.iloc[i - 1, j])
            if i < len(downs) - 1: neigh.append(grid.iloc[i + 1, j])
            if j > 0: neigh.append(grid.iloc[i, j - 1])
            if j < len(ups) - 1: neigh.append(grid.iloc[i, j + 1])
            vals[(u, d)] = np.nanmin(neigh) if neigh else np.nan
    return df.apply(lambda r: vals[(r["lambda_up"], r["lambda_down"])], axis=1)


def main() -> None:
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()
    risk_r = returns[C.RISK_TICKER]

    rows = []
    for lu in C.E29_LAMBDA_UP_GRID:
        for ld in C.E29_LAMBDA_DOWN_GRID:
            bt = X.run_lambda_backtest(returns, target_w, lambda_up=lu, lambda_down=ld)
            m = X.perf_metrics(bt["strategy_return_gross"], bt["turnover"],
                               f"up{lu:.1f}_down{ld:.1f}")
            m["lambda_up"], m["lambda_down"] = lu, ld
            m["is_diagonal"] = (lu == ld)
            m["region"] = ("defensive(down>up)" if ld > lu
                           else "diagonal" if ld == lu else "aggressive(up>down)")
            # 비용차감 CAGR (게이트 ③)
            for bps in C.COST_BPS_GRID:
                net = bt["strategy_return_gross"] - bt["turnover"] * (bps / 10000.0)
                m[f"cagr_net_{bps}bp"] = ((1 + net).prod() ** (12 / len(net)) - 1) * 100
            # tail-month 방어 (H2)
            tm = X.tail_month_defense(bt["strategy_return_gross"], risk_r)
            m["tail_strategy_avg_pct"] = tm["strategy_avg_pct"]
            m["tail_capture_ratio"] = tm["capture_ratio"]
            rows.append(m)

    grid = pd.DataFrame(rows)
    grid["neighbor_min_calmar"] = neighbor_min(
        grid, C.E29_LAMBDA_UP_GRID, C.E29_LAMBDA_DOWN_GRID, "calmar")

    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    grid.to_csv(C.TABLE_DIR / f"{C.FINAL_PREFIX}asymmetric_lambda_grid.csv",
                index=False, encoding="utf-8-sig")

    # heatmaps
    fig, axes = plt.subplots(1, 4, figsize=(18, 4))
    for ax, col, name in zip(
            axes, ["cagr_pct", "mdd_pct", "calmar", "avg_turnover_pct"],
            ["CAGR %", "MDD %", "Calmar", "Avg Turnover %"]):
        pv = grid.pivot(index="lambda_down", columns="lambda_up", values=col)
        im = ax.imshow(pv.values, origin="lower", aspect="auto")
        ax.set_xticks(range(len(pv.columns)), [f"{v:.1f}" for v in pv.columns])
        ax.set_yticks(range(len(pv.index)), [f"{v:.1f}" for v in pv.index])
        ax.set_xlabel("lambda_up"); ax.set_ylabel("lambda_down"); ax.set_title(name)
        for (i, j), v in np.ndenumerate(pv.values):
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8, color="white")
        fig.colorbar(im, ax=ax, shrink=0.8)
    fig.suptitle("E29. Asymmetric lambda grid (diagonal = symmetric reference)")
    fig.tight_layout()
    fig.savefig(C.FIGURE_DIR / f"{C.FINAL_PREFIX}fig_e29_heatmap.png",
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 대각선 = 대칭 검산 안내
    print("[완료] E29 — full grid 16셀 (필터 전 전량 기록, 게이트 ②)")
    show = ["lambda_up", "lambda_down", "region", "cagr_pct", "mdd_pct",
            "calmar", "avg_turnover_pct", "tail_strategy_avg_pct", "neighbor_min_calmar"]
    print(grid[show].round(3).to_string(index=False))
    print("\n※ 대각선 행은 E28의 동일 λ 결과와 일치해야 합니다(엔진 동일성 검산).")


if __name__ == "__main__":
    main()
