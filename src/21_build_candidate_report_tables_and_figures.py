from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


TITLE = "21_build_candidate_report_tables_and_figures.py"


def print_header(message: str) -> None:
    print("=" * 80)
    print(message)
    print("=" * 80)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent if HERE.name == "src" else HERE
OUTPUT_TABLES = PROJECT_ROOT / "output" / "tables"
OUTPUT_FIGURES = PROJECT_ROOT / "output" / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Fallback when executed outside project tree.
if not OUTPUT_TABLES.exists():
    PROJECT_ROOT = HERE
    OUTPUT_TABLES = PROJECT_ROOT / "output" / "tables"
    OUTPUT_FIGURES = PROJECT_ROOT / "output" / "figures"
    DOCS_DIR = PROJECT_ROOT / "docs"
    PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ensure_dir(OUTPUT_TABLES)
ensure_dir(OUTPUT_FIGURES)
ensure_dir(DOCS_DIR)
ensure_dir(PROCESSED_DIR)


JUDGEMENT_PATH = OUTPUT_TABLES / "main_final_candidate_final_judgement.csv"
COST_PATH = OUTPUT_TABLES / "main_final_candidate_all_cost_sensitivity.csv"
SUMMARY_PATH = OUTPUT_TABLES / "main_final_candidate_selection_summary.csv"

def find_backtest_timeseries_files() -> list[Path]:
    """
    05~11번의 백테스트 시계열 파일은 보통 data/processed에 저장된다.
    예전 초안은 output/tables만 탐색했기 때문에 파일을 찾지 못할 수 있다.
    이 함수는 data/processed와 output/tables를 모두 탐색한다.
    """
    candidates: list[Path] = []

    search_dirs = [PROCESSED_DIR, OUTPUT_TABLES]
    patterns = [
        "main_final_*backtest_timeseries.csv",
        "main_final_*backtest_ts.csv",
        "main_final_*timeseries.csv",
    ]

    for directory in search_dirs:
        if not directory.exists():
            continue
        for pattern in patterns:
            candidates.extend(directory.glob(pattern))

    unique = {p.resolve(): p for p in candidates}
    return sorted(unique.values(), key=lambda p: p.name)


BACKTEST_TS_FILES = find_backtest_timeseries_files()

PERCENT_COLS = [
    "CAGR_pct",
    "MDD_pct",
    "avg_turnover_pct",
    "max_turnover_pct",
    "CAGR_cost_drag_20bp_pct",
]
ROUND_3_COLS = ["Sharpe", "Calmar", "selection_score", "Sortino"]


def detect_date_col(df: pd.DataFrame) -> Optional[str]:
    candidates = [
        "year_month",
        "date",
        "month_end",
        "rebalance_month",
        "month",
        "signal_month",
    ]
    for col in candidates:
        if col in df.columns:
            return col
    return None


RETURN_COL_CANDIDATES = [
    "strategy_return_after_cost",
    "strategy_return_after_cost_10bp",
    "strategy_return_net",
    "strategy_return",
    "portfolio_return",
    "net_return",
    "monthly_return",
    "return",
]

CUM_COL_CANDIDATES = [
    "portfolio_nav",
    "nav",
    "cumulative_nav",
    "cumulative_wealth",
    "wealth_index",
    "cum_return_index",
    "cumulative_return_index",
]

TURNOVER_COL_CANDIDATES = [
    "turnover",
    "monthly_turnover",
    "turnover_ratio",
]

DRAWDOWN_COL_CANDIDATES = [
    "drawdown",
    "portfolio_drawdown",
    "dd",
]


def first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def parse_month_like(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    if len(text) == 7 and text.count("-") == 1:
        text = f"{text}-01"
    return pd.to_datetime(text, errors="coerce")


SOURCE_MAP = {
    "main_final_baseline_backtest_timeseries.csv": "baseline",
    "main_final_event_balance_filter_backtest_timeseries.csv": "event_balance_filter",
    "main_final_lambda_backtest_timeseries.csv": "lambda",
    "main_final_signal_combo_backtest_timeseries.csv": "signal_combo",
    "main_final_theta_backtest_timeseries.csv": "theta",
}


def pretty_strategy_name(row: pd.Series) -> str:
    strategy = str(row.get("strategy_name", "unknown"))
    source = str(row.get("source_type", ""))
    if strategy == "EW":
        return "EW (Benchmark)"
    if strategy == "HSI_final_baseline_overlay":
        return "HSI Baseline"
    if strategy == "HSI_event_balance_filter_overlay":
        return "HSI + Event Filter"
    if source == "lambda" and strategy.startswith("lambda_"):
        return strategy.replace("lambda_", "Lambda ")
    if source == "theta" and strategy.startswith("theta_"):
        return strategy.replace("theta_", "Theta ")
    return strategy



def load_judgement() -> pd.DataFrame:
    if not JUDGEMENT_PATH.exists():
        raise FileNotFoundError(f"판단표를 찾을 수 없습니다: {JUDGEMENT_PATH}")
    df = pd.read_csv(JUDGEMENT_PATH)
    if "source_type" not in df.columns:
        df["source_type"] = "unknown"
    df["report_strategy_name"] = df.apply(pretty_strategy_name, axis=1)
    return df


def load_cost() -> pd.DataFrame:
    if not COST_PATH.exists():
        raise FileNotFoundError(f"거래비용 민감도 표를 찾을 수 없습니다: {COST_PATH}")
    df = pd.read_csv(COST_PATH)
    if "source_type" not in df.columns:
        df["source_type"] = "unknown"
    if "strategy_name" in df.columns:
        df["report_strategy_name"] = df.apply(pretty_strategy_name, axis=1)
    return df


def load_all_timeseries() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in BACKTEST_TS_FILES:
        df = pd.read_csv(path)
        df["source_file"] = path.name
        df["source_type"] = SOURCE_MAP.get(path.name, path.stem)
        if "strategy_name" not in df.columns:
            if df["source_type"].iloc[0] == "baseline":
                df["strategy_name"] = "HSI_final_baseline_overlay"
            else:
                df["strategy_name"] = path.stem
        date_col = detect_date_col(df)
        if date_col is not None:
            df["report_date"] = df[date_col].map(parse_month_like)
        else:
            df["report_date"] = pd.NaT
        frames.append(df)
    if not frames:
        raise FileNotFoundError(
            "백테스트 시계열 파일을 찾지 못했습니다. "
            f"탐색 위치: {PROCESSED_DIR}, {OUTPUT_TABLES}"
        )
    combined = pd.concat(frames, ignore_index=True)
    combined["report_strategy_name"] = combined.apply(pretty_strategy_name, axis=1)
    return combined


def make_core_comparison_table(judgement: pd.DataFrame) -> pd.DataFrame:
    keep = judgement.copy()
    order_map = {
        "final_candidate": 0,
        "reserve_candidate": 1,
        "review_robustness": 2,
        "review_cost_sensitive": 3,
        "exclude_risk_metric": 4,
        "exclude_turnover": 5,
        "benchmark": 6,
    }
    keep["_order"] = keep["final_decision"].map(order_map).fillna(99)
    keep = keep.sort_values(["_order", "selection_score"], ascending=[True, False])
    cols = [
        "final_decision",
        "source_type",
        "strategy_name",
        "report_strategy_name",
        "combo_id",
        "theta_common",
        "lambda_value",
        "CAGR_pct",
        "MDD_pct",
        "Sharpe",
        "Calmar",
        "avg_turnover_pct",
        "max_turnover_pct",
        "CAGR_cost_drag_20bp_pct",
        "selection_score",
        "decision_reason",
    ]
    cols = [c for c in cols if c in keep.columns]
    keep = keep[cols].copy()
    return keep


def make_candidate_shortlist(judgement: pd.DataFrame) -> pd.DataFrame:
    shortlist = judgement[judgement["final_decision"].isin(["final_candidate", "reserve_candidate", "benchmark"])].copy()
    if shortlist.empty:
        shortlist = judgement.nlargest(5, "selection_score").copy()
    # keep one benchmark row
    if "benchmark" in shortlist["final_decision"].values:
        bench = shortlist[shortlist["final_decision"] == "benchmark"].head(1)
        non_bench = shortlist[shortlist["final_decision"] != "benchmark"]
        shortlist = pd.concat([non_bench, bench], ignore_index=True)
    return shortlist


def make_cost_pivot(cost_df: pd.DataFrame, shortlist: pd.DataFrame) -> pd.DataFrame:
    cost_rate_col = None
    for c in ["cost_label", "cost_rate_label", "cost_scenario", "cost_name"]:
        if c in cost_df.columns:
            cost_rate_col = c
            break
    if cost_rate_col is None:
        if "cost_rate" in cost_df.columns:
            cost_df = cost_df.copy()
            cost_df["cost_label"] = cost_df["cost_rate"].map(
                lambda x: {0.0: "0.00%", 0.0005: "0.05%", 0.001: "0.10%", 0.002: "0.20%"}.get(round(float(x), 4), str(x))
            )
            cost_rate_col = "cost_label"
        else:
            raise KeyError("거래비용 민감도 표에서 cost label 컬럼을 찾지 못했습니다.")

    selected_names = set(shortlist["strategy_name"].astype(str))
    selected_sources = set(shortlist.get("source_type", pd.Series(dtype=str)).astype(str))
    mask = cost_df["strategy_name"].astype(str).isin(selected_names)
    if "source_type" in cost_df.columns and selected_sources:
        mask &= cost_df["source_type"].astype(str).isin(selected_sources)
    view = cost_df.loc[mask].copy()
    value_col = None
    for c in [
        "CAGR_after_cost_pct",
        "CAGR_net_pct",
        "CAGR_pct_after_cost",
        "CAGR_pct",  # 20번 cost sensitivity 표에서는 비용 반영 후 CAGR도 이 이름으로 저장된다.
    ]:
        if c in view.columns:
            value_col = c
            break
    if value_col is None:
        raise KeyError(
            "거래비용 반영 CAGR 컬럼을 찾지 못했습니다. "
            f"현재 컬럼: {view.columns.tolist()}"
        )

    pivot = view.pivot_table(
        index=["source_type", "strategy_name", "report_strategy_name"],
        columns=cost_rate_col,
        values=value_col,
        aggfunc="first",
    ).reset_index()
    return pivot


def prepare_timeseries_subset(all_ts: pd.DataFrame, shortlist: pd.DataFrame) -> pd.DataFrame:
    selected = shortlist[["source_type", "strategy_name", "report_strategy_name"]].drop_duplicates().copy()
    merged = all_ts.merge(selected, on=["source_type", "strategy_name", "report_strategy_name"], how="inner")

    ret_col = first_existing(merged, RETURN_COL_CANDIDATES)
    cum_col = first_existing(merged, CUM_COL_CANDIDATES)
    dd_col = first_existing(merged, DRAWDOWN_COL_CANDIDATES)
    turnover_col = first_existing(merged, TURNOVER_COL_CANDIDATES)

    if ret_col is None:
        raise KeyError("백테스트 시계열에서 수익률 컬럼을 찾지 못했습니다.")

    merged = merged.sort_values(["report_strategy_name", "report_date"]).copy()

    if cum_col is None:
        merged["report_cumulative_nav"] = merged.groupby("report_strategy_name")[ret_col].transform(lambda s: (1 + s.fillna(0)).cumprod())
    else:
        merged["report_cumulative_nav"] = merged[cum_col]

    if dd_col is None:
        merged["report_drawdown"] = merged.groupby("report_strategy_name")["report_cumulative_nav"].transform(lambda s: s / s.cummax() - 1)
    else:
        merged["report_drawdown"] = merged[dd_col]

    merged["report_return"] = merged[ret_col]
    merged["report_turnover"] = merged[turnover_col] if turnover_col is not None else np.nan
    return merged


def save_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"    저장: {path}")


def plot_cumulative(ts: pd.DataFrame, out_path: Path) -> None:
    plt.figure(figsize=(11, 6.2))
    for name, g in ts.groupby("report_strategy_name"):
        plt.plot(g["report_date"], g["report_cumulative_nav"], label=name, linewidth=2)
    plt.title("Final Candidate vs Benchmark: Cumulative NAV")
    plt.xlabel("Date")
    plt.ylabel("Cumulative NAV")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_drawdown(ts: pd.DataFrame, out_path: Path) -> None:
    plt.figure(figsize=(11, 6.2))
    for name, g in ts.groupby("report_strategy_name"):
        plt.plot(g["report_date"], g["report_drawdown"] * 100, label=name, linewidth=2)
    plt.title("Final Candidate vs Benchmark: Drawdown")
    plt.xlabel("Date")
    plt.ylabel("Drawdown (%)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_turnover(shortlist: pd.DataFrame, out_path: Path) -> None:
    plot_df = shortlist[shortlist["final_decision"] != "benchmark"].copy()
    if plot_df.empty:
        plot_df = shortlist.copy()
    labels = plot_df["report_strategy_name"].tolist()
    x = np.arange(len(labels))
    width = 0.36
    plt.figure(figsize=(10, 5.8))
    plt.bar(x - width / 2, plot_df["avg_turnover_pct"], width=width, label="Average Turnover (%)")
    plt.bar(x + width / 2, plot_df["max_turnover_pct"], width=width, label="Max Turnover (%)")
    plt.xticks(x, labels, rotation=15)
    plt.ylabel("Turnover (%)")
    plt.title("Turnover Comparison of Final Candidates")
    plt.legend()
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_cost_drag(shortlist: pd.DataFrame, out_path: Path) -> None:
    plot_df = shortlist[shortlist["final_decision"] != "benchmark"].copy()
    if plot_df.empty:
        plot_df = shortlist.copy()
    plt.figure(figsize=(10, 5.6))
    plt.bar(plot_df["report_strategy_name"], plot_df["CAGR_cost_drag_20bp_pct"], width=0.6)
    plt.ylabel("CAGR drag at 0.20% cost (%p)")
    plt.title("Cost Sensitivity of Final Candidates")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_risk_return(shortlist: pd.DataFrame, out_path: Path) -> None:
    plt.figure(figsize=(8.5, 6.5))
    plt.scatter(shortlist["MDD_pct"].abs(), shortlist["CAGR_pct"], s=90)
    for _, row in shortlist.iterrows():
        plt.annotate(row["report_strategy_name"], (abs(row["MDD_pct"]), row["CAGR_pct"]), xytext=(6, 4), textcoords="offset points")
    plt.xlabel("Absolute MDD (%)")
    plt.ylabel("CAGR (%)")
    plt.title("Risk-Return View of Final Candidates")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_lambda_family(judgement: pd.DataFrame, out_path: Path) -> None:
    lam = judgement[judgement["source_type"] == "lambda"].copy()
    if lam.empty:
        return
    lam = lam.sort_values("lambda_value")
    x = np.arange(len(lam))
    width = 0.38
    fig, ax1 = plt.subplots(figsize=(11, 6.5))
    ax1.bar(x - width / 2, lam["CAGR_pct"], width=width, label="CAGR (%)")
    ax1.bar(x + width / 2, lam["avg_turnover_pct"], width=width, label="Avg Turnover (%)")
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"lambda={v:.1f}" for v in lam["lambda_value"]])
    ax1.set_ylabel("Value")
    ax1.set_title("Lambda Family Comparison")
    ax1.grid(True, axis="y", alpha=0.3)
    ax1.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def build_markdown_note(shortlist: pd.DataFrame, paths: dict[str, Path]) -> str:
    lines: list[str] = []
    lines.append("# Final Candidate Report Pack Note")
    lines.append("")
    lines.append("이 문서는 20번 최종 후보 셀렉 결과를 보고서용 표와 시각화 자료로 정리하기 위한 메모이다.")
    lines.append("")
    lines.append("## 1. 본문에 바로 넣기 좋은 표")
    lines.append("")
    lines.append("1. `main_final_report_candidate_comparison_table.csv`")
    lines.append("   - 최종 후보, 보류 후보, benchmark를 한 표에서 비교하는 핵심 표")
    lines.append("2. `main_final_report_candidate_cost_pivot.csv`")
    lines.append("   - 거래비용률 0.00%, 0.05%, 0.10%, 0.20%에서 후보별 CAGR 변화를 비교하는 표")
    lines.append("3. `main_final_report_lambda_family_table.csv`")
    lines.append("   - λ 실험 전체를 한 표로 비교하는 보조 표")
    lines.append("")
    lines.append("## 2. 본문 그림 추천 배치")
    lines.append("")
    lines.append("- Fig. 1 `main_final_report_cumulative_comparison.png`")
    lines.append("  - EW, HSI baseline, 최종 후보들의 누적 성과 흐름 비교")
    lines.append("- Fig. 2 `main_final_report_drawdown_comparison.png`")
    lines.append("  - 후보별 최대낙폭과 회복 경로 비교")
    lines.append("- Fig. 3 `main_final_report_turnover_comparison.png`")
    lines.append("  - 평균/최대 Turnover 비교")
    lines.append("- Fig. 4 `main_final_report_cost_drag_comparison.png`")
    lines.append("  - 보수적 비용 가정(0.20%)에서 CAGR 훼손 정도 비교")
    lines.append("- Fig. 5 `main_final_report_risk_return_scatter.png`")
    lines.append("  - 절대 MDD와 CAGR의 위치 비교")
    lines.append("- Fig. 6 `main_final_report_lambda_family_comparison.png`")
    lines.append("  - λ별 CAGR과 평균 Turnover 비교")
    lines.append("")
    lines.append("## 3. 해석 메모")
    lines.append("")
    finals = shortlist[shortlist["final_decision"] == "final_candidate"]
    if not finals.empty:
        lines.append("현재 최종 후보로 분류된 전략은 다음과 같다.")
        lines.append("")
        for _, row in finals.iterrows():
            lines.append(
                f"- **{row['report_strategy_name']}**: CAGR {row['CAGR_pct']:.2f}%, "
                f"MDD {row['MDD_pct']:.2f}%, Sharpe {row['Sharpe']:.3f}, "
                f"Calmar {row['Calmar']:.3f}, 평균 Turnover {row['avg_turnover_pct']:.2f}%"
            )
        lines.append("")
    lines.append("## 4. 보고서 문장 예시")
    lines.append("")
    lines.append(
        "최종 후보 선별 결과, 대부분의 baseline·signal combo·theta 전략은 Turnover 기준을 통과하지 못하였다. "
        "반면 λ 부분조정 실험에서 도출된 일부 후보는 Turnover, 거래비용 민감도, MDD, Sharpe, Calmar 기준을 함께 통과하였다. "
        "이는 HSI 상태분류를 목표 비중에 즉시 반영하기보다, 비중 전환 속도를 조절하는 부분조정 구조와 결합할 때 방어형 overlay 전략의 안정성이 개선될 수 있음을 시사한다."
    )
    lines.append("")
    lines.append("## 5. 생성 파일")
    lines.append("")
    for key, path in paths.items():
        lines.append(f"- `{path.as_posix()}`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    print_header(f"{TITLE} 실행 시작")

    print("[1] 후보 판단표 로드")
    judgement = load_judgement()
    cost = load_cost()
    all_ts = load_all_timeseries()
    print(f"    판단표: {judgement.shape}")
    print(f"    비용표: {cost.shape}")
    print(f"    시계열: {all_ts.shape}")

    print("[2] 보고서용 핵심 표 생성")
    core_table = make_core_comparison_table(judgement)
    shortlist = make_candidate_shortlist(judgement)
    cost_pivot = make_cost_pivot(cost, shortlist)
    lambda_table = judgement[judgement["source_type"] == "lambda"].copy().sort_values("lambda_value")

    core_path = OUTPUT_TABLES / "main_final_report_candidate_comparison_table.csv"
    shortlist_path = OUTPUT_TABLES / "main_final_report_candidate_shortlist.csv"
    cost_pivot_path = OUTPUT_TABLES / "main_final_report_candidate_cost_pivot.csv"
    lambda_table_path = OUTPUT_TABLES / "main_final_report_lambda_family_table.csv"

    save_csv(core_table, core_path)
    save_csv(shortlist, shortlist_path)
    save_csv(cost_pivot, cost_pivot_path)
    if not lambda_table.empty:
        save_csv(lambda_table, lambda_table_path)

    print("[3] 비교 시계열 정리")
    expanded_shortlist = shortlist.copy()
    # Ensure baseline comparison included.
    baseline_extra = judgement[
        (judgement["strategy_name"] == "HSI_final_baseline_overlay")
        & (judgement["source_type"] == "baseline")
    ].copy()
    bench_extra = judgement[judgement["final_decision"] == "benchmark"].head(1).copy()
    expanded_shortlist = pd.concat([expanded_shortlist, baseline_extra, bench_extra], ignore_index=True).drop_duplicates(
        subset=["source_type", "strategy_name"]
    )
    ts_subset = prepare_timeseries_subset(all_ts, expanded_shortlist)
    ts_path = OUTPUT_TABLES / "main_final_report_candidate_timeseries_subset.csv"
    save_csv(ts_subset, ts_path)

    print("[4] 보고서용 그림 생성")
    fig_paths = {
        "cumulative": OUTPUT_FIGURES / "main_final_report_cumulative_comparison.png",
        "drawdown": OUTPUT_FIGURES / "main_final_report_drawdown_comparison.png",
        "turnover": OUTPUT_FIGURES / "main_final_report_turnover_comparison.png",
        "cost_drag": OUTPUT_FIGURES / "main_final_report_cost_drag_comparison.png",
        "risk_return": OUTPUT_FIGURES / "main_final_report_risk_return_scatter.png",
        "lambda_family": OUTPUT_FIGURES / "main_final_report_lambda_family_comparison.png",
    }
    plot_cumulative(ts_subset, fig_paths["cumulative"])
    print(f"    저장: {fig_paths['cumulative']}")
    plot_drawdown(ts_subset, fig_paths["drawdown"])
    print(f"    저장: {fig_paths['drawdown']}")
    plot_turnover(shortlist, fig_paths["turnover"])
    print(f"    저장: {fig_paths['turnover']}")
    plot_cost_drag(shortlist, fig_paths["cost_drag"])
    print(f"    저장: {fig_paths['cost_drag']}")
    plot_risk_return(shortlist, fig_paths["risk_return"])
    print(f"    저장: {fig_paths['risk_return']}")
    plot_lambda_family(judgement, fig_paths["lambda_family"])
    print(f"    저장: {fig_paths['lambda_family']}")

    print("[5] 보고서용 메모 저장")
    note_paths = {
        "core_table": core_path,
        "shortlist": shortlist_path,
        "cost_pivot": cost_pivot_path,
        "lambda_table": lambda_table_path,
        "timeseries_subset": ts_path,
        **fig_paths,
    }
    note_text = build_markdown_note(shortlist, note_paths)
    note_path = DOCS_DIR / "main_final_candidate_report_pack_note.md"
    note_path.write_text(note_text, encoding="utf-8")
    print(f"    저장: {note_path}")

    print("\n[최종 후보 shortlist]")
    show_cols = [
        "final_decision",
        "source_type",
        "report_strategy_name",
        "CAGR_pct",
        "MDD_pct",
        "Sharpe",
        "Calmar",
        "avg_turnover_pct",
        "max_turnover_pct",
        "CAGR_cost_drag_20bp_pct",
    ]
    show_cols = [c for c in show_cols if c in shortlist.columns]
    print(shortlist[show_cols].to_string(index=False))

    print_header(f"{TITLE} 실행 완료")


if __name__ == "__main__":
    main()
