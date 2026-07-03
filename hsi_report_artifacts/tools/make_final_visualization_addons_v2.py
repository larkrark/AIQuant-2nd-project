# -*- coding: utf-8 -*-
"""
make_final_visualization_addons_v2.py

기존 main_final 추가 시각화 중 사람이 보기 불편했던 그림을
'결론이 바로 읽히는 비교형 요약 시각화'로 개선합니다.

생성:
- main_final_experiment_flow_diagram_v2.png
- main_final_hsi_macro_overlap_timeline_v2.png
- main_final_benchmark_alignment_period_cagr_heatmap_v2.png
- main_final_hsi_state_yearly_share_v2.png
- main_final_lambda_macro_sensitivity_small_multiples_v2.png
- main_final_visualization_v2_index.csv

실행:
    .\\.venv\\Scripts\\python.exe .\\src\\make_final_visualization_addons_v2.py
"""

from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"

FIGURES.mkdir(parents=True, exist_ok=True)
TABLES.mkdir(parents=True, exist_ok=True)


FINAL_COMPARISON_ORDER = [
    "Fixed 70/20/10 BM",
    "EW Benchmark",
    "HSI baseline",
    "Lambda 0.1",
    "Lambda 0.3",
]

HSI_STATE_ORDER = [
    "risk_relief",
    "neutral_watch",
    "conflict",
    "risk_warning",
    "accident_zone",
    "insufficient_data",
]

HSI_RISK_STATES = {"risk_warning", "accident_zone"}


STRATEGY_TS_CANDIDATES = [
    DATA / "main_final_benchmark_alignment_strategy_timeseries.csv",
    DATA / "main_final_regime_robustness_strategy_timeseries.csv",
]

PERIOD_SUMMARY_CANDIDATES = [
    TABLES / "main_final_benchmark_alignment_by_period.csv",
    TABLES / "main_final_regime_robustness_by_period.csv",
]

MACRO_JOINED_CANDIDATES = [
    DATA / "main_final_hsi_macro_companion_joined_monthly.csv",
    DATA / "main_final_macro_overlay_weights.csv",
    DATA / "main_final_macro_companion_features_monthly.csv",
]

MACRO_SENSITIVITY_CANDIDATES = [
    TABLES / "main_final_lambda_macro_overlay_sensitivity_summary.csv",
]


def read_csv_safely(path: Path) -> pd.DataFrame:
    for enc in ["utf-8-sig", "utf-8", "cp949"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def find_first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def parse_month_series(s: pd.Series) -> pd.Series:
    x = pd.to_datetime(s, errors="coerce")
    if x.notna().mean() < 0.5:
        x = pd.to_datetime(s.astype(str) + "-01", errors="coerce")
    return x.dt.to_period("M").dt.to_timestamp("M")


def set_korean_font() -> None:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"    저장: {path}")


def to_pct_if_decimal(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    if x.abs().max(skipna=True) <= 1.5:
        x = x * 100
    return x


def load_strategy_timeseries() -> pd.DataFrame | None:
    path = first_existing(STRATEGY_TS_CANDIDATES)
    if path is None:
        warnings.warn("전략 시계열 파일을 찾지 못했습니다.")
        return None
    df = read_csv_safely(path)
    print(f"[로드] strategy timeseries: {path}")

    date_col = find_first_col(df, ["return_month", "Date", "date", "year_month", "month"])
    if date_col is None:
        warnings.warn("전략 시계열의 날짜 컬럼을 찾지 못했습니다.")
        return None

    if "strategy_name" not in df.columns:
        st_col = find_first_col(df, ["strategy", "model_id", "strategy_id"])
        if st_col is None:
            warnings.warn("전략명 컬럼을 찾지 못했습니다.")
            return None
        df = df.rename(columns={st_col: "strategy_name"})

    df["plot_month"] = parse_month_series(df[date_col])
    return df.dropna(subset=["plot_month"]).copy()


def load_period_summary() -> pd.DataFrame | None:
    path = first_existing(PERIOD_SUMMARY_CANDIDATES)
    if path is None:
        warnings.warn("기간별 성과표 파일을 찾지 못했습니다.")
        return None
    df = read_csv_safely(path)
    print(f"[로드] period summary: {path}")
    if "strategy_name" not in df.columns:
        st_col = find_first_col(df, ["strategy", "strategy_id", "model_id"])
        if st_col:
            df = df.rename(columns={st_col: "strategy_name"})
    return df


def load_macro_joined() -> pd.DataFrame | None:
    path = first_existing(MACRO_JOINED_CANDIDATES)
    if path is None:
        warnings.warn("HSI-macro joined 파일을 찾지 못했습니다.")
        return None
    df = read_csv_safely(path)
    print(f"[로드] macro joined: {path}")
    date_col = find_first_col(df, ["year_month", "return_year_month", "Date", "date", "month"])
    if date_col is None:
        warnings.warn("macro joined 파일의 날짜 컬럼을 찾지 못했습니다.")
        return None
    df["plot_month"] = parse_month_series(df[date_col])
    return df.dropna(subset=["plot_month"]).copy()


def load_macro_sensitivity() -> pd.DataFrame | None:
    path = first_existing(MACRO_SENSITIVITY_CANDIDATES)
    if path is None:
        warnings.warn("Lambda + macro sensitivity 요약 파일을 찾지 못했습니다.")
        return None
    print(f"[로드] macro sensitivity: {path}")
    return read_csv_safely(path)


def plot_experiment_flow_diagram_v2() -> None:
    set_korean_font()
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.axis("off")

    cols = [0.12, 0.34, 0.56, 0.78]
    y_top, y_mid, y_bottom = 0.72, 0.42, 0.16

    boxes = [
        ("기반 구축\n00~05\n데이터 정리 · HSI baseline", cols[0], y_top),
        ("상태 해석 보조\n06~09\nEvent · Diagnostic", cols[1], y_top),
        ("모델 개선\n10~15\nLambda · Theta · Macro", cols[2], y_top),
        ("최종 검증\n16~17\nRobustness · BM alignment", cols[3], y_top),
        ("최종 후보\nλ=0.1 저회전·보수형\nλ=0.3 수익성·Calmar 균형형", 0.30, y_bottom),
        ("비교 기준\nMain BM: Fixed 70/20/10\nAux BM: EW\nInternal: HSI baseline", 0.70, y_bottom),
    ]

    for text, x, y in boxes:
        ax.text(x, y, text, ha="center", va="center", fontsize=11,
                bbox=dict(boxstyle="round,pad=0.55", linewidth=1.3, facecolor="white"))

    for x1, x2 in zip(cols[:-1], cols[1:]):
        ax.annotate("", xy=(x2 - 0.10, y_top), xytext=(x1 + 0.10, y_top),
                    arrowprops=dict(arrowstyle="->", lw=1.5))

    ax.annotate("", xy=(0.30, y_bottom + 0.12), xytext=(cols[3] - 0.06, y_top - 0.08),
                arrowprops=dict(arrowstyle="->", lw=1.3))
    ax.annotate("", xy=(0.70, y_bottom + 0.12), xytext=(cols[3] + 0.06, y_top - 0.08),
                arrowprops=dict(arrowstyle="->", lw=1.3))

    ax.text(0.5, y_mid,
            "프로젝트 중심축: HSI 상태를 ETF 비중 행동으로 부드럽게 번역하는 λ 부분조정 구조",
            ha="center", va="center", fontsize=12,
            bbox=dict(boxstyle="round,pad=0.35", linewidth=1.0, facecolor="white"))

    ax.set_title("Main final experiment flow v2: 00~17", fontsize=16, pad=18)
    savefig(FIGURES / "main_final_experiment_flow_diagram_v2.png")


def plot_hsi_macro_overlap_timeline_v2(macro_joined: pd.DataFrame | None) -> None:
    if macro_joined is None:
        return
    df = macro_joined.copy().sort_values("plot_month")

    if "hsi_risk_flag" in df.columns:
        hsi_risk = pd.to_numeric(df["hsi_risk_flag"], errors="coerce").fillna(0).astype(int)
    elif "hsi_state" in df.columns:
        hsi_risk = df["hsi_state"].astype(str).isin(HSI_RISK_STATES).astype(int)
    else:
        warnings.warn("HSI risk를 만들 hsi_risk_flag 또는 hsi_state 컬럼이 없습니다.")
        return

    if "macro_risk_flag" not in df.columns:
        warnings.warn("macro_risk_flag 컬럼이 없어 HSI-macro overlap 그림을 건너뜁니다.")
        return

    macro_risk = pd.to_numeric(df["macro_risk_flag"], errors="coerce").fillna(0).astype(int)
    overlap = hsi_risk + macro_risk * 2

    set_korean_font()
    fig, ax = plt.subplots(figsize=(15, 3.5))
    matrix = np.vstack([hsi_risk.to_numpy(), macro_risk.to_numpy(), overlap.to_numpy()])
    ax.imshow(matrix, aspect="auto", interpolation="nearest")

    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["HSI risk", "Macro risk", "Overlap"])

    years = sorted(df["plot_month"].dt.year.unique())
    tick_positions, tick_labels = [], []
    for y in years:
        pos = np.where(df["plot_month"].dt.year.to_numpy() == y)[0]
        if len(pos):
            tick_positions.append(int(pos[0]))
            tick_labels.append(str(y))

    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels)
    ax.set_title("HSI risk vs Macro risk overlap timeline", fontsize=15, pad=14)

    legend_items = [
        Patch(facecolor=plt.cm.viridis(0.00), label="No risk / 0"),
        Patch(facecolor=plt.cm.viridis(0.33), label="HSI only / 1"),
        Patch(facecolor=plt.cm.viridis(0.66), label="Macro only / 2"),
        Patch(facecolor=plt.cm.viridis(1.00), label="Both / 3"),
    ]
    ax.legend(handles=legend_items, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=4, frameon=False)
    savefig(FIGURES / "main_final_hsi_macro_overlap_timeline_v2.png")


def plot_period_cagr_heatmap_v2(period_summary: pd.DataFrame | None) -> None:
    if period_summary is None:
        return
    if "period" not in period_summary.columns or "strategy_name" not in period_summary.columns:
        warnings.warn("기간별 CAGR heatmap에 필요한 period/strategy_name 컬럼이 없습니다.")
        return

    cagr_col = find_first_col(period_summary, ["CAGR_pct", "CAGR(%)", "CAGR", "cagr_pct"])
    if cagr_col is None:
        warnings.warn("기간별 성과표에서 CAGR 컬럼을 찾지 못했습니다.")
        return

    df = period_summary.copy()
    df[cagr_col] = to_pct_if_decimal(df[cagr_col])

    pivot = (
        df[df["strategy_name"].isin(FINAL_COMPARISON_ORDER)]
        .pivot_table(index="strategy_name", columns="period", values=cagr_col, aggfunc="first")
        .reindex(FINAL_COMPARISON_ORDER)
    )
    if pivot.empty:
        warnings.warn("기간별 CAGR heatmap pivot이 비어 있습니다.")
        return

    set_korean_font()
    fig, ax = plt.subplots(figsize=(11, 4.8))
    im = ax.imshow(pivot.to_numpy(), aspect="auto")

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title("Benchmark alignment by period: CAGR heatmap", fontsize=14, pad=14)

    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.iloc[i, j]
            if pd.notna(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=9)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("CAGR (%)")
    savefig(FIGURES / "main_final_benchmark_alignment_period_cagr_heatmap_v2.png")


def plot_hsi_state_yearly_share_v2(ts: pd.DataFrame | None) -> None:
    if ts is None:
        return
    if "hsi_state" not in ts.columns:
        warnings.warn("hsi_state 컬럼이 없어 연도별 상태 점유율 그림을 건너뜁니다.")
        return

    df = ts[["plot_month", "hsi_state"]].dropna().drop_duplicates("plot_month").copy()
    df["year"] = df["plot_month"].dt.year

    counts = pd.crosstab(df["year"], df["hsi_state"])
    counts = counts.reindex(columns=[c for c in HSI_STATE_ORDER if c in counts.columns], fill_value=0)
    share = counts.div(counts.sum(axis=1), axis=0) * 100

    set_korean_font()
    fig, ax = plt.subplots(figsize=(12, 5))
    bottom = np.zeros(len(share))
    x = np.arange(len(share.index))

    for state in share.columns:
        vals = share[state].to_numpy()
        ax.bar(x, vals, bottom=bottom, label=state)
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels(share.index.astype(str))
    ax.set_ylabel("Share of months (%)")
    ax.set_title("HSI state composition by year", fontsize=14, pad=14)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False)
    ax.grid(True, axis="y", alpha=0.25)
    savefig(FIGURES / "main_final_hsi_state_yearly_share_v2.png")


def plot_macro_sensitivity_small_multiples_v2(macro: pd.DataFrame | None) -> None:
    if macro is None:
        return

    required = ["lambda_value", "macro_scale", "CAGR_pct", "MDD_pct", "Calmar", "avg_turnover_pct"]
    missing = [c for c in required if c not in macro.columns]
    if missing:
        warnings.warn(f"macro sensitivity small multiples에 필요한 컬럼이 없습니다: {missing}")
        return

    df = macro.copy()
    df["lambda_label"] = "Lambda " + df["lambda_value"].astype(float).map(lambda x: f"{x:.1f}")
    df = df.sort_values(["lambda_value", "macro_scale"])

    panels = [
        ("CAGR_pct", "CAGR (%)"),
        ("MDD_pct", "MDD (%)"),
        ("Calmar", "Calmar"),
        ("avg_turnover_pct", "Turnover (%)"),
    ]

    set_korean_font()
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    axes = axes.ravel()

    for ax, (col, label) in zip(axes, panels):
        for lambda_label, sub in df.groupby("lambda_label"):
            ax.plot(sub["macro_scale"], sub[col], marker="o", linewidth=1.8, label=lambda_label)
        ax.set_title(label)
        ax.set_xlabel("macro_scale")
        ax.grid(True, alpha=0.25)

    axes[0].legend(loc="best")
    fig.suptitle("Lambda + macro overlay sensitivity trade-off v2", fontsize=15)
    savefig(FIGURES / "main_final_lambda_macro_sensitivity_small_multiples_v2.png")


def write_visual_index_v2(files: list[Path]) -> None:
    descriptions = {
        "main_final_experiment_flow_diagram_v2.png": "교차 화살표를 줄이고 00~17을 기반 구축→모델 개선→최종 검증으로 재구성한 발표용 흐름도",
        "main_final_hsi_macro_overlap_timeline_v2.png": "HSI risk와 Macro risk를 0/1 선그래프 대신 overlap 상태 띠로 요약한 그림",
        "main_final_benchmark_alignment_period_cagr_heatmap_v2.png": "Fixed 70/20/10 BM을 메인 BM으로 포함한 기간별 CAGR heatmap",
        "main_final_hsi_state_yearly_share_v2.png": "월별 HSI 상태를 연도별 상태 점유율로 요약한 stacked bar",
        "main_final_lambda_macro_sensitivity_small_multiples_v2.png": "15번 Lambda+macro sensitivity 결과를 CAGR, MDD, Calmar, Turnover 미니 추세 그래프로 표현",
    }

    rows = []
    for p in files:
        rows.append({
            "file": p.name,
            "path": str(p.relative_to(ROOT)),
            "purpose": descriptions.get(p.name, ""),
            "recommended_use": "presentation_main",
        })

    out = pd.DataFrame(rows)
    out_path = TABLES / "main_final_visualization_v2_index.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"    저장: {out_path}")


def main() -> None:
    print("=" * 80)
    print("make_final_visualization_addons_v2.py 실행 시작")
    print("=" * 80)

    print("[1] 데이터 로드")
    ts = load_strategy_timeseries()
    period_summary = load_period_summary()
    macro_joined = load_macro_joined()
    macro = load_macro_sensitivity()

    print("[2] 개선 시각화 생성")
    plot_experiment_flow_diagram_v2()
    plot_hsi_macro_overlap_timeline_v2(macro_joined)
    plot_period_cagr_heatmap_v2(period_summary)
    plot_hsi_state_yearly_share_v2(ts)
    plot_macro_sensitivity_small_multiples_v2(macro)

    target_names = [
        "main_final_experiment_flow_diagram_v2.png",
        "main_final_hsi_macro_overlap_timeline_v2.png",
        "main_final_benchmark_alignment_period_cagr_heatmap_v2.png",
        "main_final_hsi_state_yearly_share_v2.png",
        "main_final_lambda_macro_sensitivity_small_multiples_v2.png",
    ]
    target_paths = [FIGURES / n for n in target_names if (FIGURES / n).exists()]

    print("[3] v2 인덱스 저장")
    write_visual_index_v2(target_paths)

    print("\n[생성/갱신 대상]")
    for p in target_paths:
        print(f"    {p}")

    print("=" * 80)
    print("make_final_visualization_addons_v2.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
