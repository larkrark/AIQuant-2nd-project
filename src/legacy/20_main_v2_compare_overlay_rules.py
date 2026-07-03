from pathlib import Path

import numpy as np
import pandas as pd


"""
20_main_v2_compare_overlay_rules.py

목적
----
main_v2와 main_v2b의 HSI 5상태 overlay 결과를 비교한다.

비교 대상
--------
1. EW
2. main_v2  : conflict를 소폭 방어로 처리
3. main_v2b : conflict를 관찰·중립처럼 처리

핵심 질문
--------
충돌 상태를 방어 신호가 아니라 관찰 신호로 두면,
불필요한 수익률 희생과 Turnover가 줄어드는가?

입력
----
output/tables/main_v2_performance_summary.csv
output/tables/main_v2b_backtest_timeseries_rank.csv
output/tables/main_v2b_backtest_timeseries_zscore.csv
output/tables/main_v2b_turnover_summary.csv

출력
----
output/tables/main_v2_rule_comparison_summary.csv
output/tables/main_v2_rule_comparison_comment.csv
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"

MAIN_V2_PERFORMANCE_PATH = TABLE_DIR / "main_v2_performance_summary.csv"

MAIN_V2B_BACKTEST_RANK_PATH = TABLE_DIR / "main_v2b_backtest_timeseries_rank.csv"
MAIN_V2B_BACKTEST_ZSCORE_PATH = TABLE_DIR / "main_v2b_backtest_timeseries_zscore.csv"
MAIN_V2B_TURNOVER_PATH = TABLE_DIR / "main_v2b_turnover_summary.csv"

OUTPUT_COMPARISON_SUMMARY_PATH = TABLE_DIR / "main_v2_rule_comparison_summary.csv"
OUTPUT_COMPARISON_COMMENT_PATH = TABLE_DIR / "main_v2_rule_comparison_comment.csv"


# ============================================================
# 1. 데이터 로드
# ============================================================

def read_csv(path: Path) -> pd.DataFrame:
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

    win_rate = (monthly_returns > 0).mean()

    return pd.Series(
        {
            "months": months,
            "total_return": total_return,
            "cagr": cagr,
            "annual_volatility": annual_volatility,
            "sharpe": sharpe,
            "mdd": mdd,
            "calmar": calmar,
            "win_rate": win_rate,
            "mean_monthly_return": monthly_mean,
            "min_monthly_return": monthly_returns.min(),
            "max_monthly_return": monthly_returns.max(),
        }
    )


def make_v2b_performance_summary(
    backtest_rank: pd.DataFrame,
    backtest_zscore: pd.DataFrame,
    turnover_summary: pd.DataFrame,
) -> pd.DataFrame:
    backtest_all = pd.concat([backtest_rank, backtest_zscore], ignore_index=True)

    summary = (
        backtest_all
        .groupby(["method", "strategy"], dropna=False)
        .apply(calculate_performance_metrics)
        .reset_index()
    )

    summary = summary.merge(
        turnover_summary,
        on=["method", "strategy"],
        how="left",
    )

    return summary


# ============================================================
# 3. 비교용 표 정리
# ============================================================

def normalize_main_v2_summary(main_v2: pd.DataFrame) -> pd.DataFrame:
    """
    main_v2 성과표를 비교용 형태로 정리한다.
    """

    result = main_v2.copy()

    result["experiment"] = np.where(
        result["strategy"] == "EW",
        "EW",
        "main_v2_conflict_defense",
    )

    result["rule_description"] = np.where(
        result["strategy"] == "EW",
        "기본 동일비중",
        "conflict를 소폭 방어로 처리",
    )

    return result


def normalize_main_v2b_summary(v2b: pd.DataFrame) -> pd.DataFrame:
    """
    main_v2b 성과표를 비교용 형태로 정리한다.
    """

    result = v2b.copy()

    result["experiment"] = np.where(
        result["strategy"] == "EW",
        "EW",
        "main_v2b_conflict_watch",
    )

    result["rule_description"] = np.where(
        result["strategy"] == "EW",
        "기본 동일비중",
        "conflict를 관찰로 처리",
    )

    return result


def build_rule_comparison(main_v2: pd.DataFrame, main_v2b: pd.DataFrame) -> pd.DataFrame:
    v2 = normalize_main_v2_summary(main_v2)
    v2b = normalize_main_v2b_summary(main_v2b)

    combined = pd.concat([v2, v2b], ignore_index=True)

    # EW는 main_v2와 main_v2b에 중복으로 존재하므로 하나만 남긴다.
    combined = combined.drop_duplicates(
        subset=["method", "experiment"],
        keep="first",
    ).reset_index(drop=True)

    # 보기 좋은 순서 부여
    order_map = {
        "EW": 0,
        "main_v2_conflict_defense": 1,
        "main_v2b_conflict_watch": 2,
    }

    combined["experiment_order"] = combined["experiment"].map(order_map)

    combined = combined.sort_values(
        ["method", "experiment_order"]
    ).reset_index(drop=True)

    # EW 대비 차이 계산
    metrics = [
        "total_return",
        "cagr",
        "annual_volatility",
        "sharpe",
        "mdd",
        "calmar",
        "win_rate",
        "avg_turnover",
        "total_turnover",
    ]

    for method in combined["method"].dropna().unique():
        ew = combined[
            (combined["method"] == method)
            & (combined["experiment"] == "EW")
        ]

        if ew.empty:
            continue

        ew = ew.iloc[0]

        for metric in metrics:
            if metric in combined.columns:
                combined.loc[
                    combined["method"] == method,
                    f"{metric}_diff_vs_ew",
                ] = combined.loc[combined["method"] == method, metric] - ew[metric]

    # main_v2 대비 main_v2b 차이 계산
    for method in combined["method"].dropna().unique():
        v2 = combined[
            (combined["method"] == method)
            & (combined["experiment"] == "main_v2_conflict_defense")
        ]

        if v2.empty:
            continue

        v2 = v2.iloc[0]

        for metric in metrics:
            if metric in combined.columns:
                combined.loc[
                    (combined["method"] == method)
                    & (combined["experiment"] == "main_v2b_conflict_watch"),
                    f"{metric}_diff_vs_main_v2",
                ] = (
                    combined.loc[
                        (combined["method"] == method)
                        & (combined["experiment"] == "main_v2b_conflict_watch"),
                        metric,
                    ]
                    - v2[metric]
                )

    return combined


# ============================================================
# 4. 해석 코멘트 생성
# ============================================================

def make_rule_comparison_comment(comparison: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for method in comparison["method"].dropna().unique():
        method_df = comparison[comparison["method"] == method]

        v2 = method_df[method_df["experiment"] == "main_v2_conflict_defense"]
        v2b = method_df[method_df["experiment"] == "main_v2b_conflict_watch"]
        ew = method_df[method_df["experiment"] == "EW"]

        if v2.empty or v2b.empty or ew.empty:
            continue

        v2 = v2.iloc[0]
        v2b = v2b.iloc[0]
        ew = ew.iloc[0]

        total_return_improved_vs_v2 = v2b["total_return"] > v2["total_return"]
        turnover_reduced_vs_v2 = v2b["avg_turnover"] < v2["avg_turnover"]
        mdd_improved_vs_v2 = v2b["mdd"] > v2["mdd"]

        mdd_better_than_ew = v2b["mdd"] > ew["mdd"]
        total_return_better_than_ew = v2b["total_return"] > ew["total_return"]

        if (
            total_return_improved_vs_v2
            and turnover_reduced_vs_v2
            and mdd_improved_vs_v2
        ):
            answer_to_question = (
                "conflict를 관찰로 처리하면 main_v2 대비 수익률 희생과 Turnover가 줄고 "
                "MDD도 개선되는 것으로 나타났다."
            )
        elif total_return_improved_vs_v2 and turnover_reduced_vs_v2:
            answer_to_question = (
                "conflict를 관찰로 처리하면 main_v2 대비 수익률 희생과 Turnover는 줄었으나, "
                "MDD 개선은 제한적이다."
            )
        else:
            answer_to_question = (
                "conflict를 관찰로 처리한 효과가 일관되게 확인되지는 않았다."
            )

        if mdd_better_than_ew and not total_return_better_than_ew:
            ew_comment = (
                "EW 대비 누적수익률은 낮지만, MDD는 EW와 비슷하거나 소폭 개선되었다."
            )
        elif mdd_better_than_ew and total_return_better_than_ew:
            ew_comment = (
                "EW 대비 누적수익률과 MDD가 모두 개선되었다."
            )
        elif not mdd_better_than_ew and not total_return_better_than_ew:
            ew_comment = (
                "EW 대비 누적수익률과 MDD 모두 우위가 확인되지는 않았다."
            )
        else:
            ew_comment = (
                "EW 대비 일부 지표는 개선되었으나 종합 판단이 필요하다."
            )

        rows.append(
            {
                "method": method,
                "question": (
                    "충돌 상태를 방어 신호가 아니라 관찰 신호로 두면, "
                    "불필요한 수익률 희생과 Turnover가 줄어드는가?"
                ),
                "answer_to_question": answer_to_question,
                "ew_comparison_comment": ew_comment,
                "interpretation": (
                    "이번 비교는 HSI 상태명과 포트폴리오 행동을 분리해야 함을 보여준다. "
                    "conflict는 위험 악화 확정 상태라기보다 신호 혼조 상태에 가까우므로, "
                    "즉시 방어전환하기보다 관찰 상태로 처리하는 규칙이 더 자연스러울 수 있다."
                ),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 5. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("20_main_v2_compare_overlay_rules.py 실행 시작")
    print("=" * 70)

    main_v2 = read_csv(MAIN_V2_PERFORMANCE_PATH)

    v2b_backtest_rank = read_csv(MAIN_V2B_BACKTEST_RANK_PATH)
    v2b_backtest_zscore = read_csv(MAIN_V2B_BACKTEST_ZSCORE_PATH)
    v2b_turnover = read_csv(MAIN_V2B_TURNOVER_PATH)

    print("[로드 완료]")
    print(f"- main_v2: {main_v2.shape}")
    print(f"- v2b_backtest_rank: {v2b_backtest_rank.shape}")
    print(f"- v2b_backtest_zscore: {v2b_backtest_zscore.shape}")
    print(f"- v2b_turnover: {v2b_turnover.shape}")

    v2b_summary = make_v2b_performance_summary(
        v2b_backtest_rank,
        v2b_backtest_zscore,
        v2b_turnover,
    )

    comparison = build_rule_comparison(main_v2, v2b_summary)
    comment = make_rule_comparison_comment(comparison)

    comparison.to_csv(OUTPUT_COMPARISON_SUMMARY_PATH, index=False, encoding="utf-8-sig")
    comment.to_csv(OUTPUT_COMPARISON_COMMENT_PATH, index=False, encoding="utf-8-sig")

    print("\n[저장 완료]")
    print(f"- {OUTPUT_COMPARISON_SUMMARY_PATH}")
    print(f"- {OUTPUT_COMPARISON_COMMENT_PATH}")

    print("\n[비교 요약]")
    display_cols = [
        "method",
        "experiment",
        "rule_description",
        "months",
        "total_return",
        "cagr",
        "annual_volatility",
        "sharpe",
        "mdd",
        "calmar",
        "win_rate",
        "avg_turnover",
        "total_return_diff_vs_ew",
        "mdd_diff_vs_ew",
        "avg_turnover_diff_vs_ew",
        "total_return_diff_vs_main_v2",
        "mdd_diff_vs_main_v2",
        "avg_turnover_diff_vs_main_v2",
    ]

    display_cols = [col for col in display_cols if col in comparison.columns]
    print(comparison[display_cols])

    print("\n[해석 코멘트]")
    print(comment)

    print("\n" + "=" * 70)
    print("20_main_v2_compare_overlay_rules.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()