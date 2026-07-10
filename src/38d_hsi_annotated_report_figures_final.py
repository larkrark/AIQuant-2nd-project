"""
38d_hsi_annotated_report_figures_final.py
==========================================
HSI Dynamic Allocation - Overfitting / Shuffle-Placebo Robustness Check
Final annotated figure generator for 38_report.md

Reads validated outputs from 38b (raw shuffle simulations) and 38c
(statistical validation tables) and renders 5 publication-ready,
fully annotated figures for the dynamic_v1 HSI strategy (Net10bp, OOS).

Inputs  (output/tables/):
    flex_38b_hsi_shuffle_placebo_runs.csv          -> Fig1 (null distributions, 3,000 rows)
    main_final_38b_hsi_shuffle_actual_metrics.csv  -> Fig1 (actual value markers)
    main_final_38b_simulation_progress_by_100.csv  -> Fig2, Fig3 (headline + convergence)
    main_final_38c_batch_homogeneity_test.csv      -> Fig4 (batch homogeneity / chi-sq)
    main_final_38c_overfitting_verdict_summary.csv -> Fig5 (final verdict grid)

Outputs (output/figures/):
    38d_fig1_null_distributions_oos.png
    38d_fig2_headline_percentile_pvalue.png
    38d_fig3_convergence_diagnostics.png
    38d_fig4_batch_homogeneity.png
    38d_fig5_overfitting_verdict_grid.png
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

# ----------------------------------------------------------------------
# 0. Paths & global config
# ---------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent   
TABLES = BASE / "output" / "tables"             # -> .../AIQuant-2nd-project/output/tables 

FIGS = BASE / "output" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

# Korean-capable font (Windows). Falls back silently if unavailable.
for cand in ["Malgun Gothic", "NanumGothic", "AppleGothic"]:
    if any(cand.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 130

PERIOD = "OOS"          # headline period for the report
STRATEGY = "dynamic_v1"

# (key, display_name, unit, "higher"/"lower" = better direction)
METRICS = [
    ("net10_cagr_pct",              "Net10bp CAGR",               "%", "higher"),
    ("net10_mdd_pct",                "Net10bp MDD",                "%", "higher"),  # less negative = better
    ("net10_calmar",                 "Net10bp Calmar",             "",  "higher"),
    ("net10_sharpe",                 "Net10bp Sharpe",             "",  "higher"),
    ("net10_tail_strategy_avg_pct",  "Net10bp tail-month 평균수익", "%", "higher"),
    ("net10_ann_vol_pct",            "Net10bp 연환산 변동성",       "%", "lower"),
    ("avg_annual_turnover_pct",      "평균 연환산 Turnover",        "%", "lower"),
    ("net10_win_rate_pct",           "Net10bp 월 승률",             "%", "higher"),
]
METRIC_KEYS   = [m[0] for m in METRICS]
DISPLAY_NAMES = {m[0]: m[1] for m in METRICS}
UNITS         = {m[0]: m[2] for m in METRICS}

C_NULL, C_ACTUAL = "#9AA5B1", "#D7263D"
C_PASS, C_FAIL, C_ACCENT = "#2E7D32", "#C62828", "#1B5FAE"

# ----------------------------------------------------------------------
# 1. Load data
# ----------------------------------------------------------------------
raw_runs  = pd.read_csv(TABLES / "flex_38b_hsi_shuffle_placebo_runs.csv")
actual_df = pd.read_csv(TABLES / "main_final_38b_hsi_shuffle_actual_metrics.csv")
progress  = pd.read_csv(TABLES / "main_final_38b_simulation_progress_by_100.csv")
batch_h   = pd.read_csv(TABLES / "main_final_38c_batch_homogeneity_test.csv")
verdict   = pd.read_csv(TABLES / "main_final_38c_overfitting_verdict_summary.csv")
verdict   = verdict[verdict["period"] == PERIOD].copy()

raw_oos    = raw_runs[raw_runs["period"] == PERIOD].copy()
actual_oos = actual_df[(actual_df["period"] == PERIOD) &
                        (actual_df["strategy"] == STRATEGY)].iloc[0]

max_checkpoint = progress["checkpoint"].max()
final_chk = progress[(progress["period"] == PERIOD) &
                      (progress["checkpoint"] == max_checkpoint)].set_index("metric")

n_sims = raw_oos["sim_id"].nunique()
print(f"[38d] Loaded {len(raw_runs):,} raw shuffle rows; "
      f"OOS null n={n_sims:,}; final checkpoint={max_checkpoint}")

# ========================================================================
# FIGURE 1 — Null distributions (OOS, 8 metrics) with actual overlay
# ========================================================================
fig, axes = plt.subplots(2, 4, figsize=(20, 9))
axes = axes.ravel()

for ax, (key, disp, unit, direction) in zip(axes, METRICS):
    null_vals = raw_oos[key].dropna().values
    actual_v  = actual_oos[key]
    pct  = final_chk.loc[key, "actual_advantage_percentile"]
    pval = final_chk.loc[key, "one_sided_p_value"]

    ax.hist(null_vals, bins=40, color=C_NULL, edgecolor="white", alpha=0.9,
            label=f"Null (n={len(null_vals)})")
    ax.axvline(actual_v, color=C_ACTUAL, lw=2.4,
               label=f"Actual = {actual_v:.2f}{unit}")
    ax.axvline(np.median(null_vals), color="black", lw=1, ls="--", alpha=0.6,
               label=f"Null median = {np.median(null_vals):.2f}{unit}")

    arrow = "▲ higher-better" if direction == "higher" else "▼ lower-better"
    ax.set_title(f"{disp}\npercentile={pct:.0f}%  |  p={pval:.3f}  ({arrow})",
                 fontsize=10.5, fontweight="bold")
    ax.set_xlabel(unit if unit else "value", fontsize=8.5)
    ax.set_ylabel("count", fontsize=8.5)
    ax.legend(fontsize=7)
    ax.tick_params(labelsize=8)

fig.suptitle(
    f"Fig 1. Shuffle-Placebo Null Distributions vs. Actual Strategy — OOS period "
    f"({n_sims:,} block-shuffle sims, block_size=4, cost=10bp)",
    fontsize=13.5, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(FIGS / "38d_fig1_null_distributions_oos.png", bbox_inches="tight")
plt.close(fig)
print("[38d] Fig1 saved.")

# ========================================================================
# FIGURE 2 — Headline percentile / one-sided p-value summary (final N)
# ========================================================================
summary = final_chk.loc[METRIC_KEYS].reset_index()
summary["disp"] = summary["metric"].map(DISPLAY_NAMES)
summary = summary.sort_values("actual_advantage_percentile", ascending=True)

fig, ax1 = plt.subplots(figsize=(11, 6.5))
y = np.arange(len(summary))
bar_colors = [C_PASS if p >= 90 else (C_ACCENT if p >= 70 else C_FAIL)
              for p in summary["actual_advantage_percentile"]]

ax1.barh(y, summary["actual_advantage_percentile"], color=bar_colors, height=0.6)
ax1.axvline(95, color="black", ls="--", lw=1, alpha=0.7)
ax1.text(95.5, len(summary) - 0.3, "95th pct\n(1-sided 5%)", fontsize=8, va="top")
ax1.set_yticks(y)
ax1.set_yticklabels(summary["disp"], fontsize=10)
ax1.set_xlabel("Actual value's percentile within null distribution (%)", fontsize=10)
ax1.set_xlim(0, 108)

for yi, (pct, pv) in enumerate(zip(summary["actual_advantage_percentile"],
                                    summary["one_sided_p_value"])):
    ax1.text(pct + 1.2, yi, f"{pct:.0f}%  (p={pv:.3f})", va="center", fontsize=9)

ax1.set_title(
    f"Fig 2. Headline Result — dynamic_v1 (Net10bp, OOS) vs. {n_sims:,}-run "
    f"Shuffle-Placebo Null (full sample, checkpoint={int(max_checkpoint)})",
    fontsize=12.5, fontweight="bold")
fig.tight_layout()
fig.savefig(FIGS / "38d_fig2_headline_percentile_pvalue.png", bbox_inches="tight")
plt.close(fig)
print("[38d] Fig2 saved.")

# ========================================================================
# FIGURE 3 — Convergence diagnostics (percentile stability across checkpoints)
# ========================================================================
prog_oos = progress[progress["period"] == PERIOD].copy()
checkpoints = sorted(prog_oos["checkpoint"].unique())

fig, axes = plt.subplots(2, 4, figsize=(20, 9), sharex=True)
axes = axes.ravel()

for ax, (key, disp, unit, direction) in zip(axes, METRICS):
    sub = prog_oos[prog_oos["metric"] == key].sort_values("checkpoint")
    ax.plot(sub["checkpoint"], sub["actual_advantage_percentile"],
            marker="o", ms=4, color=C_ACCENT, lw=1.8)
    ax.axhline(95, color="black", ls="--", lw=1, alpha=0.5)
    ax.fill_between(sub["checkpoint"], 90, 100, color=C_PASS, alpha=0.06)
    mid = len(sub) // 2
    gap = sub["actual_advantage_percentile"].iloc[-1] - sub["actual_advantage_percentile"].iloc[mid]
    ax.set_title(f"{disp}\nlate-window drift={gap:+.1f}pp", fontsize=10, fontweight="bold")
    ax.set_ylim(0, 105)
    ax.tick_params(labelsize=8)
    ax.set_xlabel("simulations run (n)", fontsize=8)
    ax.set_ylabel("percentile (%)", fontsize=8)

fig.suptitle(
    "Fig 3. Convergence Diagnostics — Percentile Estimate vs. Number of Shuffle "
    f"Simulations (checkpoints every 100, up to {int(max(checkpoints)):,}), OOS period",
    fontsize=13, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(FIGS / "38d_fig3_convergence_diagnostics.png", bbox_inches="tight")
plt.close(fig)
print("[38d] Fig3 saved.")

# ========================================================================
# FIGURE 4 — Batch homogeneity (chi-square across 10 batches of 100 sims)
# ========================================================================
fig, axes = plt.subplots(2, 4, figsize=(20, 9), sharex=True)
axes = axes.ravel()

for ax, (key, disp, unit, direction) in zip(axes, METRICS):
    sub = batch_h[batch_h["metric"] == key].sort_values("batch")
    if sub.empty:
        ax.axis("off")
        continue
    pooled = sub["pooled_phat_pct"].iloc[0]
    chi2p = sub["chi2_p_value"].iloc[0]
    ax.bar(sub["batch"], sub["phat_pct"], color=C_ACCENT, alpha=0.85, width=0.6)
    ax.axhline(pooled, color=C_ACTUAL, lw=1.6, ls="--",
           label=r"pooled $\hat{p}$" + f"={pooled:.1f}%")

    ax.set_title(f"{disp}\nχ² p-value={chi2p:.3f}", fontsize=10, fontweight="bold")
    ax.set_xlabel("batch (100 sims each)", fontsize=8)
    ax.set_ylabel("null 'beats actual'\n" + r"rate $\hat{p}$ (%)", fontsize=8)
    ax.set_xticks(sub["batch"])
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7, loc="upper right")

fig.suptitle(
    "Fig 4. Batch Homogeneity Test — Stability of Null-Beats-Actual Rate Across "
    "10 Sequential Batches of 100 Simulations (χ² test), OOS period",
    fontsize=13, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(FIGS / "38d_fig4_batch_homogeneity.png", bbox_inches="tight")
plt.close(fig)
print("[38d] Fig4 saved.")

# ========================================================================
# FIGURE 5 — Final overfitting-verdict traffic-light grid
# ========================================================================
v = verdict.set_index("metric").loc[METRIC_KEYS].reset_index()
v["disp"] = v["metric"].map(DISPLAY_NAMES)

checks = [
    ("batch_homogeneity_pass", "Batch\nHomogeneity", "chi2_p_value"),
    ("split_half_pass",        "Split-Half\nStability", "split_half_p_value"),
    ("convergence_pass",       "Convergence\nStability", "max_late_convergence_gap_pct_points"),
    ("overall_no_overfitting_evidence", "Overall\nVerdict", None),
]

fig, ax = plt.subplots(figsize=(10, 7))
n_rows, n_cols = len(v), len(checks)

for i, row in v.iterrows():
    for j, (col, label, detail_col) in enumerate(checks):
        passed = bool(row[col])
        color = C_PASS if passed else C_FAIL
        mark = "OK" if passed else "FAIL"
        ax.add_patch(plt.Rectangle((j, n_rows - 1 - i), 1, 1,
                                    facecolor=color, alpha=0.85, edgecolor="white"))
        detail = ""
        if detail_col is not None and detail_col in row:
            dv = row[detail_col]
            detail = f"\n({dv:.3f})" if isinstance(dv, float) else f"\n({dv})"
        ax.text(j + 0.5, n_rows - 1 - i + 0.5, f"{mark}{detail}",
                ha="center", va="center", fontsize=9.5, color="white", fontweight="bold")

ax.set_xlim(0, n_cols)
ax.set_ylim(0, n_rows)
ax.set_xticks(np.arange(n_cols) + 0.5)
ax.set_xticklabels([c[1] for c in checks], fontsize=10)
ax.set_yticks(np.arange(n_rows) + 0.5)
ax.set_yticklabels(v["disp"][::-1], fontsize=10)
ax.set_title(
    "Fig 5. Overfitting-Robustness Verdict Grid — dynamic_v1 (Net10bp, OOS)\n"
    f"All {n_rows} metrics: "
    f"{'PASS' if v['overall_no_overfitting_evidence'].all() else 'MIXED'} on every robustness check",
    fontsize=12.5, fontweight="bold")
ax.set_aspect("equal")
for spine in ax.spines.values():
    spine.set_visible(False)
fig.tight_layout()
fig.savefig(FIGS / "38d_fig5_overfitting_verdict_grid.png", bbox_inches="tight")
plt.close(fig)
print("[38d] Fig5 saved.")

print("\n[38d] All 5 annotated figures generated in:", FIGS.resolve())
