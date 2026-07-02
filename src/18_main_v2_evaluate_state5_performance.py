import pandas as pd

from common.io_utils import read_csv_with_date
from common.metrics import add_diff_vs_ew, calculate_performance_metrics, make_performance_summary
from common.paths import TABLE_DIR


"""
18_main_v2_evaluate_state5_performance.py

목적
----
17번에서 생성한 main_v2 HSI 5상태 overlay 백테스트 결과를 읽어
정식 성과평가표를 만든다.

입력
----
output/tables/main_v2_backtest_timeseries_rank.csv
output/tables/main_v2_backtest_timeseries_zscore.csv
output/tables/main_v2_turnover_summary.csv

출력
----
output/tables/main_v2_performance_summary.csv
output/tables/main_v2_drawdown_timeseries.csv
output/tables/main_v2_cumulative_return_timeseries.csv
output/tables/main_v2_performance_comparison_comment.csv
"""


# ============================================================
# 0. 경로 설정 (common.paths.TABLE_DIR 사용)
# ============================================================

BACKTEST_RANK_PATH = TABLE_DIR / "main_v2_backtest_timeseries_rank.csv"
BACKTEST_ZSCORE_PATH = TABLE_DIR / "main_v2_backtest_timeseries_zscore.csv"
TURNOVER_SUMMARY_PATH = TABLE_DIR / "main_v2_turnover_summary.csv"

OUTPUT_PERFORMANCE_PATH = TABLE_DIR / "main_v2_performance_summary.csv"
OUTPUT_DRAWDOWN_PATH = TABLE_DIR / "main_v2_drawdown_timeseries.csv"
OUTPUT_CUMULATIVE_PATH = TABLE_DIR / "main_v2_cumulative_return_timeseries.csv"
OUTPUT_COMMENT_PATH = TABLE_DIR / "main_v2_performance_comparison_comment.csv"


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
        "signal_date",
        "hsi_state5",
        "state_name_kr",
        "monthly_return",
        "cumulative_return",
    ]

    existing_cols = [col for col in cols if col in backtest.columns]
    return backtest[existing_cols].copy()


# ============================================================
# 5. 해석용 코멘트 표
# ============================================================

def make_comparison_comment(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for method in summary["method"].dropna().unique():
        method_df = summary[summary["method"] == method].copy()

        ew = method_df[method_df["strategy"] == "EW"]
        overlay = method_df[method_df["strategy"] == "HSI_state5_overlay"]

        if ew.empty or overlay.empty:
            continue

        ew = ew.iloc[0]
        overlay = overlay.iloc[0]

        if overlay["mdd"] > ew["mdd"]:
            mdd_comment = "MDD 개선"
        elif overlay["mdd"] < ew["mdd"]:
            mdd_comment = "MDD 악화"
        else:
            mdd_comment = "MDD 동일"

        if overlay["cagr"] > ew["cagr"]:
            cagr_comment = "CAGR 개선"
        elif overlay["cagr"] < ew["cagr"]:
            cagr_comment = "CAGR 하락"
        else:
            cagr_comment = "CAGR 동일"

        if overlay["annual_volatility"] < ew["annual_volatility"]:
            vol_comment = "변동성 감소"
        elif overlay["annual_volatility"] > ew["annual_volatility"]:
            vol_comment = "변동성 증가"
        else:
            vol_comment = "변동성 동일"

        rows.append(
            {
                "method": method,
                "comparison": "EW vs HSI_state5_overlay",
                "cagr_comment": cagr_comment,
                "mdd_comment": mdd_comment,
                "volatility_comment": vol_comment,
                "turnover_comment": "HSI overlay는 상태 변화에 따라 turnover가 발생함",
                "interpretation": (
                    "HSI 5상태 overlay는 정상적으로 구현되었으나, "
                    "현재 θ 규칙 기준으로 EW 대비 성과 개선 여부는 "
                    "CAGR, MDD, 변동성, Turnover를 함께 보아야 한다."
                ),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 6. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("18_main_v2_evaluate_state5_performance.py 실행 시작")
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
    comparison_comment = make_comparison_comment(performance_summary)

    performance_summary.to_csv(OUTPUT_PERFORMANCE_PATH, index=False, encoding="utf-8-sig")
    drawdown_timeseries.to_csv(OUTPUT_DRAWDOWN_PATH, index=False, encoding="utf-8-sig")
    cumulative_return_timeseries.to_csv(OUTPUT_CUMULATIVE_PATH, index=False, encoding="utf-8-sig")
    comparison_comment.to_csv(OUTPUT_COMMENT_PATH, index=False, encoding="utf-8-sig")

    print("\n[저장 완료]")
    print(f"- {OUTPUT_PERFORMANCE_PATH}")
    print(f"- {OUTPUT_DRAWDOWN_PATH}")
    print(f"- {OUTPUT_CUMULATIVE_PATH}")
    print(f"- {OUTPUT_COMMENT_PATH}")

    print("\n[성과 요약]")
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
    print(comparison_comment)

    print("\n" + "=" * 70)
    print("18_main_v2_evaluate_state5_performance.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()
