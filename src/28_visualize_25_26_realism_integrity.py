# -*- coding: utf-8 -*-
"""
28_visualize_25_26_realism_integrity.py

목적
----
25번(일별 리밸런싱)과 26번(월별 보유 + 일별 평가) 비교 검증 결과를
보고서/발표에 바로 사용할 수 있는 시각화와 해석 노트로 정리한다.

이 스크립트는 27번 스크립트가 생성한 비교/무결성 CSV와
25번·26번 산출 시계열을 읽어 다음을 만든다.

1) 무결성 점검 PASS/FAIL 요약 그림
2) 미래 정보 누수 방지: signal_date < Date 최소 lag 점검 그림
3) Turnover 배율 비교 그림
4) CAGR/MDD 차이 비교 그림
5) 총 Turnover 비교 그림
6) 누적수익률 비교 그림(25 vs 26)
7) Drawdown 비교 그림(25 vs 26)
8) 월별 Turnover 비교 그림(25 vs 26)
9) 보고서용 Markdown 노트

사용 위치
---------
프로젝트의 src/ 폴더에 저장한 뒤 프로젝트 루트에서 실행한다.

예:
    python src/28_visualize_25_26_realism_integrity.py
    python src/28_visualize_25_26_realism_integrity.py --method zscore --strategy HSI_state5_overlay

필수 선행 작업
-------------
먼저 25번, 26번, 27번 산출물이 존재해야 한다.

    python src/25_main_v2_daily_rebalance_backtest_etf_detail.py
    python src/26_main_v2_monthly_hold_daily_valuation_etf_detail.py
    python src/27_compare_25_26_realism_integrity.py

입력
----
output/tables/main_v2_25_26_realism_comparison.csv
output/tables/main_v2_25_26_integrity_checks.csv
output/tables/main_v2_daily_backtest_timeseries_{rank,zscore}.csv
output/tables/main_v2_mhold_backtest_timeseries_{rank,zscore}.csv
output/tables/main_v2_daily_alignment_check.csv
output/tables/main_v2_mhold_alignment_check.csv

출력
----
output/figures/main_v2_25_26_fig01_integrity_pass_fail.png
output/figures/main_v2_25_26_fig02_lookahead_min_lag_days.png
output/figures/main_v2_25_26_fig03_turnover_ratio.png
output/figures/main_v2_25_26_fig04_cagr_mdd_gap.png
output/figures/main_v2_25_26_fig05_total_turnover_comparison.png
output/figures/main_v2_25_26_fig06_cumulative_return_{method}_{strategy}.png
output/figures/main_v2_25_26_fig07_drawdown_{method}_{strategy}.png
output/figures/main_v2_25_26_fig08_monthly_turnover_{method}_{strategy}.png
output/tables/main_v2_25_26_visual_lookahead_summary.csv
docs/main_v2_25_26_visual_report_note.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager


METHODS = ["rank", "zscore"]
STRATEGIES = ["EW", "HSI_state5_overlay"]


def resolve_project_root() -> Path:
    here = Path(__file__).resolve()
    if here.parent.name == "src":
        return here.parents[1]
    return here.parent


PROJECT_ROOT = resolve_project_root()
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
FIG_DIR = PROJECT_ROOT / "output" / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"


def setup_korean_font() -> None:
    """Windows/Mac/Linux에서 가능한 한글 폰트를 자동 설정한다."""
    candidates = [
        "Malgun Gothic",
        "AppleGothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "NanumGothic",
        "DejaVu Sans",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


def read_csv(path: Path, parse_dates: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"필요한 파일이 없습니다: {path}\n"
            "먼저 25번, 26번, 27번 스크립트를 실행했는지 확인하세요."
        )
    return pd.read_csv(path, parse_dates=parse_dates)


def savefig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"- 저장: {path}")


def add_bar_labels(ax, fmt: str = "{:.2f}", suffix: str = "") -> None:
    for patch in ax.patches:
        width = patch.get_width()
        height = patch.get_height()
        if np.isnan(width):
            continue
        x = width
        y = patch.get_y() + height / 2
        ha = "left" if width >= 0 else "right"
        offset = 0.01 * max(1.0, abs(ax.get_xlim()[1] - ax.get_xlim()[0]))
        ax.text(x + (offset if width >= 0 else -offset), y, fmt.format(width) + suffix,
                va="center", ha=ha, fontsize=9)


def label_case(df: pd.DataFrame) -> pd.Series:
    return df["method"].astype(str) + " / " + df["strategy"].astype(str)


def plot_integrity_pass_fail(checks: pd.DataFrame) -> Path:
    counts = checks["result"].value_counts().reindex(["PASS", "FAIL"], fill_value=0)
    fig_path = FIG_DIR / "main_v2_25_26_fig01_integrity_pass_fail.png"

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.bar(counts.index, counts.values)
    for i, v in enumerate(counts.values):
        ax.text(i, v, f"{int(v)}개", ha="center", va="bottom", fontsize=11)
    ax.set_title("25번·26번 비교 검증: 무결성 점검 결과")
    ax.set_ylabel("점검 항목 수")
    ax.set_xlabel("판정")
    ax.grid(axis="y", alpha=0.3)
    ymax = max(counts.max() * 1.15, 1)
    ax.set_ylim(0, ymax)
    savefig(fig_path)
    return fig_path


def build_lookahead_summary() -> pd.DataFrame:
    rows: list[dict] = []
    for assumption, prefix in [
        ("25_daily_rebalance", "main_v2_daily_backtest_timeseries"),
        ("26_monthly_hold_daily_valuation", "main_v2_mhold_backtest_timeseries"),
    ]:
        for method in METHODS:
            path = TABLE_DIR / f"{prefix}_{method}.csv"
            df = read_csv(path, parse_dates=["Date", "signal_date"])
            if "signal_date" not in df.columns or "Date" not in df.columns:
                raise ValueError(f"Date/signal_date 컬럼이 없습니다: {path}")
            if "strategy" not in df.columns:
                df["strategy"] = "ALL"
            tmp = df.dropna(subset=["Date", "signal_date"]).copy()
            tmp["lag_days"] = (tmp["Date"] - tmp["signal_date"]).dt.days
            for strategy, g in tmp.groupby("strategy"):
                min_lag = int(g["lag_days"].min()) if len(g) else np.nan
                median_lag = float(g["lag_days"].median()) if len(g) else np.nan
                fail_count = int((g["lag_days"] <= 0).sum()) if len(g) else 0
                rows.append({
                    "assumption": assumption,
                    "method": method,
                    "strategy": strategy,
                    "rows_checked": int(len(g)),
                    "min_lag_days": min_lag,
                    "median_lag_days": median_lag,
                    "lookahead_fail_count": fail_count,
                    "result": "PASS" if fail_count == 0 and pd.notna(min_lag) and min_lag > 0 else "FAIL",
                })
    out = pd.DataFrame(rows)
    out_path = TABLE_DIR / "main_v2_25_26_visual_lookahead_summary.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"- 저장: {out_path}")
    return out


def plot_lookahead_min_lag(lookahead: pd.DataFrame) -> Path:
    fig_path = FIG_DIR / "main_v2_25_26_fig02_lookahead_min_lag_days.png"
    show = lookahead.copy()
    show = show[show["strategy"].isin(STRATEGIES)].copy()
    show["case"] = show["assumption"].str.replace("25_daily_rebalance", "25 daily", regex=False)
    show["case"] = show["case"].str.replace("26_monthly_hold_daily_valuation", "26 monthly hold", regex=False)
    show["case"] = show["case"] + " / " + show["method"] + " / " + show["strategy"]
    show = show.sort_values(["assumption", "method", "strategy"])

    fig, ax = plt.subplots(figsize=(10, max(4.5, 0.45 * len(show))))
    y = np.arange(len(show))
    ax.barh(y, show["min_lag_days"])
    ax.set_yticks(y)
    ax.set_yticklabels(show["case"])
    ax.axvline(0, linestyle="--", linewidth=1)
    ax.set_title("미래 정보 누수 점검: signal_date와 실제 평가일 사이 최소 lag")
    ax.set_xlabel("Date - signal_date 최소 일수")
    ax.set_ylabel("검증 케이스")
    ax.grid(axis="x", alpha=0.3)
    for i, v in enumerate(show["min_lag_days"]):
        ax.text(v + 0.2, i, f"{int(v)}일", va="center", fontsize=9)
    savefig(fig_path)
    return fig_path


def plot_turnover_ratio(comparison: pd.DataFrame) -> Path:
    fig_path = FIG_DIR / "main_v2_25_26_fig03_turnover_ratio.png"
    show = comparison.copy()
    show["case"] = label_case(show)
    show = show.sort_values("Turnover_daily_div_mhold", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.barh(show["case"], show["Turnover_daily_div_mhold"])
    ax.axvline(1.0, linestyle="--", linewidth=1)
    ax.set_title("현실성 비교: 25번 일별 리밸런싱의 Turnover 배율")
    ax.set_xlabel("26번 대비 25번 총 Turnover 배율")
    ax.set_ylabel("방법 / 전략")
    ax.grid(axis="x", alpha=0.3)
    add_bar_labels(ax, fmt="{:.2f}", suffix="배")
    savefig(fig_path)
    return fig_path


def plot_cagr_mdd_gap(comparison: pd.DataFrame) -> Path:
    fig_path = FIG_DIR / "main_v2_25_26_fig04_cagr_mdd_gap.png"
    show = comparison.copy()
    show["case"] = label_case(show)
    plot_df = show[["case", "CAGR_daily_minus_mhold_pp", "MDD_daily_minus_mhold_pp"]].copy()
    plot_df = plot_df.rename(columns={
        "CAGR_daily_minus_mhold_pp": "CAGR gap",
        "MDD_daily_minus_mhold_pp": "MDD gap",
    })
    long = plot_df.melt(id_vars="case", var_name="metric", value_name="gap_pp")
    cases = list(plot_df["case"])
    x = np.arange(len(cases))
    width = 0.36

    fig, ax = plt.subplots(figsize=(10, 5.2))
    for idx, metric in enumerate(["CAGR gap", "MDD gap"]):
        vals = long[long["metric"] == metric].set_index("case").loc[cases, "gap_pp"]
        ax.bar(x + (idx - 0.5) * width, vals, width, label=metric)
        for xi, v in zip(x + (idx - 0.5) * width, vals):
            ax.text(xi, v - 0.01 if v < 0 else v + 0.01, f"{v:.3f}%p",
                    ha="center", va="top" if v < 0 else "bottom", fontsize=8, rotation=90)
    ax.axhline(0, linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(cases, rotation=20, ha="right")
    ax.set_title("성과 차이: 25번 일별 리밸런싱 - 26번 월별 보유")
    ax.set_ylabel("차이(%p)")
    ax.set_xlabel("방법 / 전략")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    savefig(fig_path)
    return fig_path


def plot_total_turnover_comparison(comparison: pd.DataFrame) -> Path:
    fig_path = FIG_DIR / "main_v2_25_26_fig05_total_turnover_comparison.png"
    show = comparison.copy()
    show["case"] = label_case(show)
    cases = list(show["case"])
    x = np.arange(len(cases))
    width = 0.36

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.bar(x - width / 2, show["total_turnover_pct_daily"], width, label="25 daily rebalance")
    ax.bar(x + width / 2, show["total_turnover_pct_mhold"], width, label="26 monthly hold")
    ax.set_xticks(x)
    ax.set_xticklabels(cases, rotation=20, ha="right")
    ax.set_title("총 Turnover 비교: 일별 리밸런싱 vs 월별 보유")
    ax.set_ylabel("총 Turnover(%)")
    ax.set_xlabel("방법 / 전략")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    savefig(fig_path)
    return fig_path


def load_timeseries(method: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily = read_csv(
        TABLE_DIR / f"main_v2_daily_backtest_timeseries_{method}.csv",
        parse_dates=["Date", "signal_date"],
    )
    mhold = read_csv(
        TABLE_DIR / f"main_v2_mhold_backtest_timeseries_{method}.csv",
        parse_dates=["Date", "signal_date"],
    )
    return daily, mhold


def plot_cumulative_return(method: str, strategy: str) -> Path:
    fig_path = FIG_DIR / f"main_v2_25_26_fig06_cumulative_return_{method}_{strategy}.png"
    daily, mhold = load_timeseries(method)
    d = daily[daily["strategy"] == strategy].sort_values("Date")
    m = mhold[mhold["strategy"] == strategy].sort_values("Date")

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(d["Date"], (d["cumulative_return"] - 1.0) * 100, label="25 daily rebalance")
    ax.plot(m["Date"], (m["cumulative_return"] - 1.0) * 100, label="26 monthly hold")
    ax.set_title(f"누적수익률 비교: {method} / {strategy}")
    ax.set_ylabel("누적수익률(%)")
    ax.set_xlabel("날짜")
    ax.legend()
    ax.grid(alpha=0.3)
    savefig(fig_path)
    return fig_path


def plot_drawdown(method: str, strategy: str) -> Path:
    fig_path = FIG_DIR / f"main_v2_25_26_fig07_drawdown_{method}_{strategy}.png"
    daily, mhold = load_timeseries(method)
    d = daily[daily["strategy"] == strategy].sort_values("Date")
    m = mhold[mhold["strategy"] == strategy].sort_values("Date")

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(d["Date"], d["drawdown"] * 100, label="25 daily rebalance")
    ax.plot(m["Date"], m["drawdown"] * 100, label="26 monthly hold")
    ax.axhline(0, linewidth=1)
    ax.set_title(f"Drawdown 비교: {method} / {strategy}")
    ax.set_ylabel("Drawdown(%)")
    ax.set_xlabel("날짜")
    ax.legend()
    ax.grid(alpha=0.3)
    savefig(fig_path)
    return fig_path


def plot_monthly_turnover(method: str, strategy: str) -> Path:
    fig_path = FIG_DIR / f"main_v2_25_26_fig08_monthly_turnover_{method}_{strategy}.png"
    daily, mhold = load_timeseries(method)
    d = daily[daily["strategy"] == strategy].copy()
    m = mhold[mhold["strategy"] == strategy].copy()
    d["year_month"] = d["Date"].dt.to_period("M").dt.to_timestamp()
    m["year_month"] = m["Date"].dt.to_period("M").dt.to_timestamp()
    d_mon = d.groupby("year_month")["turnover"].sum() * 100
    m_mon = m.groupby("year_month")["turnover"].sum() * 100

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(d_mon.index, d_mon.values, label="25 daily rebalance")
    ax.plot(m_mon.index, m_mon.values, label="26 monthly hold")
    ax.set_title(f"월별 Turnover 비교: {method} / {strategy}")
    ax.set_ylabel("월별 Turnover 합계(%)")
    ax.set_xlabel("월")
    ax.legend()
    ax.grid(alpha=0.3)
    savefig(fig_path)
    return fig_path


def get_num(df: pd.DataFrame, col: str, default=np.nan) -> float:
    if col not in df.columns or df.empty:
        return default
    return float(df.iloc[0][col])


def build_report_note(
    comparison: pd.DataFrame,
    checks: pd.DataFrame,
    lookahead: pd.DataFrame,
    figure_paths: list[Path],
    method: str,
    strategy: str,
) -> Path:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    note_path = DOCS_DIR / "main_v2_25_26_visual_report_note.md"

    fail_count = int((checks["result"] == "FAIL").sum())
    pass_count = int((checks["result"] == "PASS").sum())
    total_count = int(len(checks))
    lookahead_fail = int(lookahead["lookahead_fail_count"].sum())
    min_lag = int(lookahead["min_lag_days"].min())

    row = comparison[(comparison["method"] == method) & (comparison["strategy"] == strategy)]
    cagr_gap = get_num(row, "CAGR_daily_minus_mhold_pp")
    mdd_gap = get_num(row, "MDD_daily_minus_mhold_pp")
    turnover_gap = get_num(row, "Turnover_daily_minus_mhold_pp")
    turnover_ratio = get_num(row, "Turnover_daily_div_mhold")

    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")

    lines: list[str] = []
    lines.append("# 25번·26번 기반 현실성 및 무결성 시각화 보고 노트")
    lines.append("")
    lines.append("## 1. 검증 목적")
    lines.append("")
    lines.append(
        "본 프로젝트는 월말 HSI 상태를 이용하여 다음 월의 ETF 목표비중을 정하는 월간 자산배분 전략이다. "
        "따라서 일별 가격 자료를 사용하더라도, 매 거래일 목표비중을 다시 맞추는 가정은 실제 월간 운용 구조보다 "
        "거래 빈도를 높게 잡는 실험적 가정에 가깝다."
    )
    lines.append("")
    lines.append(
        "이에 따라 25번 스크립트는 일별 리밸런싱 민감도 실험으로, 26번 스크립트는 월초 리밸런싱 후 월중 보유를 "
        "가정하는 현실성 검증으로 구분하였다. 이후 27번과 28번 스크립트를 통해 두 방식의 계산 무결성과 성과 차이를 "
        "함께 확인하였다."
    )
    lines.append("")
    lines.append("## 2. 무결성 및 미래정보 누수 점검")
    lines.append("")
    lines.append(
        f"무결성 점검 결과, 총 {total_count}개 점검 항목 중 PASS {pass_count}개, FAIL {fail_count}개로 확인되었다. "
        f"또한 signal_date와 실제 평가일 Date의 시차를 확인한 결과, 최소 lag는 {min_lag}일이며 "
        f"look-ahead fail count는 {lookahead_fail}건으로 집계되었다."
    )
    lines.append("")
    lines.append("![무결성 PASS/FAIL 요약](../output/figures/main_v2_25_26_fig01_integrity_pass_fail.png)")
    lines.append("")
    lines.append("![미래정보 누수 점검](../output/figures/main_v2_25_26_fig02_lookahead_min_lag_days.png)")
    lines.append("")
    lines.append(
        "이 결과는 월말 신호가 같은 달 수익률에 섞이지 않고, 다음 기간의 평가일에 적용되었음을 보여준다. "
        "따라서 본 비교는 신호와 수익률의 시점 정렬 측면에서 중대한 미래정보 누수 없이 수행된 것으로 해석할 수 있다."
    )
    lines.append("")
    lines.append("## 3. 현실성 비교: 성과보다 Turnover 차이가 핵심")
    lines.append("")
    lines.append(
        f"대표 케이스인 {method}/{strategy} 기준으로, 25번 일별 리밸런싱 방식은 26번 월별 보유 방식에 비해 "
        f"CAGR 차이가 {cagr_gap:.4f}%p, MDD 차이가 {mdd_gap:.4f}%p로 나타났다. 반면 총 Turnover는 "
        f"{turnover_gap:.4f}%p 높고, 배율로는 {turnover_ratio:.4f}배 수준이었다."
    )
    lines.append("")
    lines.append("![Turnover 배율 비교](../output/figures/main_v2_25_26_fig03_turnover_ratio.png)")
    lines.append("")
    lines.append("![CAGR/MDD 차이 비교](../output/figures/main_v2_25_26_fig04_cagr_mdd_gap.png)")
    lines.append("")
    lines.append("![총 Turnover 비교](../output/figures/main_v2_25_26_fig05_total_turnover_comparison.png)")
    lines.append("")
    lines.append(
        "즉, 일별 리밸런싱은 성과를 뚜렷하게 개선하지 못하면서 거래 빈도와 거래 부담을 크게 증가시켰다. "
        "이는 25번 결과를 최종 운용 성과로 보기보다는 실행가정 민감도 또는 대조군으로 해석해야 함을 의미한다."
    )
    lines.append("")
    lines.append("## 4. 경로 비교: 누적수익률, Drawdown, 월별 Turnover")
    lines.append("")
    lines.append(f"아래 그림은 대표 케이스 {method}/{strategy}에 대해 25번과 26번의 경로를 직접 비교한 것이다.")
    lines.append("")
    lines.append(f"![누적수익률 비교](../output/figures/main_v2_25_26_fig06_cumulative_return_{method}_{strategy}.png)")
    lines.append("")
    lines.append(f"![Drawdown 비교](../output/figures/main_v2_25_26_fig07_drawdown_{method}_{strategy}.png)")
    lines.append("")
    lines.append(f"![월별 Turnover 비교](../output/figures/main_v2_25_26_fig08_monthly_turnover_{method}_{strategy}.png)")
    lines.append("")
    lines.append(
        "누적수익률과 drawdown 경로는 두 방식이 같은 HSI 목표비중 체계를 공유하지만, 리밸런싱 실행가정에 따라 "
        "월중 평가 경로와 거래 부담이 달라질 수 있음을 보여준다. 특히 월별 Turnover 비교는 25번의 일별 재조정 가정이 "
        "불필요하게 높은 거래량을 만들 수 있음을 시각적으로 확인시켜 준다."
    )
    lines.append("")
    lines.append("## 5. 결론")
    lines.append("")
    lines.append(
        "25번·26번 비교 검증 결과, 본 프로젝트의 최종 현실성 평가는 26번 월별 보유 + 일별 평가 방식을 중심으로 "
        "해석하는 것이 타당하다. 25번은 매 거래일 목표비중을 유지하는 이론적·실험적 가정에 가깝고, 실제 비교 결과에서도 "
        "성과 개선보다는 Turnover 증가 효과가 더 두드러졌다. 반면 26번은 월초 리밸런싱 이후 보유수량과 평가금액을 통해 "
        "일별 포트폴리오 가치를 재계산하므로, 본 프로젝트의 월간 HSI 자산배분 구조와 더 잘 부합한다."
    )
    lines.append("")
    lines.append(
        "따라서 이번 검증은 HSI 전략이 단순히 백테스트 결과만 제시한 것이 아니라, 미래정보 누수, 계산 무결성, 리밸런싱 실행가정, "
        "Turnover 부담을 함께 점검했다는 점을 보여준다. 이 결과는 전략의 미래 성과를 보장하는 것은 아니지만, 보고서에서 "
        "백테스트 결과의 현실성과 계산 신뢰도를 보완하는 근거로 사용할 수 있다."
    )
    lines.append("")
    lines.append("## 생성 그림 목록")
    lines.append("")
    for p in figure_paths:
        lines.append(f"- `{rel(p)}`")

    note_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"- 저장: {note_path}")
    return note_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", default="zscore", choices=METHODS,
                        help="경로 비교 그림에 사용할 대표 점수화 방식")
    parser.add_argument("--strategy", default="HSI_state5_overlay", choices=STRATEGIES,
                        help="경로 비교 그림에 사용할 대표 전략")
    args = parser.parse_args()

    setup_korean_font()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("28_visualize_25_26_realism_integrity.py 실행 시작")
    print("=" * 80)
    print(f"[PROJECT_ROOT] {PROJECT_ROOT}")
    print(f"[대표 케이스] method={args.method}, strategy={args.strategy}")

    comparison = read_csv(TABLE_DIR / "main_v2_25_26_realism_comparison.csv")
    checks = read_csv(TABLE_DIR / "main_v2_25_26_integrity_checks.csv")

    print("[1] look-ahead summary 생성")
    lookahead = build_lookahead_summary()

    print("[2] 시각화 생성")
    figure_paths = [
        plot_integrity_pass_fail(checks),
        plot_lookahead_min_lag(lookahead),
        plot_turnover_ratio(comparison),
        plot_cagr_mdd_gap(comparison),
        plot_total_turnover_comparison(comparison),
        plot_cumulative_return(args.method, args.strategy),
        plot_drawdown(args.method, args.strategy),
        plot_monthly_turnover(args.method, args.strategy),
    ]

    print("[3] 보고서 노트 생성")
    note_path = build_report_note(
        comparison=comparison,
        checks=checks,
        lookahead=lookahead,
        figure_paths=figure_paths,
        method=args.method,
        strategy=args.strategy,
    )

    print("\n[요약]")
    print(f"- 생성 그림 수: {len(figure_paths)}")
    print(f"- 보고서 노트: {note_path}")
    print(f"- 무결성 FAIL 수: {(checks['result'] == 'FAIL').sum()}")
    print(f"- Look-ahead FAIL 수: {lookahead['lookahead_fail_count'].sum()}")
    print("=" * 80)
    print("28_visualize_25_26_realism_integrity.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
