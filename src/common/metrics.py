"""
성과지표 계산.

기존 18/20/21에 복제돼 있던 성과지표 함수를 단일 정본으로 통합한다.
(20의 복사본은 Sortino와 months==0 가드가 누락된 채 어긋나 있었으므로,
 완전판인 18/21 구현을 정본으로 채택한다.)
"""

import numpy as np
import pandas as pd


def calculate_performance_metrics(group: pd.DataFrame) -> pd.Series:
    """
    한 (method, strategy) 그룹의 월간 수익률에서 성과지표를 계산한다.

    반환 컬럼: months, total_return, cagr, annual_volatility, sharpe,
    sortino, mdd, calmar, win_rate, mean_monthly_return, std_monthly_return,
    min_monthly_return, max_monthly_return.
    """
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

    downside_returns = monthly_returns[monthly_returns < 0]
    downside_std = downside_returns.std(ddof=1) * np.sqrt(12)

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


# EW 대비 차이 계산에 사용하는 표준 지표 목록
DIFF_METRICS = [
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


def make_performance_summary(
    backtest: pd.DataFrame,
    turnover_summary: pd.DataFrame,
) -> pd.DataFrame:
    """(method, strategy)별 성과지표 표를 만들고 turnover 요약을 붙인다."""
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


def add_diff_vs_ew(summary: pd.DataFrame, metrics: list[str] | None = None) -> pd.DataFrame:
    """각 method 내에서 EW 전략 대비 지표 차이(`_diff_vs_ew`)를 추가한다."""
    if metrics is None:
        metrics = DIFF_METRICS

    result = summary.copy()

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
