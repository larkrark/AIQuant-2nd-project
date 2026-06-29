from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


"""
26_main_v2_plot_drawdown.py

목적
----
EW, main_v2, main_v2b의 Drawdown을 비교한다.

질문
----
HSI 5상태 overlay는 단순 동일비중 대비 낙폭을 줄였는가?
그리고 conflict를 관찰로 처리한 main_v2b는
conflict를 방어로 처리한 main_v2보다 Drawdown 측면에서 나은가?

입력
----
output/tables/main_v2_drawdown_timeseries.csv
output/tables/main_v2b_drawdown_timeseries.csv

출력
----
output/figures/main_v2_fig3_drawdown_comparison_rank.png
output/figures/main_v2_fig3_drawdown_comparison_zscore.png
output/tables/main_v2_fig3_drawdown_plot_data.csv
docs/main_v2_fig3_drawdown_note.md
"""


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
FIGURE_DIR = PROJECT_ROOT / "output" / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

MAIN_V2_PATH = TABLE_DIR / "main_v2_drawdown_timeseries.csv"
MAIN_V2B_PATH = TABLE_DIR / "main_v2b_drawdown_timeseries.csv"

OUTPUT_FIGURE_RANK_PATH = FIGURE_DIR / "main_v2_fig3_drawdown_comparison_rank.png"
OUTPUT_FIGURE_ZSCORE_PATH = FIGURE_DIR / "main_v2_fig3_drawdown_comparison_zscore.png"
OUTPUT_PLOT_DATA_PATH = TABLE_DIR / "main_v2_fig3_drawdown_plot_data.csv"
OUTPUT_NOTE_PATH = DOCS_DIR / "main_v2_fig3_drawdown_note.md"


def set_korean_font() -> None:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


STRATEGY_LABEL_MAP = {
    "EW": "EW",
    "HSI_state5_overlay": "main_v2: conflict 방어",
    "HSI_state5_overlay_v2b": "main_v2b: conflict 관찰",
}


def read_csv_with_date(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    df = pd.read_csv(path)

    if "Date" not in df.columns:
        raise ValueError(f"Date 컬럼이 없습니다: {path}")

    df["Date"] = pd.to_datetime(df["Date"])
    return df


def load_and_prepare_data() -> pd.DataFrame:
    main_v2 = read_csv_with_date(MAIN_V2_PATH)
    main_v2b = read_csv_with_date(MAIN_V2B_PATH)

    main_v2["experiment"] = main_v2["strategy"].map(
        {
            "EW": "EW",
            "HSI_state5_overlay": "main_v2_conflict_defense",
        }
    )

    main_v2b["experiment"] = main_v2b["strategy"].map(
        {
            "EW": "EW",
            "HSI_state5_overlay_v2b": "main_v2b_conflict_watch",
        }
    )

    combined = pd.concat([main_v2, main_v2b], ignore_index=True)

    combined = combined.drop_duplicates(
        subset=["Date", "method", "experiment"],
        keep="first",
    ).reset_index(drop=True)

    combined["display_name"] = combined["strategy"].map(STRATEGY_LABEL_MAP)
    combined["drawdown_pct"] = combined["drawdown"] * 100

    required_cols = [
        "Date",
        "method",
        "strategy",
        "experiment",
        "display_name",
        "monthly_return",
        "cumulative_return",
        "drawdown",
        "drawdown_pct",
    ]

    existing_cols = [col for col in required_cols if col in combined.columns]
    return combined[existing_cols].copy()


def plot_drawdown(plot_data: pd.DataFrame, method: str, output_path: Path) -> None:
    set_korean_font()

    method_data = plot_data[plot_data["method"] == method].copy()

    if method_data.empty:
        raise ValueError(f"{method} 데이터가 없습니다.")

    plt.figure(figsize=(12, 6))

    order = [
        "EW",
        "main_v2_conflict_defense",
        "main_v2b_conflict_watch",
    ]

    for experiment in order:
        temp = method_data[method_data["experiment"] == experiment].sort_values("Date")

        if temp.empty:
            continue

        label = temp["display_name"].iloc[0]

        plt.plot(
            temp["Date"],
            temp["drawdown_pct"],
            label=label,
            linewidth=2,
        )

    plt.axhline(0, linewidth=1)
    plt.title(f"Fig.3 Drawdown 비교 ({method})", fontsize=14)
    plt.xlabel("Date")
    plt.ylabel("Drawdown (%)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def make_note(plot_data: pd.DataFrame) -> str:
    mdd_summary = (
        plot_data
        .groupby(["method", "experiment", "display_name"], dropna=False)
        .agg(
            mdd=("drawdown", "min"),
            mdd_pct=("drawdown_pct", "min"),
        )
        .reset_index()
        .sort_values(["method", "experiment"])
    )

    lines = []

    lines.append("# Fig.3 Drawdown 비교 해석 노트")
    lines.append("")
    lines.append("## 그림의 질문")
    lines.append("")
    lines.append(
        "HSI 5상태 overlay는 단순 동일비중 대비 낙폭을 줄였는가?"
    )
    lines.append("")
    lines.append("## MDD 요약")
    lines.append("")
    lines.append("| method | 전략 | MDD | MDD(%) |")
    lines.append("|---|---|---:|---:|")

    for _, row in mdd_summary.iterrows():
        lines.append(
            f"| {row['method']} | {row['display_name']} | "
            f"{row['mdd']:.6f} | {row['mdd_pct']:.2f}% |"
        )

    lines.append("")
    lines.append("## 해석")
    lines.append("")
    lines.append(
        "Drawdown은 누적수익률이 이전 고점 대비 얼마나 하락했는지를 보여주는 지표이다."
    )
    lines.append(
        "방어형 overlay 전략에서는 최종 누적수익률뿐 아니라 Drawdown과 MDD를 함께 확인해야 한다."
    )
    lines.append(
        "main_v2와 main_v2b의 차이는 conflict 상태를 방어로 처리할지, 관찰로 처리할지에 있다."
    )
    lines.append(
        "main_v2b의 MDD가 main_v2보다 개선된다면, conflict를 즉시 방어전환으로 처리하기보다 "
        "관찰 상태로 두는 것이 낙폭 관리 측면에서도 더 자연스러울 수 있다."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("=" * 70)
    print("26_main_v2_plot_drawdown.py 실행 시작")
    print("=" * 70)

    plot_data = load_and_prepare_data()

    plot_data.to_csv(OUTPUT_PLOT_DATA_PATH, index=False, encoding="utf-8-sig")

    plot_drawdown(plot_data, method="rank", output_path=OUTPUT_FIGURE_RANK_PATH)
    plot_drawdown(plot_data, method="zscore", output_path=OUTPUT_FIGURE_ZSCORE_PATH)

    note = make_note(plot_data)
    OUTPUT_NOTE_PATH.write_text(note, encoding="utf-8")

    print("[저장 완료]")
    print(f"- {OUTPUT_FIGURE_RANK_PATH}")
    print(f"- {OUTPUT_FIGURE_ZSCORE_PATH}")
    print(f"- {OUTPUT_PLOT_DATA_PATH}")
    print(f"- {OUTPUT_NOTE_PATH}")

    print("\n[MDD 요약]")
    mdd_summary = (
        plot_data
        .groupby(["method", "experiment", "display_name"], dropna=False)
        .agg(
            mdd=("drawdown", "min"),
            mdd_pct=("drawdown_pct", "min"),
        )
        .reset_index()
        .sort_values(["method", "experiment"])
    )
    print(mdd_summary)

    print("\n" + "=" * 70)
    print("26_main_v2_plot_drawdown.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()