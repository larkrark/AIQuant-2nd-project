# -*- coding: utf-8 -*-
"""
28_lambda_response_curve.py — E28 단일 λ 반응곡선 (재현·기준선)

수행 (v2 §3.5):
1) 사전 고정 grid λ ∈ {0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0} (+0.05 보조)
2) 동일 목표비중·동일 수익률로 백테스트
3) CAGR·MDD·Sharpe·Sortino·Calmar·Turnover·비용차감 성과
4) 게이트 ①: λ=0.1/0.3/1.0 결과를 config.BASELINE_REFERENCE 와 대조 출력

출력:
  output/tables/main_final_lambda_response_metrics.csv
  output/tables/flex_lambda_response_timeseries.csv
  output/figures/main_final_fig_e28_response_curve.png
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
import common as X


def main(fine: bool = False) -> None:
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()

    grid = C.E28_LAMBDA_GRID_FINE if fine else C.E28_LAMBDA_GRID
    metric_rows, ts_frames = [], []

    for lam in grid:
        bt = X.run_lambda_backtest(returns, target_w, lambda_up=lam, lambda_down=lam)
        m = X.perf_metrics(bt["strategy_return_gross"], bt["turnover"], f"lambda_{lam:.2f}")
        m["lambda"] = lam
        # 비용 민감도 (게이트 ③)
        for bps in C.COST_BPS_GRID:
            net = bt["strategy_return_gross"] - bt["turnover"] * (bps / 10000.0)
            m[f"cagr_net_{bps}bp"] = ((1 + net).prod() ** (12 / len(net)) - 1) * 100
        metric_rows.append(m)
        ts = bt[["strategy_return_gross", "turnover", f"w_{C.RISK_TICKER}"]].copy()
        ts["lambda"] = lam
        ts_frames.append(ts.reset_index())

    metrics = pd.DataFrame(metric_rows).sort_values("lambda")
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(C.TABLE_DIR / f"{C.FINAL_PREFIX}lambda_response_metrics.csv",
                   index=False, encoding="utf-8-sig")
    pd.concat(ts_frames).to_csv(C.TABLE_DIR / f"{C.INTERIM_PREFIX}lambda_response_timeseries.csv",
                                index=False, encoding="utf-8-sig")

    # 게이트 ① 재현·검산 대조
    print("[게이트 ① 재현·검산] 기존 기준선 대비 (config.BASELINE_REFERENCE):")
    for conv, ref in C.BASELINE_REFERENCE.items():
        for key, lam in (("lambda_0.1", 0.1), ("lambda_0.3", 0.3), ("hsi_baseline", 1.0)):
            row = metrics.loc[(metrics["lambda"] - lam).abs() < 1e-9]
            if row.empty:
                continue
            got_cagr, got_mdd = row["cagr_pct"].iloc[0], row["mdd_pct"].iloc[0]
            print(f"  {conv} {key}: 기준 CAGR {ref[key]['cagr']:.2f} / MDD {ref[key]['mdd']:.2f}"
                  f"  ↔ 재현 CAGR {got_cagr:.2f} / MDD {got_mdd:.2f}"
                  f"  (ΔCAGR {got_cagr - ref[key]['cagr']:+.2f}%p)")

    # 반응곡선 그림
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, col, name in zip(axes, ["cagr_pct", "mdd_pct", "avg_turnover_pct"],
                             ["CAGR %", "MDD %", "Avg Turnover %"]):
        ax.plot(metrics["lambda"], metrics[col], marker="o")
        for lam in (0.1, 0.3):
            ax.axvline(lam, linestyle="--", linewidth=1, color="grey")
        ax.set_xlabel("lambda"); ax.set_title(name)
    fig.suptitle("E28. Lambda response curve (dashed: current candidates 0.1 / 0.3)")
    fig.tight_layout()
    fig.savefig(C.FIGURE_DIR / f"{C.FINAL_PREFIX}fig_e28_response_curve.png",
                dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("[완료] E28")
    print(metrics[["lambda", "cagr_pct", "ann_vol_pct", "mdd_pct",
                   "sharpe", "calmar", "avg_turnover_pct", "max_turnover_pct"]]
          .round(2).to_string(index=False))


if __name__ == "__main__":
    main(fine="--fine" in sys.argv)
