"""
백테스트 공통 헬퍼.

17(main_v2)과 19(main_v2b)에 완전히 동일하게 복제돼 있던
정렬/turnover/정렬점검 함수를 통합한다.

주의: 월말 HSI 상태(Date=t)를 다음 달(Date=t+1) 월간 수익률에 적용하는
look-ahead 방어 정렬 규칙을 그대로 유지한다.
"""

import numpy as np
import pandas as pd

from .config import ASSETS


def align_state_with_next_returns(
    state5: pd.DataFrame,
    monthly_returns: pd.DataFrame,
    method: str,
) -> pd.DataFrame:
    """
    Date=t의 HSI 상태와 비중을 Date=t+1의 월간 수익률에 정렬한다.

    마지막 달은 다음 달 수익률이 없으므로 제외한다.
    """
    returns = monthly_returns[["Date"] + ASSETS].copy()
    returns = returns.sort_values("Date").reset_index(drop=True)

    for asset in ASSETS:
        returns[f"{asset}_next_return"] = returns[asset].shift(-1)

    returns["next_return_date"] = returns["Date"].shift(-1)

    aligned = state5.copy()
    aligned = aligned.sort_values("Date").reset_index(drop=True)

    aligned = aligned.merge(
        returns[
            ["Date", "next_return_date"]
            + [f"{asset}_next_return" for asset in ASSETS]
        ],
        on="Date",
        how="left",
    )

    aligned["method"] = method

    next_return_cols = [f"{asset}_next_return" for asset in ASSETS]
    aligned = aligned.dropna(subset=next_return_cols).reset_index(drop=True)

    return aligned


def calculate_turnover(weights: pd.DataFrame) -> pd.DataFrame:
    """
    월별 turnover 계산.
    turnover = 0.5 * sum(abs(w_t - w_{t-1})), 각 (method, strategy) 첫 달은 0.
    """
    weight_cols = [f"{asset}_weight" for asset in ASSETS]

    result_parts = []

    for (_method, _strategy), group in weights.groupby(["method", "strategy"], dropna=False):
        group = group.sort_values("Date").copy()

        diff = group[weight_cols].diff().abs()
        group["turnover"] = 0.5 * diff.sum(axis=1)
        group.loc[group.index[0], "turnover"] = 0.0

        result_parts.append(group)

    return pd.concat(result_parts, ignore_index=True)


def make_turnover_summary(turnover: pd.DataFrame) -> pd.DataFrame:
    """(method, strategy)별 turnover 요약(평균/최대/합계)."""
    return (
        turnover
        .groupby(["method", "strategy"], dropna=False)
        .agg(
            months=("Date", "count"),
            avg_turnover=("turnover", "mean"),
            max_turnover=("turnover", "max"),
            total_turnover=("turnover", "sum"),
        )
        .reset_index()
    )


def make_alignment_check(
    aligned_rank: pd.DataFrame,
    aligned_zscore: pd.DataFrame,
) -> pd.DataFrame:
    """
    rank/zscore 정렬 결과 점검표.

    주의: `alignment_flag`는 현재 리터럴 "OK"로 고정돼 있다(기존 동작 유지).
    실제 계산된 플래그로 바꾸는 것은 로드맵 4.4(별도 범위) 사항이다.
    """
    rows = []

    for method, aligned in [("rank", aligned_rank), ("zscore", aligned_zscore)]:
        rows.append(
            {
                "method": method,
                "rows": len(aligned),
                "first_signal_date": aligned["Date"].min(),
                "last_signal_date": aligned["Date"].max(),
                "first_return_date": aligned["next_return_date"].min(),
                "last_return_date": aligned["next_return_date"].max(),
                "missing_next_return_cells": aligned[
                    [f"{asset}_next_return" for asset in ASSETS]
                ].isna().sum().sum(),
                "alignment_rule": "signal_date의 HSI 상태를 next_return_date의 월간 수익률에 적용",
                "alignment_flag": "OK",
            }
        )

    return pd.DataFrame(rows)
