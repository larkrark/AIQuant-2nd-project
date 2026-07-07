from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


"""
27_main_v2_plot_weights_turnover.py

목적
----
main_v2와 main_v2b의 포트폴리오 비중 변화와 Turnover를 시각화한다.

질문
----
1. HSI 상태가 실제 ETF 비중 조정으로 연결되었는가?
2. conflict를 관찰로 처리한 main_v2b는 main_v2보다 Turnover를 줄였는가?

입력
----
output/tables/main_v2_strategy_weights_rank.csv
output/tables/main_v2_strategy_weights_zscore.csv
output/tables/main_v2b_strategy_weights_rank.csv
output/tables/main_v2b_strategy_weights_zscore.csv
output/tables/main_v2_turnover_summary.csv
output/tables/main_v2b_turnover_summary.csv

출력
----
output/figures/main_v2_fig4_weight_transition_rank.png
output/figures/main_v2_fig4_weight_transition_zscore.png
output/figures/main_v2_fig5_turnover_comparison.png
output/tables/main_v2_fig4_weight_transition_plot_data.csv
output/tables/main_v2_fig5_turnover_plot_data.csv
docs/main_v2_fig4_fig5_weights_turnover_note.md
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

WEIGHTS_V2_RANK_PATH = TABLE_DIR / "main_v2_strategy_weights_rank.csv"
WEIGHTS_V2_ZSCORE_PATH = TABLE_DIR / "main_v2_strategy_weights_zscore.csv"
WEIGHTS_V2B_RANK_PATH = TABLE_DIR / "main_v2b_strategy_weights_rank.csv"
WEIGHTS_V2B_ZSCORE_PATH = TABLE_DIR / "main_v2b_strategy_weights_zscore.csv"

TURNOVER_V2_PATH = TABLE_DIR / "main_v2_turnover_summary.csv"
TURNOVER_V2B_PATH = TABLE_DIR / "main_v2b_turnover_summary.csv"

OUTPUT_WEIGHT_FIG_RANK = FIGURE_DIR / "main_v2_fig4_weight_transition_rank.png"
OUTPUT_WEIGHT_FIG_ZSCORE = FIGURE_DIR / "main_v2_fig4_weight_transition_zscore.png"
OUTPUT_TURNOVER_FIG = FIGURE_DIR / "main_v2_fig5_turnover_comparison.png"

OUTPUT_WEIGHT_PLOT_DATA = TABLE_DIR / "main_v2_fig4_weight_transition_plot_data.csv"
OUTPUT_TURNOVER_PLOT_DATA = TABLE_DIR / "main_v2_fig5_turnover_plot_data.csv"

OUTPUT_NOTE_PATH = DOCS_DIR / "main_v2_fig4_fig5_weights_turnover_note.md"


# ============================================================
# 1. 기본 설정
# ============================================================

ASSET_LABEL_MAP = {
    "069500_weight": "069500 위험자산",
    "114260_weight": "114260 채권형",
    "153130_weight": "153130 단기채권",
}

STRATEGY_LABEL_MAP = {
    "HSI_state5_overlay": "main_v2: conflict 방어",
    "HSI_state5_overlay_v2b": "main_v2b: conflict 관찰",
}


def set_korean_font() -> None:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


# ============================================================
# 2. 데이터 로드
# ============================================================

def read_csv_with_date(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    df = pd.read_csv(path)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])

    if "signal_date" in df.columns:
        df["signal_date"] = pd.to_datetime(df["signal_date"])

    return df


def load_weight_data() -> pd.DataFrame:
    v2_rank = read_csv_with_date(WEIGHTS_V2_RANK_PATH)
    v2_zscore = read_csv_with_date(WEIGHTS_V2_ZSCORE_PATH)
    v2b_rank = read_csv_with_date(WEIGHTS_V2B_RANK_PATH)
    v2b_zscore = read_csv_with_date(WEIGHTS_V2B_ZSCORE_PATH)

    v2_rank["experiment"] = "main_v2_conflict_defense"
    v2_zscore["experiment"] = "main_v2_conflict_defense"
    v2b_rank["experiment"] = "main_v2b_conflict_watch"
    v2b_zscore["experiment"] = "main_v2b_conflict_watch"

    combined = pd.concat(
        [v2_rank, v2_zscore, v2b_rank, v2b_zscore],
        ignore_index=True,
    )

    # HSI overlay 전략만 그림에 사용한다.
    combined = combined[
        combined["strategy"].isin(["HSI_state5_overlay", "HSI_state5_overlay_v2b"])
    ].copy()

    combined["display_name"] = combined["strategy"].map(STRATEGY_LABEL_MAP)

    weight_cols = ["069500_weight", "114260_weight", "153130_weight"]

    plot_data = combined.melt(
        id_vars=[
            "Date",
            "signal_date",
            "method",
            "strategy",
            "experiment",
            "display_name",
            "hsi_state5",
            "state_name_kr",
            "action",
        ],
        value_vars=weight_cols,
        var_name="asset",
        value_name="weight",
    )

    plot_data["asset_label"] = plot_data["asset"].map(ASSET_LABEL_MAP)
    plot_data["weight_pct"] = plot_data["weight"] * 100

    return plot_data


def load_turnover_data() -> pd.DataFrame:
    v2 = pd.read_csv(TURNOVER_V2_PATH)
    v2b = pd.read_csv(TURNOVER_V2B_PATH)

    v2["experiment"] = v2["strategy"].map(
        {
            "EW": "EW",
            "HSI_state5_overlay": "main_v2_conflict_defense",
        }
    )

    v2b["experiment"] = v2b["strategy"].map(
        {
            "EW": "EW",
            "HSI_state5_overlay_v2b": "main_v2b_conflict_watch",
        }
    )

    combined = pd.concat([v2, v2b], ignore_index=True)

    combined = combined.drop_duplicates(
        subset=["method", "experiment"],
        keep="first",
    ).reset_index(drop=True)

    combined["display_name"] = combined["experiment"].map(
        {
            "EW": "EW",
            "main_v2_conflict_defense": "main_v2: conflict 방어",
            "main_v2b_conflict_watch": "main_v2b: conflict 관찰",
        }
    )

    return combined


# ============================================================
# 3. 비중 변화 그래프
# ============================================================

def plot_weight_transition(weight_data: pd.DataFrame, method: str, output_path: Path) -> None:
    set_korean_font()

    method_data = weight_data[weight_data["method"] == method].copy()

    if method_data.empty:
        raise ValueError(f"{method} 비중 데이터가 없습니다.")

    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)

    experiments = [
        ("main_v2_conflict_defense", "main_v2: conflict 방어"),
        ("main_v2b_conflict_watch", "main_v2b: conflict 관찰"),
    ]

    for ax, (experiment, title) in zip(axes, experiments):
        temp_exp = method_data[method_data["experiment"] == experiment].copy()

        for asset_label in ASSET_LABEL_MAP.values():
            temp_asset = temp_exp[temp_exp["asset_label"] == asset_label].sort_values("Date")

            ax.plot(
                temp_asset["Date"],
                temp_asset["weight_pct"],
                label=asset_label,
                linewidth=1.8,
            )

        ax.set_title(title)
        ax.set_ylabel("비중 (%)")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper right")

    axes[-1].set_xlabel("Date")

    fig.suptitle(f"Fig.4 HSI 상태별 포트폴리오 비중 변화 ({method})", fontsize=15)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


# ============================================================
# 4. Turnover 비교 그래프
# ============================================================

def plot_turnover_comparison(turnover_data: pd.DataFrame) -> None:
    set_korean_font()

    plot_data = turnover_data[
        turnover_data["experiment"].isin(
            ["main_v2_conflict_defense", "main_v2b_conflict_watch"]
        )
    ].copy()

    pivot = plot_data.pivot(
        index="method",
        columns="display_name",
        values="avg_turnover",
    )

    ax = pivot.plot(
        kind="bar",
        figsize=(10, 6),
        width=0.7,
    )

    ax.set_title("Fig.5 평균 Turnover 비교: main_v2 vs main_v2b", fontsize=14)
    ax.set_xlabel("점수화 방식")
    ax.set_ylabel("평균 Turnover")
    ax.legend(title="overlay 규칙")
    ax.grid(axis="y", alpha=0.3)

    for container in ax.containers:
        ax.bar_label(container, fmt="%.4f", fontsize=9)

    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(OUTPUT_TURNOVER_FIG, dpi=150)
    plt.close()


# ============================================================
# 5. 해석 노트
# ============================================================

def make_note(turnover_data: pd.DataFrame) -> str:
    rows = []

    for method in ["rank", "zscore"]:
        v2 = turnover_data[
            (turnover_data["method"] == method)
            & (turnover_data["experiment"] == "main_v2_conflict_defense")
        ]

        v2b = turnover_data[
            (turnover_data["method"] == method)
            & (turnover_data["experiment"] == "main_v2b_conflict_watch")
        ]

        if v2.empty or v2b.empty:
            continue

        v2 = v2.iloc[0]
        v2b = v2b.iloc[0]

        rows.append(
            {
                "method": method,
                "v2_avg_turnover": v2["avg_turnover"],
                "v2b_avg_turnover": v2b["avg_turnover"],
                "diff": v2b["avg_turnover"] - v2["avg_turnover"],
            }
        )

    lines = []

    lines.append("# Fig.4~Fig.5 비중 변화 및 Turnover 해석 노트")
    lines.append("")
    lines.append("## 그림의 질문")
    lines.append("")
    lines.append("1. HSI 상태가 실제 ETF 비중 조정으로 연결되었는가?")
    lines.append("2. conflict를 관찰로 처리하면 Turnover가 줄어드는가?")
    lines.append("")
    lines.append("## Turnover 비교")
    lines.append("")
    lines.append("| method | main_v2 평균 Turnover | main_v2b 평균 Turnover | 차이 |")
    lines.append("|---|---:|---:|---:|")

    for row in rows:
        lines.append(
            f"| {row['method']} | {row['v2_avg_turnover']:.6f} | "
            f"{row['v2b_avg_turnover']:.6f} | {row['diff']:.6f} |"
        )

    lines.append("")
    lines.append("## 해석")
    lines.append("")
    lines.append(
        "비중 변화 그림은 HSI 상태가 단순한 설명 라벨에 머무르지 않고 "
        "실제 ETF 비중 조정으로 연결되었음을 보여준다."
    )
    lines.append(
        "Turnover 비교 결과는 conflict 상태를 방어전환이 아니라 관찰 상태로 처리했을 때 "
        "불필요한 비중 변화가 줄어드는지 확인하는 근거다."
    )
    lines.append(
        "main_v2b의 평균 Turnover가 main_v2보다 낮다면, conflict를 즉시 방어 신호로 사용하는 것보다 "
        "관찰 상태로 두는 규칙이 더 안정적인 포트폴리오 행동을 만들 수 있음을 시사한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 6. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("27_main_v2_plot_weights_turnover.py 실행 시작")
    print("=" * 70)

    weight_data = load_weight_data()
    turnover_data = load_turnover_data()

    weight_data.to_csv(OUTPUT_WEIGHT_PLOT_DATA, index=False, encoding="utf-8-sig")
    turnover_data.to_csv(OUTPUT_TURNOVER_PLOT_DATA, index=False, encoding="utf-8-sig")

    plot_weight_transition(weight_data, method="rank", output_path=OUTPUT_WEIGHT_FIG_RANK)
    plot_weight_transition(weight_data, method="zscore", output_path=OUTPUT_WEIGHT_FIG_ZSCORE)
    plot_turnover_comparison(turnover_data)

    note = make_note(turnover_data)
    OUTPUT_NOTE_PATH.write_text(note, encoding="utf-8")

    print("[저장 완료]")
    print(f"- {OUTPUT_WEIGHT_FIG_RANK}")
    print(f"- {OUTPUT_WEIGHT_FIG_ZSCORE}")
    print(f"- {OUTPUT_TURNOVER_FIG}")
    print(f"- {OUTPUT_WEIGHT_PLOT_DATA}")
    print(f"- {OUTPUT_TURNOVER_PLOT_DATA}")
    print(f"- {OUTPUT_NOTE_PATH}")

    print("\n[Turnover 비교 데이터]")
    display = turnover_data[
        turnover_data["experiment"].isin(
            ["main_v2_conflict_defense", "main_v2b_conflict_watch"]
        )
    ][
        [
            "method",
            "experiment",
            "display_name",
            "avg_turnover",
            "max_turnover",
            "total_turnover",
        ]
    ].sort_values(["method", "experiment"])

    print(display)

    print("\n" + "=" * 70)
    print("27_main_v2_plot_weights_turnover.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()