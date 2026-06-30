from pathlib import Path
from datetime import datetime

import pandas as pd


"""
29_main_v2_visualization_output_index.py

목적
----
main_v2 / main_v2b HSI 5상태 overlay 실험에서 생성한
시각화 산출물의 존재 여부와 보고서 배치 순서를 정리한다.

이 파일은 그래프를 새로 그리지 않는다.
이미 생성된 figure, plot_data, note 파일이 모두 있는지 점검한다.

출력
----
output/tables/main_v2_visualization_output_index.csv
docs/main_v2_visualization_output_index.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
FIGURE_DIR = PROJECT_ROOT / "output" / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"

DOCS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_INDEX_CSV = TABLE_DIR / "main_v2_visualization_output_index.csv"
OUTPUT_INDEX_MD = DOCS_DIR / "main_v2_visualization_output_index.md"


# ============================================================
# 1. 시각화 산출물 목록
# ============================================================

VISUAL_OUTPUTS = [
    {
        "figure_id": "Fig.1",
        "figure_name": "HSI 5상태 분포",
        "report_position": "본문",
        "question": "rank와 zscore 방식은 HSI 5상태를 어떻게 다르게 분류하는가?",
        "figure_files": "output/figures/main_v2_fig1_hsi_state5_distribution.png",
        "data_files": "output/tables/main_v2_fig1_hsi_state5_distribution_plot_data.csv",
        "note_files": "docs/main_v2_fig1_hsi_state5_distribution_note.md",
    },
    {
        "figure_id": "Fig.2",
        "figure_name": "누적수익률 비교",
        "report_position": "본문",
        "question": "EW, main_v2, main_v2b의 누적성과 흐름은 어떻게 다른가?",
        "figure_files": (
            "output/figures/main_v2_fig2_cumulative_return_comparison_rank.png; "
            "output/figures/main_v2_fig2_cumulative_return_comparison_zscore.png"
        ),
        "data_files": "output/tables/main_v2_fig2_cumulative_return_plot_data.csv",
        "note_files": "docs/main_v2_fig2_cumulative_return_note.md",
    },
    {
        "figure_id": "Fig.3",
        "figure_name": "Drawdown 비교",
        "report_position": "본문",
        "question": "HSI overlay는 낙폭을 줄였는가?",
        "figure_files": (
            "output/figures/main_v2_fig3_drawdown_comparison_rank.png; "
            "output/figures/main_v2_fig3_drawdown_comparison_zscore.png"
        ),
        "data_files": "output/tables/main_v2_fig3_drawdown_plot_data.csv",
        "note_files": "docs/main_v2_fig3_drawdown_note.md",
    },
    {
        "figure_id": "Fig.4",
        "figure_name": "HSI 상태별 포트폴리오 비중 변화",
        "report_position": "본문",
        "question": "HSI 상태가 실제 ETF 비중 조정으로 연결되었는가?",
        "figure_files": (
            "output/figures/main_v2_fig4_weight_transition_rank.png; "
            "output/figures/main_v2_fig4_weight_transition_zscore.png"
        ),
        "data_files": "output/tables/main_v2_fig4_weight_transition_plot_data.csv",
        "note_files": "docs/main_v2_fig4_fig5_weights_turnover_note.md",
    },
    {
        "figure_id": "Fig.5",
        "figure_name": "Turnover 비교",
        "report_position": "본문",
        "question": "conflict를 관찰로 처리하면 Turnover가 줄어드는가?",
        "figure_files": "output/figures/main_v2_fig5_turnover_comparison.png",
        "data_files": "output/tables/main_v2_fig5_turnover_plot_data.csv",
        "note_files": "docs/main_v2_fig4_fig5_weights_turnover_note.md",
    },
    {
        "figure_id": "Fig.6",
        "figure_name": "main_v2 vs main_v2b 규칙 비교 요약",
        "report_position": "본문",
        "question": "conflict 방어 처리와 conflict 관찰 처리 중 어느 쪽이 더 안정적인가?",
        "figure_files": (
            "output/figures/main_v2_fig6_rule_comparison_summary_rank.png; "
            "output/figures/main_v2_fig6_rule_comparison_summary_zscore.png"
        ),
        "data_files": "output/tables/main_v2_fig6_rule_comparison_plot_data.csv",
        "note_files": "docs/main_v2_fig6_rule_comparison_note.md",
    },
]


# ============================================================
# 2. 파일 존재 여부 점검
# ============================================================

def split_paths(path_text: str) -> list[str]:
    return [item.strip() for item in path_text.split(";") if item.strip()]


def check_paths(path_text: str) -> tuple[bool, str]:
    missing = []

    for rel_path in split_paths(path_text):
        full_path = PROJECT_ROOT / rel_path
        if not full_path.exists():
            missing.append(rel_path)

    if len(missing) == 0:
        return True, ""

    return False, "; ".join(missing)


def build_index() -> pd.DataFrame:
    rows = []

    for item in VISUAL_OUTPUTS:
        figure_ready, missing_figures = check_paths(item["figure_files"])
        data_ready, missing_data = check_paths(item["data_files"])
        note_ready, missing_notes = check_paths(item["note_files"])

        all_ready = figure_ready and data_ready and note_ready

        rows.append(
            {
                "figure_id": item["figure_id"],
                "figure_name": item["figure_name"],
                "report_position": item["report_position"],
                "question": item["question"],
                "figure_files": item["figure_files"],
                "data_files": item["data_files"],
                "note_files": item["note_files"],
                "figure_ready": figure_ready,
                "data_ready": data_ready,
                "note_ready": note_ready,
                "all_ready": all_ready,
                "missing_figures": missing_figures,
                "missing_data": missing_data,
                "missing_notes": missing_notes,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 3. Markdown 인덱스 생성
# ============================================================

def make_markdown(index_df: pd.DataFrame) -> str:
    ready_count = int(index_df["all_ready"].sum())
    total_count = len(index_df)

    lines = []

    lines.append("# main_v2 HSI 5상태 Overlay 시각화 산출물 인덱스")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 준비 완료: {ready_count} / {total_count}")
    lines.append("")

    lines.append("## 1. 보고서 삽입 권장 순서")
    lines.append("")
    lines.append("| 순서 | Figure | 이름 | 답하는 질문 | 준비 상태 |")
    lines.append("|---:|---|---|---|---|")

    for i, (_, row) in enumerate(index_df.iterrows(), start=1):
        status = "OK" if row["all_ready"] else "MISSING"
        lines.append(
            f"| {i} | {row['figure_id']} | {row['figure_name']} | "
            f"{row['question']} | {status} |"
        )

    lines.append("")
    lines.append("## 2. 해석 흐름")
    lines.append("")
    lines.append("1. Fig.1에서 HSI 5상태가 rank와 zscore에서 어떻게 분포하는지 확인한다.")
    lines.append("2. Fig.2에서 EW, main_v2, main_v2b의 장기 누적성과 흐름을 비교한다.")
    lines.append("3. Fig.3에서 Drawdown과 MDD를 비교해 방어 효과를 확인한다.")
    lines.append("4. Fig.4에서 HSI 상태가 실제 ETF 비중 변화로 연결되었는지 확인한다.")
    lines.append("5. Fig.5에서 conflict 처리 방식이 Turnover에 미친 영향을 확인한다.")
    lines.append("6. Fig.6에서 main_v2와 main_v2b 규칙 차이를 종합 요약한다.")
    lines.append("")

    missing = index_df[index_df["all_ready"] == False]

    if len(missing) > 0:
        lines.append("## 3. 미완성 항목")
        lines.append("")
        for _, row in missing.iterrows():
            lines.append(f"### {row['figure_id']} {row['figure_name']}")
            if row["missing_figures"]:
                lines.append(f"- 누락 figure: {row['missing_figures']}")
            if row["missing_data"]:
                lines.append(f"- 누락 data: {row['missing_data']}")
            if row["missing_notes"]:
                lines.append(f"- 누락 note: {row['missing_notes']}")
            lines.append("")
    else:
        lines.append("## 3. 산출물 상태")
        lines.append("")
        lines.append("- 모든 본문용 시각화 산출물이 준비되어 있다.")
        lines.append("")

    lines.append("## 4. 보고서 연결 문장")
    lines.append("")
    lines.append(
        "본 시각화 묶음은 HSI 5상태 체계가 단순한 상태 라벨에 그치지 않고, "
        "포트폴리오 비중 조정과 성과 차이로 이어지는지를 확인하기 위해 구성하였다. "
        "특히 conflict 상태를 방어 신호로 처리한 main_v2와 관찰 신호로 처리한 main_v2b를 비교함으로써, "
        "HSI 상태명과 실제 포트폴리오 행동을 분리해 설계할 필요가 있음을 확인하였다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 4. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("29_main_v2_visualization_output_index.py 실행 시작")
    print("=" * 70)

    index_df = build_index()

    index_df.to_csv(OUTPUT_INDEX_CSV, index=False, encoding="utf-8-sig")

    markdown = make_markdown(index_df)
    OUTPUT_INDEX_MD.write_text(markdown, encoding="utf-8")

    print("[저장 완료]")
    print(f"- {OUTPUT_INDEX_CSV}")
    print(f"- {OUTPUT_INDEX_MD}")

    print("\n[시각화 산출물 준비 상태]")
    print(
        index_df[
            [
                "figure_id",
                "figure_name",
                "figure_ready",
                "data_ready",
                "note_ready",
                "all_ready",
            ]
        ]
    )

    if index_df["all_ready"].all():
        print("\n모든 본문용 시각화 산출물이 준비되어 있습니다.")
    else:
        print("\n일부 시각화 산출물이 누락되어 있습니다.")

    print("\n" + "=" * 70)
    print("29_main_v2_visualization_output_index.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()