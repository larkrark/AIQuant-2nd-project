"""
성과지표 계산 (단일 정본).

월간 수익률 시계열에서 CAGR/MDD/Sharpe/Sortino/Calmar 등을 계산한다.
연율화 계수는 월간 기준 12, sqrt(12).
"""

import numpy as np
import pandas as pd


def calculate_performance_metrics(
    monthly_returns: pd.Series,
    *,
    periods_per_year: int = 12,
) -> dict:
    """
    월간 수익률 Series -> 성과지표 dict.

    반환 키: months, total_return, cagr, annual_volatility, sharpe,
    sortino, mdd, calmar, win_rate, mean_monthly_return, std_monthly_return.
    """
    r = pd.Series(monthly_returns).dropna()
    months = len(r)
    if months == 0:
        raise ValueError("monthly_returns 데이터가 없습니다.")

    cumulative = (1 + r).cumprod()
    total_return = cumulative.iloc[-1] - 1

    years = months / periods_per_year
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else np.nan

    mean = r.mean()
    std = r.std(ddof=1)
    annual_vol = std * np.sqrt(periods_per_year)
    sharpe = np.nan if (annual_vol == 0 or pd.isna(annual_vol)) else (mean * periods_per_year) / annual_vol

    running_max = cumulative.cummax()
    drawdown = cumulative / running_max - 1
    mdd = drawdown.min()
    calmar = np.nan if (mdd == 0 or pd.isna(mdd)) else cagr / abs(mdd)

    downside = r[r < 0]
    downside_std = downside.std(ddof=1) * np.sqrt(periods_per_year)
    sortino = np.nan if (downside_std == 0 or pd.isna(downside_std)) else (mean * periods_per_year) / downside_std

    win_rate = (r > 0).mean()

    return {
        "months": months,
        "total_return": total_return,
        "cagr": cagr,
        "annual_volatility": annual_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "mdd": mdd,
        "calmar": calmar,
        "win_rate": win_rate,
        "mean_monthly_return": mean,
        "std_monthly_return": std,
    }


def drawdown_series(cumulative: pd.Series) -> pd.Series:
    """누적수익률 시계열 -> drawdown 시계열."""
    running_max = cumulative.cummax()
    return cumulative / running_max - 1
