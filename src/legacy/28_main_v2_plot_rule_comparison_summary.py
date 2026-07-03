from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


"""
28_main_v2_plot_rule_comparison_summary.py

목적
----
main_v2와 main_v2b의 규칙 비교 결과를 시각화한다.

질문
----
conflict를 방어로 처리한 main_v2와
conflict를 관찰로 처리한 main_v2b 중
어느 규칙이 더 안정적인가?

입력
----
output/tables/main_v2_rule_comparison_summary.csv
output/tables/main_v2_rule_comparison_comment.csv

출력
----
output/figures/main_v2_fig6_rule_comparison_summary_rank.png
output/figures/main_v2_fig6_rule_comparison_summary_zscore.png
output/tables/main_v2_fig6_rule_comparison_plot_data.csv
docs/main_v2_fig6_rule_comparison_note.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
FIGURE_DIR = PROJECT_ROOT / "output" / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_SUMMARY_PATH = TABLE_DIR / "main_v2_rule_comparison_summary.csv"
INPUT_COMMENT_PATH = TABLE_DIR / "main_v2_rule_comparison_comment.csv"

OUTPUT_FIGURE_RANK_PATH = FIGURE_DIR / "main_v2_fig6_rule_comparison_summary_rank.png"
OUTPUT_FIGURE_ZSCORE_PATH = FIGURE_DIR / "main_v2_fig6_rule_comparison_summary_zscore.png"
OUTPUT_PLOT_DATA_PATH = TABLE_DIR / "main_v2_fig6_rule_comparison_plot_data.csv"
OUTPUT_NOTE_PATH = DOCS_DIR / "main_v2_fig6_rule_comparison_note.md"


# ============================================================
# 1. 표시 설정
# ============================================================

EXPERIMENT_LABEL_MAP = {
    "EW": "EW",
    "main_v2_conflict_defense": "main_v2\nconflict 방어",
    "main_v2b_conflict_watch": "main_v2b\nconflict 관찰",
}


def set_korean_font() -> None:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


# ============================================================
# 2. 데이터 로드
# ============================================================

def load_summary() -> pd.DataFrame:
    if not INPUT_SUMMARY_PATH.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {INPUT_SUMMARY_PATH}")

    df = pd.read_csv(INPUT_SUMMARY_PATH)

    required_cols = [
        "method",
        "experiment",
        "total_return",
        "cagr",
        "annual_volatility",
        "sharpe",
        "mdd",
        "calmar",
        "avg_turnover",
    ]

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"필요한 컬럼이 없습니다: {missing}")

    df["experiment_label"] = df["experiment"].map(EXPERIMENT_LABEL_MAP)
    df["total_return_pct"] = df["total_return"] * 100
    df["cagr_pct"] = df["cagr"] * 100
    df["annual_volatility_pct"] = df["annual_volatility"] * 100
    df["mdd_pct"] = df["mdd"] * 100

    return df


# ============================================================
# 3. 그래프 생성
# ============================================================

def plot_rule_comparison(plot_data: pd.DataFrame, method: str, output_path: Path) -> None:
    set_korean_font()

    method_data = plot_data[plot_data["method"] == method].copy()

    if method_data.empty:
        raise ValueError(f"{method} 데이터가 없습니다.")

    order = [
        "EW",
        "main_v2_conflict_defense",
        "main_v2b_conflict_watch",
    ]

    method_data["experiment"] = pd.Categorical(
        method_data["experiment"],
        categories=order,
        ordered=True,
    )

    method_data = method_data.sort_values("experiment")

    labels = method_data["experiment_label"].tolist()

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    metrics = [
        ("total_return_pct", "총수익률 (%)"),
        ("mdd_pct", "MDD (%)"),
        ("sharpe", "Sharpe"),
        ("avg_turnover", "평균 Turnover"),
    ]

    for ax, (metric, title) in zip(axes.flatten(), metrics):
        ax.bar(labels, method_data[metric])
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.3)

        for i, value in enumerate(method_data[metric]):
            if metric in ["total_return_pct", "mdd_pct"]:
                text = f"{value:.2f}%"
            else:
                text = f"{value:.4f}"
            ax.text(i, value, text, ha="center", va="bottom" if value >= 0 else "top", fontsize=9)

    fig.suptitle(f"Fig.6 규칙 비교 요약 ({method})", fontsize=15)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


# ============================================================
# 4. 해석 노트 생성
# ============================================================

def make_note(plot_data: pd.DataFrame) -> str:
    lines = []

    lines.append("# Fig.6 규칙 비교 요약 해석 노트")
    lines.append("")
    lines.append("## 그림의 질문")
    lines.append("")
    lines.append("conflict를 방어로 처리한 main_v2와 conflict를 관찰로 처리한 main_v2b 중 어느 규칙이 더 안정적인가?")
    lines.append("")
    lines.append("## 핵심 비교")
    lines.append("")
    lines.append("| method | experiment | 총수익률 | CAGR | MDD | Sharpe | 평균 Turnover |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")

    display = plot_data[
        [
            "method",
            "experiment",
            "total_return_pct",
            "cagr_pct",
            "mdd_pct",
            "sharpe",
            "avg_turnover",
        ]
    ].copy()

    for _, row in display.iterrows():
        lines.append(
            f"| {row['method']} | {row['experiment']} | "
            f"{row['total_return_pct']:.2f}% | "
            f"{row['cagr_pct']:.2f}% | "
            f"{row['mdd_pct']:.2f}% | "
            f"{row['sharpe']:.4f} | "
            f"{row['avg_turnover']:.4f} |"
        )

    lines.append("")
    lines.append("## 해석")
    lines.append("")
    lines.append(
        "main_v2는 conflict 상태를 소폭 방어로 처리한 규칙이고, "
        "main_v2b는 conflict 상태를 관찰 상태로 처리한 규칙이다."
    )
    lines.append(
        "이 비교는 HSI 상태명과 실제 포트폴리오 행동을 분리해서 설계해야 함을 보여준다."
    )
    lines.append(
        "conflict는 위험 악화가 확정된 상태라기보다 위험 완화 신호와 위험 악화 신호가 동시에 나타나는 혼조 상태이므로, "
        "즉시 방어전환하기보다 관찰 상태로 처리하는 규칙이 불필요한 Turnover를 줄일 수 있다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 5. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("28_main_v2_plot_rule_comparison_summary.py 실행 시작")
    print("=" * 70)

    plot_data = load_summary()
    plot_data.to_csv(OUTPUT_PLOT_DATA_PATH, index=False, encoding="utf-8-sig")

    plot_rule_comparison(plot_data, method="rank", output_path=OUTPUT_FIGURE_RANK_PATH)
    plot_rule_comparison(plot_data, method="zscore", output_path=OUTPUT_FIGURE_ZSCORE_PATH)

    note = make_note(plot_data)
    OUTPUT_NOTE_PATH.write_text(note, encoding="utf-8")

    print("[저장 완료]")
    print(f"- {OUTPUT_FIGURE_RANK_PATH}")
    print(f"- {OUTPUT_FIGURE_ZSCORE_PATH}")
    print(f"- {OUTPUT_PLOT_DATA_PATH}")
    print(f"- {OUTPUT_NOTE_PATH}")

    print("\n[규칙 비교 데이터]")
    display_cols = [
        "method",
        "experiment",
        "rule_description",
        "total_return_pct",
        "cagr_pct",
        "annual_volatility_pct",
        "sharpe",
        "mdd_pct",
        "calmar",
        "avg_turnover",
    ]
    display_cols = [col for col in display_cols if col in plot_data.columns]
    print(plot_data[display_cols])

    print("\n" + "=" * 70)
    print("28_main_v2_plot_rule_comparison_summary.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()