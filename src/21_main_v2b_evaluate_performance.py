import pandas as pd

from common.io_utils import read_csv_with_date
from common.metrics import add_diff_vs_ew, calculate_performance_metrics, make_performance_summary
from common.paths import TABLE_DIR


"""
21_main_v2b_evaluate_performance.py

목적
----
main_v2b, 즉 conflict를 방어 신호가 아니라 관찰 신호로 처리한
HSI 5상태 완화형 overlay 전략의 정식 성과평가표를 만든다.

main_v2b 규칙
------------
risk_relief      -> 기본 동일비중
neutral_watch    -> 기본 동일비중
conflict         -> 기본 동일비중
risk_warning     -> 방어 강화
accident_zone    -> 강한 방어전환

입력
----
output/tables/main_v2b_backtest_timeseries_rank.csv
output/tables/main_v2b_backtest_timeseries_zscore.csv
output/tables/main_v2b_turnover_summary.csv

출력
----
output/tables/main_v2b_performance_summary.csv
output/tables/main_v2b_drawdown_timeseries.csv
output/tables/main_v2b_cumulative_return_timeseries.csv
output/tables/main_v2b_performance_comment.csv
"""


# ============================================================
# 0. 경로 설정 (common.paths.TABLE_DIR 사용)
# ============================================================

BACKTEST_RANK_PATH = TABLE_DIR / "main_v2b_backtest_timeseries_rank.csv"
BACKTEST_ZSCORE_PATH = TABLE_DIR / "main_v2b_backtest_timeseries_zscore.csv"
TURNOVER_SUMMARY_PATH = TABLE_DIR / "main_v2b_turnover_summary.csv"

OUTPUT_PERFORMANCE_PATH = TABLE_DIR / "main_v2b_performance_summary.csv"
OUTPUT_DRAWDOWN_PATH = TABLE_DIR / "main_v2b_drawdown_timeseries.csv"
OUTPUT_CUMULATIVE_PATH = TABLE_DIR / "main_v2b_cumulative_return_timeseries.csv"
OUTPUT_COMMENT_PATH = TABLE_DIR / "main_v2b_performance_comment.csv"


# ============================================================
# 1. 데이터 로드 · 2. 성과지표 · 3. EW 대비 차이
#    → common.io_utils / common.metrics 로 통합
# ============================================================


# ============================================================
# 4. 시계열 표 정리
# ============================================================

def make_drawdown_timeseries(backtest: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "Date",
        "method",
        "strategy",
        "overlay_rule",
        "signal_date",
        "hsi_state5",
        "state_name_kr",
        "action",
        "monthly_return",
        "cumulative_return",
        "drawdown",
    ]

    existing_cols = [col for col in cols if col in backtest.columns]
    return backtest[existing_cols].copy()


def make_cumulative_return_timeseries(backtest: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "Date",
        "method",
        "strategy",
        "overlay_rule",
        "signal_date",
        "hsi_state5",
        "state_name_kr",
        "monthly_return",
        "cumulative_return",
    ]

    existing_cols = [col for col in cols if col in backtest.columns]
    return backtest[existing_cols].copy()


# ============================================================
# 5. 해석 코멘트 표
# ============================================================

def make_performance_comment(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for method in summary["method"].dropna().unique():
        method_df = summary[summary["method"] == method].copy()

        ew = method_df[method_df["strategy"] == "EW"]
        overlay = method_df[method_df["strategy"] == "HSI_state5_overlay_v2b"]

        if ew.empty or overlay.empty:
            continue

        ew = ew.iloc[0]
        overlay = overlay.iloc[0]

        if overlay["mdd"] > ew["mdd"]:
            mdd_comment = "EW 대비 MDD 소폭 개선"
        elif overlay["mdd"] < ew["mdd"]:
            mdd_comment = "EW 대비 MDD 악화"
        else:
            mdd_comment = "EW와 MDD 동일"

        if overlay["total_return"] > ew["total_return"]:
            return_comment = "EW 대비 누적수익률 개선"
        elif overlay["total_return"] < ew["total_return"]:
            return_comment = "EW 대비 누적수익률 하락"
        else:
            return_comment = "EW와 누적수익률 동일"

        if overlay["avg_turnover"] > 0:
            turnover_comment = "HSI 상태 변화에 따라 Turnover 발생"
        else:
            turnover_comment = "Turnover 없음"

        rows.append(
            {
                "method": method,
                "strategy": "HSI_state5_overlay_v2b",
                "question": (
                    "conflict를 방어전환이 아닌 관찰 상태로 처리한 완화형 HSI overlay는 "
                    "EW 대비 어떤 위험·수익 특성을 보이는가?"
                ),
                "return_comment": return_comment,
                "mdd_comment": mdd_comment,
                "turnover_comment": turnover_comment,
                "interpretation": (
                    "main_v2b는 HSI 5상태 체계는 유지하되 conflict를 관찰 상태로 처리한 규칙이다. "
                    "따라서 위험 악화가 명확한 risk_warning과 accident_zone에서만 방어적으로 움직인다. "
                    "이 결과는 HSI 상태명과 실제 포트폴리오 행동을 분리하여 설계할 필요가 있음을 보여준다."
                ),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 6. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("21_main_v2b_evaluate_performance.py 실행 시작")
    print("=" * 70)

    backtest_rank = read_csv_with_date(BACKTEST_RANK_PATH)
    backtest_zscore = read_csv_with_date(BACKTEST_ZSCORE_PATH)
    turnover_summary = read_csv_with_date(TURNOVER_SUMMARY_PATH)

    backtest_all = pd.concat([backtest_rank, backtest_zscore], ignore_index=True)

    print("[로드 완료]")
    print(f"- backtest_rank: {backtest_rank.shape}")
    print(f"- backtest_zscore: {backtest_zscore.shape}")
    print(f"- backtest_all: {backtest_all.shape}")
    print(f"- turnover_summary: {turnover_summary.shape}")

    performance_summary = make_performance_summary(backtest_all, turnover_summary)
    performance_summary = add_diff_vs_ew(performance_summary)

    drawdown_timeseries = make_drawdown_timeseries(backtest_all)
    cumulative_return_timeseries = make_cumulative_return_timeseries(backtest_all)
    performance_comment = make_performance_comment(performance_summary)

    performance_summary.to_csv(OUTPUT_PERFORMANCE_PATH, index=False, encoding="utf-8-sig")
    drawdown_timeseries.to_csv(OUTPUT_DRAWDOWN_PATH, index=False, encoding="utf-8-sig")
    cumulative_return_timeseries.to_csv(OUTPUT_CUMULATIVE_PATH, index=False, encoding="utf-8-sig")
    performance_comment.to_csv(OUTPUT_COMMENT_PATH, index=False, encoding="utf-8-sig")

    print("\n[저장 완료]")
    print(f"- {OUTPUT_PERFORMANCE_PATH}")
    print(f"- {OUTPUT_DRAWDOWN_PATH}")
    print(f"- {OUTPUT_CUMULATIVE_PATH}")
    print(f"- {OUTPUT_COMMENT_PATH}")

    print("\n[main_v2b 성과 요약]")
    display_cols = [
        "method",
        "strategy",
        "months",
        "total_return",
        "cagr",
        "annual_volatility",
        "sharpe",
        "sortino",
        "mdd",
        "calmar",
        "win_rate",
        "avg_turnover",
        "total_return_diff_vs_ew",
        "cagr_diff_vs_ew",
        "mdd_diff_vs_ew",
        "sharpe_diff_vs_ew",
        "avg_turnover_diff_vs_ew",
    ]

    display_cols = [col for col in display_cols if col in performance_summary.columns]
    print(performance_summary[display_cols])

    print("\n[해석 코멘트]")
    print(performance_comment)

    print("\n" + "=" * 70)
    print("21_main_v2b_evaluate_performance.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()
