"""
백테스트 공통 헬퍼.

- 월말 상태/비중(Date=t)을 다음 달(t+1) 수익률에 정렬(look-ahead 방어)
- 전략 월수익률 계산
- turnover 계산
"""

import numpy as np
import pandas as pd

from .config import ASSETS


def align_weights_with_next_returns(
    weights: pd.DataFrame,
    monthly_returns: pd.DataFrame,
    assets: list[str] | None = None,
) -> pd.DataFrame:
    """
    Date=t의 비중을 Date=t+1의 월간 수익률에 정렬한다.
    weights: Date + <asset>_weight, monthly_returns: Date + <asset>.
    마지막 달은 다음 달 수익률이 없어 제외.
    """
    assets = assets or ASSETS
    ret = monthly_returns[["Date"] + assets].sort_values("Date").reset_index(drop=True)
    for a in assets:
        ret[f"{a}_next_return"] = ret[a].shift(-1)
    ret["next_return_date"] = ret["Date"].shift(-1)

    w = weights.sort_values("Date").reset_index(drop=True)
    aligned = w.merge(
        ret[["Date", "next_return_date"] + [f"{a}_next_return" for a in assets]],
        on="Date", how="left",
    )
    return aligned.dropna(subset=[f"{a}_next_return" for a in assets]).reset_index(drop=True)


def strategy_monthly_returns(aligned: pd.DataFrame, assets: list[str] | None = None) -> pd.Series:
    """정렬된 표에서 월별 전략수익률 = sum(weight_t * next_return)."""
    assets = assets or ASSETS
    out = 0.0
    for a in assets:
        out = out + aligned[f"{a}_weight"] * aligned[f"{a}_next_return"]
    return out


def calculate_turnover(weights: pd.DataFrame, assets: list[str] | None = None) -> pd.Series:
    """
    월별 turnover = 0.5 * sum(|w_t - w_{t-1}|). 첫 달은 0.
    weights는 시간순으로 정렬돼 있다고 가정.
    """
    assets = assets or ASSETS
    cols = [f"{a}_weight" for a in assets]
    diff = weights[cols].diff().abs()
    turnover = 0.5 * diff.sum(axis=1)
    if len(turnover) > 0:
        turnover.iloc[0] = 0.0
    return turnover
