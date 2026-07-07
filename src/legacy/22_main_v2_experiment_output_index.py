from pathlib import Path
from datetime import datetime

import pandas as pd


"""
22_main_v2_experiment_output_index.py

목적
----
main_v2 HSI 5상태 overlay 실험과 main_v2b 완화형 overlay 실험에서
생성된 주요 산출물을 정리한다.

이 파일은 백테스트를 새로 계산하지 않는다.
이미 생성된 파일들이 존재하는지 확인하고,
산출물 인덱스와 실험 로그를 만든다.

출력
----
output/tables/main_v2_experiment_output_index.csv
docs/main_v2_hsi_state_overlay_experiment_log.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
DOCS_DIR = PROJECT_ROOT / "docs"

DOCS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_INDEX_PATH = TABLE_DIR / "main_v2_experiment_output_index.csv"
OUTPUT_LOG_PATH = DOCS_DIR / "main_v2_hsi_state_overlay_experiment_log.md"


# ============================================================
# 1. 산출물 목록 정의
# ============================================================

OUTPUT_ITEMS = [
    {
        "step": "16",
        "file_name": "main_v2_hsi_state5_table_rank.csv",
        "path": "output/tables/main_v2_hsi_state5_table_rank.csv",
        "role": "rank 기준 HSI 5상태 월별 분류표",
    },
    {
        "step": "16",
        "file_name": "main_v2_hsi_state5_table_zscore.csv",
        "path": "output/tables/main_v2_hsi_state5_table_zscore.csv",
        "role": "zscore 기준 HSI 5상태 월별 분류표",
    },
    {
        "step": "16",
        "file_name": "main_v2_hsi_state5_definition.csv",
        "path": "output/tables/main_v2_hsi_state5_definition.csv",
        "role": "HSI 5상태 정의표",
    },
    {
        "step": "16",
        "file_name": "main_v2_allocation_rule_table.csv",
        "path": "output/tables/main_v2_allocation_rule_table.csv",
        "role": "main_v2 상태별 overlay 비중 규칙",
    },
    {
        "step": "16",
        "file_name": "main_v2_hsi_state5_distribution.csv",
        "path": "output/tables/main_v2_hsi_state5_distribution.csv",
        "role": "HSI 5상태 분포 요약",
    },
    {
        "step": "17",
        "file_name": "main_v2_backtest_timeseries_rank.csv",
        "path": "output/tables/main_v2_backtest_timeseries_rank.csv",
        "role": "main_v2 rank 기준 백테스트 시계열",
    },
    {
        "step": "17",
        "file_name": "main_v2_backtest_timeseries_zscore.csv",
        "path": "output/tables/main_v2_backtest_timeseries_zscore.csv",
        "role": "main_v2 zscore 기준 백테스트 시계열",
    },
    {
        "step": "17",
        "file_name": "main_v2_strategy_weights_rank.csv",
        "path": "output/tables/main_v2_strategy_weights_rank.csv",
        "role": "main_v2 rank 기준 월별 전략 비중",
    },
    {
        "step": "17",
        "file_name": "main_v2_strategy_weights_zscore.csv",
        "path": "output/tables/main_v2_strategy_weights_zscore.csv",
        "role": "main_v2 zscore 기준 월별 전략 비중",
    },
    {
        "step": "18",
        "file_name": "main_v2_performance_summary.csv",
        "path": "output/tables/main_v2_performance_summary.csv",
        "role": "main_v2 정식 성과평가표",
    },
    {
        "step": "19",
        "file_name": "main_v2b_backtest_timeseries_rank.csv",
        "path": "output/tables/main_v2b_backtest_timeseries_rank.csv",
        "role": "main_v2b rank 기준 백테스트 시계열",
    },
    {
        "step": "19",
        "file_name": "main_v2b_backtest_timeseries_zscore.csv",
        "path": "output/tables/main_v2b_backtest_timeseries_zscore.csv",
        "role": "main_v2b zscore 기준 백테스트 시계열",
    },
    {
        "step": "19",
        "file_name": "main_v2b_strategy_weights_rank.csv",
        "path": "output/tables/main_v2b_strategy_weights_rank.csv",
        "role": "main_v2b rank 기준 월별 전략 비중",
    },
    {
        "step": "19",
        "file_name": "main_v2b_strategy_weights_zscore.csv",
        "path": "output/tables/main_v2b_strategy_weights_zscore.csv",
        "role": "main_v2b zscore 기준 월별 전략 비중",
    },
    {
        "step": "19",
        "file_name": "main_v2b_allocation_rule_table.csv",
        "path": "output/tables/main_v2b_allocation_rule_table.csv",
        "role": "main_v2b 상태별 overlay 비중 규칙",
    },
    {
        "step": "20",
        "file_name": "main_v2_rule_comparison_summary.csv",
        "path": "output/tables/main_v2_rule_comparison_summary.csv",
        "role": "main_v2와 main_v2b 규칙 비교표",
    },
    {
        "step": "20",
        "file_name": "main_v2_rule_comparison_comment.csv",
        "path": "output/tables/main_v2_rule_comparison_comment.csv",
        "role": "main_v2와 main_v2b 비교 해석 코멘트",
    },
    {
        "step": "21",
        "file_name": "main_v2b_performance_summary.csv",
        "path": "output/tables/main_v2b_performance_summary.csv",
        "role": "main_v2b 정식 성과평가표",
    },
    {
        "step": "21",
        "file_name": "main_v2b_drawdown_timeseries.csv",
        "path": "output/tables/main_v2b_drawdown_timeseries.csv",
        "role": "main_v2b Drawdown 시계열",
    },
    {
        "step": "21",
        "file_name": "main_v2b_cumulative_return_timeseries.csv",
        "path": "output/tables/main_v2b_cumulative_return_timeseries.csv",
        "role": "main_v2b 누적수익률 시계열",
    },
    {
        "step": "21",
        "file_name": "main_v2b_performance_comment.csv",
        "path": "output/tables/main_v2b_performance_comment.csv",
        "role": "main_v2b 성과 해석 코멘트",
    },
]


# ============================================================
# 2. 파일 존재 여부 확인
# ============================================================

def build_output_index() -> pd.DataFrame:
    rows = []

    for item in OUTPUT_ITEMS:
        full_path = PROJECT_ROOT / item["path"]
        exists = full_path.exists()

        if exists:
            size_kb = full_path.stat().st_size / 1024
            modified_time = datetime.fromtimestamp(full_path.stat().st_mtime)
        else:
            size_kb = None
            modified_time = None

        rows.append(
            {
                "step": item["step"],
                "file_name": item["file_name"],
                "relative_path": item["path"],
                "role": item["role"],
                "exists": exists,
                "size_kb": size_kb,
                "modified_time": modified_time,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 3. 로그 문서 생성
# ============================================================

def make_markdown_log(index_df: pd.DataFrame) -> str:
    completed = index_df[index_df["exists"] == True]
    missing = index_df[index_df["exists"] == False]

    lines = []

    lines.append("# main_v2 HSI 5상태 Overlay 실험 로그")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("- 목적: HSI 5상태 체계를 이용한 방어형 overlay 전략 실험 산출물 정리")
    lines.append("")

    lines.append("## 1. 실험 흐름")
    lines.append("")
    lines.append("| 단계 | 파일 | 역할 |")
    lines.append("|---|---|---|")

    for _, row in index_df.iterrows():
        status = "생성 완료" if row["exists"] else "미생성"
        lines.append(
            f"| {row['step']} | `{row['file_name']}` | {row['role']} ({status}) |"
        )

    lines.append("")
    lines.append("## 2. 실험 구분")
    lines.append("")
    lines.append("| 실험 | 설명 |")
    lines.append("|---|---|")
    lines.append("| main_v2 | conflict 상태를 소폭 방어로 처리한 HSI 5상태 overlay |")
    lines.append("| main_v2b | conflict 상태를 관찰 상태로 처리한 완화형 HSI 5상태 overlay |")
    lines.append("")

    lines.append("## 3. 현재 산출물 상태")
    lines.append("")
    lines.append(f"- 생성 완료 파일 수: {len(completed)}")
    lines.append(f"- 미생성 파일 수: {len(missing)}")
    lines.append("")

    if len(missing) > 0:
        lines.append("### 미생성 파일")
        lines.append("")
        for _, row in missing.iterrows():
            lines.append(f"- `{row['relative_path']}`")
        lines.append("")

    lines.append("## 4. 작업 메모")
    lines.append("")
    lines.append(
        "- HSI 5상태는 `risk_relief`, `neutral_watch`, `conflict`, "
        "`risk_warning`, `accident_zone`으로 구성하였다."
    )
    lines.append(
        "- main_v2에서는 `conflict`를 소폭 방어 상태로 처리하였다."
    )
    lines.append(
        "- main_v2b에서는 `conflict`를 위험 악화 확정 상태가 아니라 "
        "관찰 상태로 처리하였다."
    )
    lines.append(
        "- 월말 HSI 상태는 다음 달 월간 수익률에 적용하여 look-ahead bias를 피하는 구조로 정렬하였다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 4. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("22_main_v2_experiment_output_index.py 실행 시작")
    print("=" * 70)

    index_df = build_output_index()
    index_df.to_csv(OUTPUT_INDEX_PATH, index=False, encoding="utf-8-sig")

    markdown_log = make_markdown_log(index_df)
    OUTPUT_LOG_PATH.write_text(markdown_log, encoding="utf-8")

    print("[저장 완료]")
    print(f"- {OUTPUT_INDEX_PATH}")
    print(f"- {OUTPUT_LOG_PATH}")

    print("\n[산출물 상태 요약]")
    print(index_df.groupby("exists").size().reset_index(name="count"))

    missing = index_df[index_df["exists"] == False]

    if len(missing) > 0:
        print("\n[미생성 파일]")
        print(missing[["step", "file_name", "relative_path"]])
    else:
        print("\n모든 주요 산출물이 생성되어 있습니다.")

    print("\n" + "=" * 70)
    print("22_main_v2_experiment_output_index.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()