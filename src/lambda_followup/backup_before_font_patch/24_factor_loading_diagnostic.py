# -*- coding: utf-8 -*-
"""
24_factor_loading_diagnostic.py — E24 팩터로딩 진단

회귀식 (v2 §3.4):
  (a) R_strategy,t = α + Σ βk·Factor_k,t + ε
  (b) R_strategy,t − R_FixedBM,t = α + Σ βk·Factor_k,t + ε
전체기간 단일 회귀 + 36개월 rolling.

입력(팀 확정 필요 [D-C3]):
  data/processed/factor_inputs_monthly.csv
  index=월말 Date, 열: Market, Bond, Momentum, Volatility, MacroRisk
  (decimal 수익률 또는 z-score. PIT·전월 lag는 데이터 생성 단계에서 처리)

강의요건 보고서 §3.3 반영: 본 스크립트는 후속 실험용이지만 최종 후보(λ=0.1/0.3)에
먼저 실행해 '본편' 팩터 절로 승격하는 용도를 겸한다.

출력:
  output/tables/main_final_factor_loading_summary.csv
  output/tables/flex_factor_loading_timeseries.csv
  output/figures/main_final_fig_e24_rolling_beta.png
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

FACTOR_COLS = ["Market", "Bond", "Momentum", "Volatility", "MacroRisk"]
ROLL_WINDOW = 36


def ols_with_t(y: pd.Series, Xf: pd.DataFrame):
    """단순 OLS (절편 포함) — β, t값, R² 반환."""
    df = pd.concat([y, Xf], axis=1).dropna()
    yy = df.iloc[:, 0].values
    XX = np.column_stack([np.ones(len(df)), df.iloc[:, 1:].values])
    beta, res, *_ = np.linalg.lstsq(XX, yy, rcond=None)
    resid = yy - XX @ beta
    dof = len(yy) - XX.shape[1]
    sigma2 = resid @ resid / dof
    cov = sigma2 * np.linalg.inv(XX.T @ XX)
    tvals = beta / np.sqrt(np.diag(cov))
    r2 = 1 - (resid @ resid) / ((yy - yy.mean()) @ (yy - yy.mean()))
    names = ["alpha"] + list(df.columns[1:])
    return dict(zip(names, beta)), dict(zip(names, tvals)), r2, len(df)


def main() -> None:
    if not C.FACTORS_FILE.exists():
        print(f"[건너뜀] 팩터 파일 미확보: {C.FACTORS_FILE}")
        print(f"필요 열: {FACTOR_COLS} (index=월말 Date). [D-C3] 대용치 확정 후 실행하세요.")
        return

    factors = pd.read_csv(C.FACTORS_FILE, index_col=0, parse_dates=True).sort_index()
    missing = [c for c in FACTOR_COLS if c not in factors.columns]
    if missing:
        print(f"[건너뜀] 팩터 열 부족: {missing}. 확보 후 재실행하세요.")
        return
    factors = factors[FACTOR_COLS]

    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()
    bm = X.run_fixed_weight_backtest(returns, C.FIXED_BM_WEIGHTS)

    strategies = {
        "FixedBM": bm,
        "EW": X.run_fixed_weight_backtest(returns, C.EW_WEIGHTS),
        "HSI_baseline": X.run_lambda_backtest(returns, target_w, 1.0, 1.0)["strategy_return_gross"],
        "lambda_0.1": X.run_lambda_backtest(returns, target_w, 0.1, 0.1)["strategy_return_gross"],
        "lambda_0.3": X.run_lambda_backtest(returns, target_w, 0.3, 0.3)["strategy_return_gross"],
    }

    summary_rows, ts_frames = [], []
    for name, r in strategies.items():
        for dep_label, y in (("raw", r), ("excess_vs_BM", r - bm.reindex(r.index))):
            beta, tval, r2, n = ols_with_t(y, factors)
            row = {"strategy": name, "dependent": dep_label, "n": n, "r2": r2}
            for k in ["alpha"] + FACTOR_COLS:
                row[f"beta_{k}"] = beta.get(k, np.nan)
                row[f"t_{k}"] = tval.get(k, np.nan)
            summary_rows.append(row)

        # 36개월 rolling β (raw 기준)
        joined = pd.concat([r.rename("y"), factors], axis=1).dropna()
        for end in range(ROLL_WINDOW, len(joined) + 1):
            win = joined.iloc[end - ROLL_WINDOW:end]
            beta, _, _, _ = ols_with_t(win["y"], win[FACTOR_COLS])
            ts_frames.append({"strategy": name, "date": win.index[-1],
                              **{k: beta.get(k, np.nan) for k in FACTOR_COLS}})

    summary = pd.DataFrame(summary_rows)
    ts = pd.DataFrame(ts_frames)
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(C.TABLE_DIR / f"{C.FINAL_PREFIX}factor_loading_summary.csv",
                   index=False, encoding="utf-8-sig")
    ts.to_csv(C.TABLE_DIR / f"{C.INTERIM_PREFIX}factor_loading_timeseries.csv",
              index=False, encoding="utf-8-sig")

    fig, axes = plt.subplots(len(FACTOR_COLS), 1, figsize=(11, 3 * len(FACTOR_COLS)), sharex=True)
    for ax, f in zip(axes, FACTOR_COLS):
        for name in ("lambda_0.1", "lambda_0.3", "HSI_baseline"):
            seg = ts[ts["strategy"] == name]
            ax.plot(seg["date"], seg[f], label=name)
        ax.axhline(0, linewidth=1, color="grey")
        ax.set_ylabel(f"β {f}")
    axes[0].legend(); axes[0].set_title("E24. 36-month rolling factor loadings")
    fig.tight_layout()
    fig.savefig(C.FIGURE_DIR / f"{C.FINAL_PREFIX}fig_e24_rolling_beta.png",
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("[완료] E24")
    print(summary[["strategy", "dependent", "r2", "beta_alpha", "beta_Volatility",
                   "t_Volatility"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
