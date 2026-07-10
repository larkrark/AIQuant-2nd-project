# -*- coding: utf-8 -*-
"""
33_report_outputs.py — 결과보고서용 산출물 (팀 요구 반영)

산출:
1) 리밸런싱 일자별 포트폴리오 구성 내역
   → main_final_portfolio_composition_{전략}.csv
     (signal_date, apply_date, hsi_state, w_069500/114260/153130, λ_used, direction, turnover)
2) IS / OOS 구간별: 전략 vs Fixed 70/20/10 BM vs EW 의
   누적수익률·연변동성·MDD·Sharpe 비교표 + 차트
   → main_final_is_oos_performance_table.csv
   → main_final_fig_cumret_IS.png / _OOS.png / _FULL.png
   → main_final_fig_drawdown_FULL.png

대상 전략(기본): 대칭 λ=0.1/0.3 + 비대칭 대표(31번 CANDIDATES와 동일 소스) + dynamic_v1
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

dyn = importlib.import_module("30_dynamic_lambda_rule_v1")
dyn_macro = importlib.import_module("30_dynamic_lambda_rule_v1_macro")
# 차트·구성내역에 올릴 전략 (E29/32 결과 확인 후 조정 가능 — 조정 이력 주석 기록)
STRATEGIES = [
    ("lambda_0.1", 0.10, 0.10),
    ("lambda_0.3", 0.30, 0.30),
    ("asym_up0.1_down0.3", 0.10, 0.30),
    ("dynamic_v1", None, None),
    ("dynamic_v1_macro", None, None),
]
SEGMENTS = {"IS": (None,), "OOS": (None,), "FULL": (None,)}  # 경계는 config 사용


def segment_bounds(name):
    if name == "IS":
        return C.IS_START, C.IS_END
    if name == "OOS":
        return C.OOS_START, C.OOS_END
    return None, None


def seg_slice(s: pd.Series, name: str) -> pd.Series:
    a, b = segment_bounds(name)
    return s if a is None else s.loc[a:b]


def main() -> None:
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()

    # 백테스트 수행
    bts, series = {}, {}
    for name, lu, ld in STRATEGIES:
        if name == "dynamic_v1":
            sv = dyn.build_state_variables(returns, target_w)
            lam_t, cond = dyn.assign_lambda(sv)
            lam_t = lam_t.fillna(C.E30_RULE_V1["lambda_base"])

            bt = X.run_lambda_backtest(
                returns,
                target_w,
                np.nan,
                np.nan,
                lambda_series=lam_t,
            )

        elif name == "dynamic_v1_macro":
            sv_macro = dyn_macro.build_state_variables_macro(returns, target_w)
            lam_macro, cond_macro, reason_macro = dyn_macro.assign_lambda_macro(sv_macro)
            lam_macro = lam_macro.fillna(C.E30_RULE_V1["lambda_base"])

            bt = X.run_lambda_backtest(
                returns,
                target_w,
                np.nan,
                np.nan,
                lambda_series=lam_macro,
            )

        else:
            bt = X.run_lambda_backtest(returns, target_w, lu, ld)

        bts[name] = bt
        series[name] = bt["strategy_return_gross"]

    start = next(iter(bts.values())).index.min()
    series["FixedBM_70_20_10"] = X.run_fixed_weight_backtest(returns, C.FIXED_BM_WEIGHTS, start)
    series["EW"] = X.run_fixed_weight_backtest(returns, C.EW_WEIGHTS, start)

    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    # --- 1) 리밸런싱 일자별 구성 내역 ---
    state_map = target_w["hsi_state"] if "hsi_state" in target_w.columns else None
    for name, bt in bts.items():
        comp = bt[["signal_date"] + [f"w_{t}" for t in C.TICKERS]
                  + ["lambda_used", "direction", "turnover"]].copy()
        if state_map is not None:
            comp["hsi_state"] = state_map.reindex(comp["signal_date"]).values
        comp.to_csv(
            C.TABLE_DIR / f"{C.FINAL_PREFIX}portfolio_composition_{name}.csv",
            encoding="utf-8-sig")

    # --- 2) IS/OOS 성과표 ---
    rows = []
    for name, r in series.items():
        for seg in ("IS", "OOS", "FULL"):
            rr = seg_slice(r, seg).dropna()
            if len(rr) < 6:
                continue
            m = X.perf_metrics(rr, label=name)
            m["segment"] = seg
            m["cum_return_pct"] = ((1 + rr).prod() - 1) * 100
            rows.append(m)
    table = pd.DataFrame(rows)[
        ["strategy", "segment", "months", "cum_return_pct", "cagr_pct",
         "ann_vol_pct", "mdd_pct", "sharpe", "sharpe_geom", "calmar", "win_rate_pct"]]
    table.to_csv(C.TABLE_DIR / f"{C.FINAL_PREFIX}is_oos_performance_table.csv",
                 index=False, encoding="utf-8-sig")

    # --- 3) 차트: 누적수익률 (IS / OOS / FULL) + drawdown(FULL) ---
    for seg in ("IS", "OOS", "FULL"):
        fig, ax = plt.subplots(figsize=(11, 5))
        for name, r in series.items():
            rr = seg_slice(r, seg).dropna()
            if len(rr) < 6:
                continue
            ax.plot(rr.index, (1 + rr).cumprod(), label=name,
                    linewidth=2 if "BM" in name or name == "EW" else 1.4,
                    linestyle="--" if name in ("FixedBM_70_20_10", "EW") else "-")
        ax.axhline(1, linewidth=0.8, color="grey")
        ax.set_title(f"Cumulative return — {seg}"
                     + ("" if seg == "FULL" else f" ({segment_bounds(seg)[0][:7]}~{segment_bounds(seg)[1][:7]})"))
        ax.set_ylabel("Cumulative index"); ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(C.FIGURE_DIR / f"{C.FINAL_PREFIX}fig_cumret_{seg}.png",
                    dpi=150, bbox_inches="tight")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 4))
    for name, r in series.items():
        idx = (1 + r.dropna()).cumprod()
        ax.plot(idx.index, idx / idx.cummax() - 1, label=name,
                linestyle="--" if name in ("FixedBM_70_20_10", "EW") else "-")
    ax.set_title("Drawdown — FULL"); ax.set_ylabel("Drawdown"); ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(C.FIGURE_DIR / f"{C.FINAL_PREFIX}fig_drawdown_FULL.png",
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("[완료] 33_report_outputs")
    print(table.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
