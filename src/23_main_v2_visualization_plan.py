from pathlib import Path
from datetime import datetime

import pandas as pd


"""
23_main_v2_visualization_plan.py

목적
----
main_v2 / main_v2b HSI 5상태 overlay 실험의 시각화 계획표를 만든다.

이 파일은 그래프를 직접 그리지 않는다.
어떤 그림을 만들지, 어떤 입력 파일을 사용할지, 각 그림이 어떤 질문에 답하는지 정리한다.

출력
----
output/tables/main_v2_visualization_plan.csv
docs/main_v2_visualization_plan.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
DOCS_DIR = PROJECT_ROOT / "docs"

DOCS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PLAN_CSV = TABLE_DIR / "main_v2_visualization_plan.csv"
OUTPUT_PLAN_MD = DOCS_DIR / "main_v2_visualization_plan.md"


# ============================================================
# 1. 시각화 계획 정의
# ============================================================

VISUALIZATION_ITEMS = [
    {
        "figure_id": "Fig.1",
        "figure_name": "HSI 5상태 분포",
        "output_file": "output/figures/main_v2_fig1_hsi_state5_distribution.png",
        "input_files": "output/tables/main_v2_hsi_state5_distribution.csv",
        "main_question": "rank와 zscore 방식은 HSI 5상태를 어떻게 다르게 분류하는가?",
        "why_needed": "HSI 5상태 체계가 실제 월별 상태로 어떻게 나타났는지 보여준다.",
        "report_position": "본문",
        "status": "planned",
    },
    {
        "figure_id": "Fig.2",
        "figure_name": "누적수익률 비교",
        "output_file": "output/figures/main_v2_fig2_cumulative_return_comparison.png",
        "input_files": (
            "output/tables/main_v2_cumulative_return_timeseries.csv; "
            "output/tables/main_v2b_cumulative_return_timeseries.csv"
        ),
        "main_question": "EW, main_v2, main_v2b의 누적성과 흐름은 어떻게 다른가?",
        "why_needed": "방어형 overlay가 단순 동일비중 대비 수익률 흐름을 어떻게 바꾸는지 확인한다.",
        "report_position": "본문",
        "status": "planned",
    },
    {
        "figure_id": "Fig.3",
        "figure_name": "Drawdown 비교",
        "output_file": "output/figures/main_v2_fig3_drawdown_comparison.png",
        "input_files": (
            "output/tables/main_v2_drawdown_timeseries.csv; "
            "output/tables/main_v2b_drawdown_timeseries.csv"
        ),
        "main_question": "HSI overlay는 낙폭을 줄였는가?",
        "why_needed": "본 프로젝트가 수익률 극대화보다 위험관리 성격을 가지므로 Drawdown 비교가 핵심 증거다.",
        "report_position": "본문",
        "status": "planned",
    },
    {
        "figure_id": "Fig.4",
        "figure_name": "HSI 상태별 포트폴리오 비중 변화",
        "output_file": "output/figures/main_v2_fig4_state_weight_transition.png",
        "input_files": (
            "output/tables/main_v2_strategy_weights_rank.csv; "
            "output/tables/main_v2b_strategy_weights_rank.csv"
        ),
        "main_question": "HSI 상태가 실제 ETF 비중 조정으로 연결되었는가?",
        "why_needed": "HSI가 단순 설명 지표가 아니라 포트폴리오 행동으로 연결되는 overlay 구조임을 보여준다.",
        "report_position": "본문",
        "status": "planned",
    },
    {
        "figure_id": "Fig.5",
        "figure_name": "Turnover 비교",
        "output_file": "output/figures/main_v2_fig5_turnover_comparison.png",
        "input_files": (
            "output/tables/main_v2_turnover_summary.csv; "
            "output/tables/main_v2b_turnover_summary.csv"
        ),
        "main_question": "conflict를 관찰로 처리하면 Turnover가 줄어드는가?",
        "why_needed": "main_v2와 main_v2b의 핵심 차이인 conflict 처리 방식의 효과를 보여준다.",
        "report_position": "본문",
        "status": "planned",
    },
    {
        "figure_id": "Fig.6",
        "figure_name": "main_v2 vs main_v2b 규칙 비교 요약",
        "output_file": "output/figures/main_v2_fig6_rule_comparison_summary.png",
        "input_files": "output/tables/main_v2_rule_comparison_summary.csv",
        "main_question": "conflict 방어 처리와 conflict 관찰 처리 중 어느 쪽이 더 안정적인가?",
        "why_needed": "상태명과 포트폴리오 행동을 분리해야 한다는 결론을 시각적으로 요약한다.",
        "report_position": "본문",
        "status": "planned",
    },
    {
        "figure_id": "Appendix Fig.1",
        "figure_name": "HSI 상태 정의 및 비중 규칙표",
        "output_file": "output/figures/main_v2_appendix_state_rule_table.png",
        "input_files": (
            "output/tables/main_v2_hsi_state5_definition.csv; "
            "output/tables/main_v2_allocation_rule_table.csv; "
            "output/tables/main_v2b_allocation_rule_table.csv"
        ),
        "main_question": "각 HSI 상태는 어떤 의미이며, 어떤 포트폴리오 행동으로 연결되는가?",
        "why_needed": "보고서 부록에서 상태 정의와 비중 규칙의 재현 가능성을 확보한다.",
        "report_position": "부록",
        "status": "planned",
    },
]


# ============================================================
# 2. 파일 존재 여부 확인
# ============================================================

def check_input_files(input_files: str) -> tuple[bool, str]:
    paths = [item.strip() for item in input_files.split(";")]

    missing = []

    for rel_path in paths:
        full_path = PROJECT_ROOT / rel_path
        if not full_path.exists():
            missing.append(rel_path)

    if len(missing) == 0:
        return True, ""

    return False, "; ".join(missing)


def build_visualization_plan() -> pd.DataFrame:
    rows = []

    for item in VISUALIZATION_ITEMS:
        input_ready, missing_inputs = check_input_files(item["input_files"])

        rows.append(
            {
                "figure_id": item["figure_id"],
                "figure_name": item["figure_name"],
                "output_file": item["output_file"],
                "input_files": item["input_files"],
                "input_ready": input_ready,
                "missing_inputs": missing_inputs,
                "main_question": item["main_question"],
                "why_needed": item["why_needed"],
                "report_position": item["report_position"],
                "status": item["status"],
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 3. Markdown 문서 생성
# ============================================================

def make_markdown_plan(plan: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_v2 HSI 5상태 Overlay 시각화 계획")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("- 목적: HSI 5상태 overlay 실험 결과를 보고서용 증거 그림으로 정리하기 위한 계획표")
    lines.append("")

    lines.append("## 1. 핵심 원칙")
    lines.append("")
    lines.append("- 그림은 장식이 아니라 분석 질문에 대한 증거로 사용한다.")
    lines.append("- 누적수익률만 보지 않고 Drawdown, Turnover, 비중 변화까지 함께 확인한다.")
    lines.append("- HSI 상태명과 실제 포트폴리오 행동을 구분해서 보여준다.")
    lines.append("")

    lines.append("## 2. 시각화 목록")
    lines.append("")
    lines.append("| Figure | 이름 | 답하려는 질문 | 보고서 위치 | 입력 준비 |")
    lines.append("|---|---|---|---|---|")

    for _, row in plan.iterrows():
        ready = "OK" if row["input_ready"] else "MISSING"
        lines.append(
            f"| {row['figure_id']} | {row['figure_name']} | "
            f"{row['main_question']} | {row['report_position']} | {ready} |"
        )

    lines.append("")

    missing = plan[plan["input_ready"] == False]

    if len(missing) > 0:
        lines.append("## 3. 미준비 입력 파일")
        lines.append("")
        for _, row in missing.iterrows():
            lines.append(f"- {row['figure_id']} `{row['figure_name']}`: {row['missing_inputs']}")
        lines.append("")
    else:
        lines.append("## 3. 입력 파일 상태")
        lines.append("")
        lines.append("- 모든 시각화 입력 파일이 준비되어 있다.")
        lines.append("")

    lines.append("## 4. 권장 생성 순서")
    lines.append("")
    lines.append("1. HSI 5상태 분포")
    lines.append("2. 누적수익률 비교")
    lines.append("3. Drawdown 비교")
    lines.append("4. 포트폴리오 비중 변화")
    lines.append("5. Turnover 비교")
    lines.append("6. 규칙 비교 요약")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 4. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("23_main_v2_visualization_plan.py 실행 시작")
    print("=" * 70)

    plan = build_visualization_plan()

    plan.to_csv(OUTPUT_PLAN_CSV, index=False, encoding="utf-8-sig")

    markdown = make_markdown_plan(plan)
    OUTPUT_PLAN_MD.write_text(markdown, encoding="utf-8")

    print("[저장 완료]")
    print(f"- {OUTPUT_PLAN_CSV}")
    print(f"- {OUTPUT_PLAN_MD}")

    print("\n[시각화 입력 준비 상태]")
    print(
        plan[
            [
                "figure_id",
                "figure_name",
                "input_ready",
                "missing_inputs",
                "report_position",
            ]
        ]
    )

    missing_count = (~plan["input_ready"]).sum()

    if missing_count == 0:
        print("\n모든 시각화 입력 파일이 준비되어 있습니다.")
    else:
        print(f"\n입력 파일이 부족한 시각화 항목: {missing_count}개")

    print("\n" + "=" * 70)
    print("23_main_v2_visualization_plan.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()