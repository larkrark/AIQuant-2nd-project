from pathlib import Path

import numpy as np
import pandas as pd


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
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"

BACKTEST_RANK_PATH = TABLE_DIR / "main_v2_backtest_timeseries_rank.csv"
BACKTEST_ZSCORE_PATH = TABLE_DIR / "main_v2_backtest_timeseries_zscore.csv"
TURNOVER_SUMMARY_PATH = TABLE_DIR / "main_v2_turnover_summary.csv"

OUTPUT_PERFORMANCE_PATH = TABLE_DIR / "main_v2_performance_summary.csv"
OUTPUT_DRAWDOWN_PATH = TABLE_DIR / "main_v2_drawdown_timeseries.csv"
OUTPUT_CUMULATIVE_PATH = TABLE_DIR / "main_v2_cumulative_return_timeseries.csv"
OUTPUT_COMMENT_PATH = TABLE_DIR / "main_v2_performance_comparison_comment.csv"


# ============================================================
# 1. 데이터 로드
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


# ============================================================
# 2. 성과지표 계산
# ============================================================

def calculate_performance_metrics(group: pd.DataFrame) -> pd.Series:
    group = group.sort_values("Date").copy()

    monthly_returns = group["monthly_return"].dropna()
    months = len(monthly_returns)

    if months == 0:
        raise ValueError("monthly_return 데이터가 없습니다.")

    cumulative = (1 + monthly_returns).cumprod()
    total_return = cumulative.iloc[-1] - 1

    years = months / 12
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else np.nan

    monthly_mean = monthly_returns.mean()
    monthly_std = monthly_returns.std(ddof=1)

    annual_volatility = monthly_std * np.sqrt(12)

    if annual_volatility == 0 or pd.isna(annual_volatility):
        sharpe = np.nan
    else:
        sharpe = (monthly_mean * 12) / annual_volatility

    running_max = cumulative.cummax()
    drawdown = cumulative / running_max - 1
    mdd = drawdown.min()

    if mdd == 0 or pd.isna(mdd):
        calmar = np.nan
    else:
        calmar = cagr / abs(mdd)

    downside = monthly_returns[monthly_returns < 0]
    downside_std = downside.std(ddof=1) * np.sqrt(12)

    if downside_std == 0 or pd.isna(downside_std):
        sortino = np.nan
    else:
        sortino = (monthly_mean * 12) / downside_std

    win_rate = (monthly_returns > 0).mean()

    return pd.Series(
        {
            "months": months,
            "total_return": total_return,
            "cagr": cagr,
            "annual_volatility": annual_volatility,
            "sharpe": sharpe,
            "sortino": sortino,
            "mdd": mdd,
            "calmar": calmar,
            "win_rate": win_rate,
            "mean_monthly_return": monthly_mean,
            "std_monthly_return": monthly_std,
            "min_monthly_return": monthly_returns.min(),
            "max_monthly_return": monthly_returns.max(),
        }
    )


def make_performance_summary(backtest: pd.DataFrame, turnover_summary: pd.DataFrame) -> pd.DataFrame:
    summary = (
        backtest
        .groupby(["method", "strategy"], dropna=False)
        .apply(calculate_performance_metrics)
        .reset_index()
    )

    summary = summary.merge(
        turnover_summary,
        on=["method", "strategy"],
        how="left",
        suffixes=("", "_turnover"),
    )

    return summary


# ============================================================
# 3. EW 대비 차이 계산
# ============================================================

def add_diff_vs_ew(summary: pd.DataFrame) -> pd.DataFrame:
    result = summary.copy()

    metrics = [
        "total_return",
        "cagr",
        "annual_volatility",
        "sharpe",
        "sortino",
        "mdd",
        "calmar",
        "win_rate",
        "mean_monthly_return",
        "avg_turnover",
        "max_turnover",
        "total_turnover",
    ]

    for method in result["method"].dropna().unique():
        ew_row = result[(result["method"] == method) & (result["strategy"] == "EW")]

        if ew_row.empty:
            continue

        ew_values = ew_row.iloc[0]

        for metric in metrics:
            if metric in result.columns:
                result.loc[result["method"] == method, f"{metric}_diff_vs_ew"] = (
                    result.loc[result["method"] == method, metric] - ew_values[metric]
                )

    return result


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