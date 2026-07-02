from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from common.io_utils import read_csv_with_date as _read_csv
from common.paths import DOCS_DIR, FIGURE_DIR, TABLE_DIR
from common.viz import STRATEGY_LABEL_MAP, set_korean_font


"""
25_main_v2_plot_cumulative_return.py

목적
----
EW, main_v2, main_v2b의 누적수익률을 비교한다.

질문
----
conflict를 방어로 처리한 main_v2와
conflict를 관찰로 처리한 main_v2b는
EW 대비 누적성과 흐름이 어떻게 다른가?

입력
----
output/tables/main_v2_cumulative_return_timeseries.csv
output/tables/main_v2b_cumulative_return_timeseries.csv

출력
----
output/figures/main_v2_fig2_cumulative_return_comparison_rank.png
output/figures/main_v2_fig2_cumulative_return_comparison_zscore.png
output/tables/main_v2_fig2_cumulative_return_plot_data.csv
docs/main_v2_fig2_cumulative_return_note.md
"""


# ============================================================
# 0. 경로 설정 (common.paths 사용)
# ============================================================

FIGURE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

MAIN_V2_PATH = TABLE_DIR / "main_v2_cumulative_return_timeseries.csv"
MAIN_V2B_PATH = TABLE_DIR / "main_v2b_cumulative_return_timeseries.csv"

OUTPUT_FIGURE_RANK_PATH = FIGURE_DIR / "main_v2_fig2_cumulative_return_comparison_rank.png"
OUTPUT_FIGURE_ZSCORE_PATH = FIGURE_DIR / "main_v2_fig2_cumulative_return_comparison_zscore.png"
OUTPUT_PLOT_DATA_PATH = TABLE_DIR / "main_v2_fig2_cumulative_return_plot_data.csv"
OUTPUT_NOTE_PATH = DOCS_DIR / "main_v2_fig2_cumulative_return_note.md"


# ============================================================
# 1. 설정 · 2. 데이터 로드
#    set_korean_font / STRATEGY_LABEL_MAP / read_csv_with_date → common
# ============================================================

def read_csv_with_date(path: Path) -> pd.DataFrame:
    """기존 엄격형 로더 동작(Date 필수, signal_date 미파싱)을 common으로 위임."""
    return _read_csv(path, require_date=True, parse_signal_date=False)


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

    # EW가 main_v2와 main_v2b에 중복으로 들어 있으므로 하나만 남긴다.
    combined = combined.drop_duplicates(
        subset=["Date", "method", "experiment"],
        keep="first",
    ).reset_index(drop=True)

    combined["display_name"] = combined["strategy"].map(STRATEGY_LABEL_MAP)

    required_cols = [
        "Date",
        "method",
        "strategy",
        "experiment",
        "display_name",
        "monthly_return",
        "cumulative_return",
    ]

    existing_cols = [col for col in required_cols if col in combined.columns]
    return combined[existing_cols].copy()


# ============================================================
# 3. 그래프 생성
# ============================================================

def plot_cumulative_return(plot_data: pd.DataFrame, method: str, output_path: Path) -> None:
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
            temp["cumulative_return"],
            label=label,
            linewidth=2,
        )

    plt.title(f"Fig.2 누적수익률 비교 ({method})", fontsize=14)
    plt.xlabel("Date")
    plt.ylabel("Cumulative Return")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


# ============================================================
# 4. 해석 노트 생성
# ============================================================

def make_note(plot_data: pd.DataFrame) -> str:
    final_rows = (
        plot_data
        .sort_values("Date")
        .groupby(["method", "experiment", "display_name"], dropna=False)
        .tail(1)
        .copy()
    )

    lines = []

    lines.append("# Fig.2 누적수익률 비교 해석 노트")
    lines.append("")
    lines.append("## 그림의 질문")
    lines.append("")
    lines.append(
        "EW, main_v2, main_v2b의 누적성과 흐름은 어떻게 다른가?"
    )
    lines.append("")
    lines.append("## 최종 누적수익률 요약")
    lines.append("")
    lines.append("| method | 전략 | 최종 누적값 |")
    lines.append("|---|---|---:|")

    for _, row in final_rows.iterrows():
        lines.append(
            f"| {row['method']} | {row['display_name']} | {row['cumulative_return']:.6f} |"
        )

    lines.append("")
    lines.append("## 해석")
    lines.append("")
    lines.append(
        "main_v2는 conflict 상태를 소폭 방어로 처리한 규칙이고, "
        "main_v2b는 conflict 상태를 관찰 상태로 처리한 규칙이다."
    )
    lines.append(
        "누적수익률 비교는 conflict 처리 방식이 장기 성과 흐름에 어떤 영향을 주는지 보여준다."
    )
    lines.append(
        "특히 main_v2b가 main_v2보다 높은 누적성과를 보인다면, "
        "conflict를 즉시 방어전환으로 처리하는 것이 불필요한 수익률 희생을 만들었을 가능성을 시사한다."
    )
    lines.append("")
    lines.append("## 보고서 연결 문장")
    lines.append("")
    lines.append(
        "누적수익률 비교 결과는 HSI 5상태 중 conflict의 포트폴리오 행동을 어떻게 정의하느냐가 "
        "장기 성과 흐름에 영향을 줄 수 있음을 보여준다. "
        "따라서 conflict는 위험 악화가 확정된 상태라기보다 신호 혼조 상태로 해석하고, "
        "즉시 방어전환하기보다는 관찰 상태로 처리하는 규칙을 별도로 비교할 필요가 있다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 5. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("25_main_v2_plot_cumulative_return.py 실행 시작")
    print("=" * 70)

    plot_data = load_and_prepare_data()

    plot_data.to_csv(OUTPUT_PLOT_DATA_PATH, index=False, encoding="utf-8-sig")

    plot_cumulative_return(plot_data, method="rank", output_path=OUTPUT_FIGURE_RANK_PATH)
    plot_cumulative_return(plot_data, method="zscore", output_path=OUTPUT_FIGURE_ZSCORE_PATH)

    note = make_note(plot_data)
    OUTPUT_NOTE_PATH.write_text(note, encoding="utf-8")

    print("[저장 완료]")
    print(f"- {OUTPUT_FIGURE_RANK_PATH}")
    print(f"- {OUTPUT_FIGURE_ZSCORE_PATH}")
    print(f"- {OUTPUT_PLOT_DATA_PATH}")
    print(f"- {OUTPUT_NOTE_PATH}")

    print("\n[최종 누적수익률]")
    final_summary = (
        plot_data
        .sort_values("Date")
        .groupby(["method", "experiment", "display_name"], dropna=False)
        .tail(1)
        [["method", "experiment", "display_name", "Date", "cumulative_return"]]
        .sort_values(["method", "experiment"])
    )
    print(final_summary)

    print("\n" + "=" * 70)
    print("25_main_v2_plot_cumulative_return.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()
