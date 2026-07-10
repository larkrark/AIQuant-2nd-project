# -*- coding: utf-8 -*-
"""
37_lambda_path_macro_difference.py

목적
----
dynamic_v1과 dynamic_v1_macro의 차이가 포트폴리오 구성비중 그림에서
크게 보이지 않는 이유를 설명하기 위한 보조 그림을 생성한다.

생성 산출물
----------
output/figures/main_final_fig_lambda_path_dynamic_vs_macro.png
output/figures/main_final_fig_risk_weight_difference_macro_minus_dynamic.png
output/tables/main_final_lambda_path_macro_difference_summary.csv
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


def main() -> None:
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()

    # ------------------------------------------------------------
    # 1. dynamic_v1 λ 경로
    # ------------------------------------------------------------
    sv = dyn.build_state_variables(returns, target_w)
    lam_dyn, cond_dyn = dyn.assign_lambda(sv)
    lam_dyn = lam_dyn.fillna(C.E30_RULE_V1["lambda_base"])

    # ------------------------------------------------------------
    # 2. dynamic_v1_macro λ 경로
    # ------------------------------------------------------------
    sv_macro = dyn_macro.build_state_variables_macro(returns, target_w)
    lam_macro, cond_macro, reason_macro = dyn_macro.assign_lambda_macro(sv_macro)
    lam_macro = lam_macro.fillna(C.E30_RULE_V1["lambda_base"])

    # index 정렬
    idx = lam_dyn.index.union(lam_macro.index).sort_values()
    lam_dyn = lam_dyn.reindex(idx).ffill()
    lam_macro = lam_macro.reindex(idx).ffill()

    path_df = pd.DataFrame({
        "lambda_dynamic_v1": lam_dyn,
        "lambda_dynamic_v1_macro": lam_macro,
        "lambda_diff_macro_minus_dynamic": lam_macro - lam_dyn,
    })

    # ------------------------------------------------------------
    # 3. 월별 λ 경로 비교 그림
    # ------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 4.8))

    ax.step(
        path_df.index,
        path_df["lambda_dynamic_v1"],
        where="post",
        label="dynamic_v1",
        linewidth=1.8,
    )
    ax.step(
        path_df.index,
        path_df["lambda_dynamic_v1_macro"],
        where="post",
        label="dynamic_v1_macro",
        linewidth=1.8,
        linestyle="--",
    )

    if hasattr(C, "OOS_START"):
        ax.axvline(pd.to_datetime(C.OOS_START), linestyle="--", linewidth=1.0, alpha=0.7)

    ax.set_title("dynamic_v1과 dynamic_v1_macro의 월별 λ 경로 비교", fontsize=13, pad=12)
    ax.set_ylabel("λ")
    ax.set_xlabel("적용월")
    ax.set_ylim(0, 0.55)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=9)

    lambda_fig = savefig(fig, f"{C.FINAL_PREFIX}fig_lambda_path_dynamic_vs_macro.png")

    # ------------------------------------------------------------
    # 4. 실제 위험자산 비중 차이 확인
    # ------------------------------------------------------------
    bt_dyn = X.run_lambda_backtest(
        returns,
        target_w,
        np.nan,
        np.nan,
        lambda_series=lam_dyn,
    )

    bt_macro = X.run_lambda_backtest(
        returns,
        target_w,
        np.nan,
        np.nan,
        lambda_series=lam_macro,
    )

    risk_col = f"w_{C.RISK_TICKER}"
    common_idx = bt_dyn.index.intersection(bt_macro.index)

    diff_pp = (
        bt_macro.loc[common_idx, risk_col]
        - bt_dyn.loc[common_idx, risk_col]
    ) * 100

    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.plot(diff_pp.index, diff_pp, linewidth=1.5)
    ax.axhline(0, linewidth=0.8)

    if hasattr(C, "OOS_START"):
        ax.axvline(pd.to_datetime(C.OOS_START), linestyle="--", linewidth=1.0, alpha=0.7)

    ax.set_title("dynamic_v1_macro - dynamic_v1 위험자산 비중 차이", fontsize=13, pad=12)
    ax.set_ylabel("069500 비중 차이 (%p)")
    ax.set_xlabel("적용월")
    ax.grid(True, alpha=0.25)

    diff_fig = savefig(fig, f"{C.FINAL_PREFIX}fig_risk_weight_difference_macro_minus_dynamic.png")

    # ------------------------------------------------------------
    # 5. 요약표
    # ------------------------------------------------------------
    lambda_diff_months = int((path_df["lambda_diff_macro_minus_dynamic"].abs() > 1e-12).sum())
    lambda_total_months = int(path_df["lambda_diff_macro_minus_dynamic"].notna().sum())

    summary = pd.DataFrame([{
        "months_total": lambda_total_months,
        "months_lambda_diff": lambda_diff_months,
        "lambda_diff_ratio_pct": lambda_diff_months / lambda_total_months * 100 if lambda_total_months else np.nan,
        "avg_lambda_dynamic_v1": path_df["lambda_dynamic_v1"].mean(),
        "avg_lambda_dynamic_v1_macro": path_df["lambda_dynamic_v1_macro"].mean(),
        "mean_abs_risk_weight_diff_pp": diff_pp.abs().mean(),
        "max_abs_risk_weight_diff_pp": diff_pp.abs().max(),
        "avg_turnover_dynamic_v1_pct": bt_dyn["turnover"].mean() * 100,
        "avg_turnover_dynamic_v1_macro_pct": bt_macro["turnover"].mean() * 100,
    }])

    summary_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}lambda_path_macro_difference_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print("[완료] 37_lambda_path_macro_difference")
    print(f"- lambda path fig: {lambda_fig}")
    print(f"- risk weight diff fig: {diff_fig}")
    print(f"- summary table: {summary_path}")
    print(summary.round(4).to_string(index=False))


if __name__ == "__main__":
    main()