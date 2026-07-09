"""
32_main_v2_plot_daily_rebalance_etf_detail.py

목적
----
31_main_v2_daily_rebalance_backtest_etf_detail.py 가 만든 성과표(CSV)를
그래프로 시각화한다. 새 산출물만 생성하며 기존 파일은 건드리지 않는다.

입력 (31번 산출물)
----
output/tables/main_v2_daily_backtest_timeseries_{method}.csv
output/tables/main_v2_daily_performance_summary.csv
output/tables/main_v2_daily_etf_summary_{method}.csv
output/tables/main_v2_daily_etf_detail_monthly_{method}.csv

출력 (모두 신규)
----
output/figures/main_v2_daily_fig1_cumulative_return.png   (누적수익률 시계열)
output/figures/main_v2_daily_fig2_drawdown.png            (드로다운 언더워터)
output/figures/main_v2_daily_fig3_strategy_metrics.png    (전략 성과지표 비교 바)
output/figures/main_v2_daily_fig4_etf_contribution.png    (ETF 총기여도 분해 바)
output/figures/main_v2_daily_fig5_monthly_heatmap.png     (전략 월별 수익률 히트맵)

형식 선택 근거
----
- 누적수익률/드로다운: 시간 축이 핵심 → 폭 넓은 라인/언더워터 차트.
- 성과지표: 전략 간 상대비교 → 그룹 막대(%지표와 비율지표 축 분리).
- ETF 기여도: 구성요소 분해 → ETF별 그룹 막대(EW vs HSI overlay).
- 월별 수익률: 계절성/구간 확인 → 연×월 히트맵.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ------------------------------------------------------------
# 경로 & 한글 폰트
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
FIGURE_DIR = PROJECT_ROOT / "output" / "figures"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def setup_korean_font() -> None:
    for cand in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]:
        if Path(cand).exists():
            try:
                font_manager.fontManager.addfont(cand)
                name = font_manager.FontProperties(fname=cand).get_name()
                plt.rcParams["font.family"] = name
                break
            except Exception:
                continue
    plt.rcParams["axes.unicode_minus"] = False


setup_korean_font()

ASSETS = ["069500", "114260", "153130"]
ETF_LABEL = {"069500": "069500 주식", "114260": "114260 채권", "153130": "153130 현금성"}
COLORS = {
    "EW": "#888888",
    "overlay_rank": "#1f77b4",
    "overlay_zscore": "#d62728",
}
LABEL = {
    "EW": "EW (동일가중 BM)",
    "overlay_rank": "HSI overlay (rank)",
    "overlay_zscore": "HSI overlay (zscore)",
}


def load_timeseries():
    frames = {}
    for m in ["rank", "zscore"]:
        df = pd.read_csv(TABLE_DIR / f"main_v2_daily_backtest_timeseries_{m}.csv")
        df["Date"] = pd.to_datetime(df["Date"])
        frames[m] = df
    return frames


def _series(frames, key):
    """key ∈ {EW, overlay_rank, overlay_zscore} → (Date, cum, dd, daily_ret)."""
    if key == "EW":
        df = frames["rank"]
        g = df[df["strategy"] == "EW"]
    else:
        m = key.split("_")[1]
        df = frames[m]
        g = df[df["strategy"] == "HSI_state5_overlay"]
    g = g.sort_values("Date")
    return g["Date"].values, g["cumulative_return"].values, g["drawdown"].values, g["daily_return"].values


# ------------------------------------------------------------
# Fig1. 누적수익률 시계열
# ------------------------------------------------------------
def plot_cumulative(frames):
    fig, ax = plt.subplots(figsize=(12, 5.5))
    for key in ["EW", "overlay_rank", "overlay_zscore"]:
        d, cum, _, _ = _series(frames, key)
        ax.plot(d, cum, label=LABEL[key], color=COLORS[key], lw=1.6)
    ax.set_title("일별 리밸런싱 누적수익률 비교 (초기자본=1.0)", fontsize=14, fontweight="bold")
    ax.set_ylabel("누적 성장배수 (배)")
    ax.set_xlabel("날짜")
    ax.axhline(1.0, color="black", lw=0.7, ls="--", alpha=0.5)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", framealpha=0.9)
    fig.tight_layout()
    p = FIGURE_DIR / "main_v2_daily_fig1_cumulative_return.png"
    fig.savefig(p, dpi=130); plt.close(fig)
    print(f"- 저장: {p}")


# ------------------------------------------------------------
# Fig2. 드로다운 언더워터
# ------------------------------------------------------------
def plot_drawdown(frames):
    fig, ax = plt.subplots(figsize=(12, 5.0))
    for key in ["EW", "overlay_rank", "overlay_zscore"]:
        d, _, dd, _ = _series(frames, key)
        ax.plot(d, dd * 100, label=LABEL[key], color=COLORS[key], lw=1.3)
        if key == "overlay_rank":
            ax.fill_between(d, dd * 100, 0, color=COLORS[key], alpha=0.15)
    ax.set_title("일별 리밸런싱 드로다운(낙폭) 비교", fontsize=14, fontweight="bold")
    ax.set_ylabel("Drawdown (%)")
    ax.set_xlabel("날짜")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left", framealpha=0.9)
    fig.tight_layout()
    p = FIGURE_DIR / "main_v2_daily_fig2_drawdown.png"
    fig.savefig(p, dpi=130); plt.close(fig)
    print(f"- 저장: {p}")


# ------------------------------------------------------------
# Fig3. 전략 성과지표 비교 (%지표 / 비율지표 분리)
# ------------------------------------------------------------
def plot_metrics():
    perf = pd.read_csv(TABLE_DIR / "main_v2_daily_performance_summary.csv")

    def row(method, strat):
        return perf[(perf["method"] == method) & (perf["strategy"] == strat)].iloc[0]

    keys = ["EW", "overlay_rank", "overlay_zscore"]
    rows = {
        "EW": row("rank", "EW"),
        "overlay_rank": row("rank", "HSI_state5_overlay"),
        "overlay_zscore": row("zscore", "HSI_state5_overlay"),
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))

    # (a) % 지표: CAGR / 연변동성 / |MDD|
    pct_metrics = [("CAGR_pct", "CAGR"), ("annual_volatility_pct", "연변동성"), ("MDD_pct", "|MDD|")]
    x = np.arange(len(pct_metrics)); w = 0.26
    for i, key in enumerate(keys):
        vals = [abs(rows[key][mk]) for mk, _ in pct_metrics]
        b = ax1.bar(x + (i - 1) * w, vals, w, label=LABEL[key], color=COLORS[key])
        ax1.bar_label(b, fmt="%.1f", fontsize=8, padding=2)
    ax1.set_xticks(x); ax1.set_xticklabels([lab for _, lab in pct_metrics])
    ax1.set_ylabel("%"); ax1.set_title("수익·위험 (% 지표)", fontsize=12, fontweight="bold")
    ax1.grid(alpha=0.3, axis="y"); ax1.legend(fontsize=8)

    # (b) 비율 지표: Sharpe / Calmar
    ratio_metrics = [("Sharpe", "Sharpe"), ("Calmar", "Calmar")]
    x2 = np.arange(len(ratio_metrics))
    for i, key in enumerate(keys):
        vals = [rows[key][mk] for mk, _ in ratio_metrics]
        b = ax2.bar(x2 + (i - 1) * w, vals, w, label=LABEL[key], color=COLORS[key])
        ax2.bar_label(b, fmt="%.2f", fontsize=8, padding=2)
    ax2.set_xticks(x2); ax2.set_xticklabels([lab for _, lab in ratio_metrics])
    ax2.set_ylabel("비율"); ax2.set_title("위험조정 성과 (비율 지표)", fontsize=12, fontweight="bold")
    ax2.grid(alpha=0.3, axis="y"); ax2.legend(fontsize=8)

    fig.suptitle("일별 리밸런싱 전략 성과지표 비교 (연율화 252일)", fontsize=14, fontweight="bold")
    fig.tight_layout()
    p = FIGURE_DIR / "main_v2_daily_fig3_strategy_metrics.png"
    fig.savefig(p, dpi=130); plt.close(fig)
    print(f"- 저장: {p}")


# ------------------------------------------------------------
# Fig4. ETF 총기여도 분해 (EW vs HSI overlay, rank)
# ------------------------------------------------------------
def plot_etf_contribution():
    summ = pd.read_csv(TABLE_DIR / "main_v2_daily_etf_summary_rank.csv", dtype={"ticker": str})
    summ["ticker"] = summ["ticker"].str.zfill(6)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    strat_keys = [("EW", "EW (동일가중)"), ("HSI_state5_overlay", "HSI overlay (rank)")]
    x = np.arange(len(ASSETS)); w = 0.36
    palette = ["#4c72b0", "#dd8452"]
    for i, (sk, slab) in enumerate(strat_keys):
        g = summ[summ["strategy"] == sk].set_index("ticker")
        vals = [g.loc[a, "total_contribution_pct"] for a in ASSETS]
        b = ax.bar(x + (i - 0.5) * w, vals, w, label=slab, color=palette[i])
        ax.bar_label(b, fmt="%.1f", fontsize=9, padding=2)
    ax.set_xticks(x); ax.set_xticklabels([ETF_LABEL[a] for a in ASSETS])
    ax.set_ylabel("총 기여도 (%, 단순합)")
    ax.set_title("ETF별 총 수익 기여도 분해", fontsize=14, fontweight="bold")
    ax.axhline(0, color="black", lw=0.7)
    ax.grid(alpha=0.3, axis="y"); ax.legend()
    fig.tight_layout()
    p = FIGURE_DIR / "main_v2_daily_fig4_etf_contribution.png"
    fig.savefig(p, dpi=130); plt.close(fig)
    print(f"- 저장: {p}")


# ------------------------------------------------------------
# Fig5. 전략 월별 수익률 히트맵 (HSI overlay, rank)
# ------------------------------------------------------------
def plot_monthly_heatmap():
    mon = pd.read_csv(TABLE_DIR / "main_v2_daily_etf_detail_monthly_rank.csv")
    g = mon[mon["strategy"] == "HSI_state5_overlay"].copy()
    g["year"] = g["year_month"].str[:4].astype(int)
    g["month"] = g["year_month"].str[5:7].astype(int)
    pivot = g.pivot_table(index="year", columns="month", values="strategy_month_return_pct")

    fig, ax = plt.subplots(figsize=(11, 6))
    vmax = np.nanmax(np.abs(pivot.values))
    im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(pivot.shape[1])); ax.set_xticklabels([f"{c}월" for c in pivot.columns])
    ax.set_yticks(range(pivot.shape[0])); ax.set_yticklabels(pivot.index)
    for r in range(pivot.shape[0]):
        for c in range(pivot.shape[1]):
            v = pivot.values[r, c]
            if not np.isnan(v):
                ax.text(c, r, f"{v:.1f}", ha="center", va="center", fontsize=7,
                        color="black" if abs(v) < vmax * 0.6 else "white")
    ax.set_title("HSI overlay(rank) 전략 월별 수익률 히트맵 (%)", fontsize=14, fontweight="bold")
    fig.colorbar(im, ax=ax, label="월 수익률 (%)", fraction=0.025)
    fig.tight_layout()
    p = FIGURE_DIR / "main_v2_daily_fig5_monthly_heatmap.png"
    fig.savefig(p, dpi=130); plt.close(fig)
    print(f"- 저장: {p}")


def main():
    print("=" * 70)
    print("32_main_v2_plot_daily_rebalance_etf_detail.py 실행 (성과표 → 그래프)")
    print("=" * 70)
    frames = load_timeseries()
    plot_cumulative(frames)
    plot_drawdown(frames)
    plot_metrics()
    plot_etf_contribution()
    plot_monthly_heatmap()
    print("완료: output/figures/main_v2_daily_fig1~5")


if __name__ == "__main__":
    main()
