"""
검증 하네스: IS/OOS 분리 + Walk-forward (보고서 §9, §3.9).

- split_is_oos       : IS(≤2020-12) / OOS(≥2021-01) 분리
- walk_forward_segments : train→test→step 이동 구간(테스트 인덱스) 생성
- walk_forward_returns  : 테스트 구간 수익률을 이어붙인 OOS-like 시계열
- walk_forward_metrics  : 이어붙인 시계열의 성과지표

규칙형/고정 전략은 창별 재적합이 없으므로, walk-forward는 "창을 이동하며 평가 구간
성과가 유지되는지"를 확인하는 안정성 검증으로 사용한다(과적합 방어 근거).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.metrics import calculate_performance_metrics
from pipeline.config import IS_END, OOS_START, WALK_FORWARD


def split_is_oos(df: pd.DataFrame, *, date_col: str = "Date"):
    """(IS, OOS) 분리. IS ≤ IS_END, OOS ≥ OOS_START."""
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col])
    is_df = d[d[date_col] <= pd.Timestamp(IS_END)].reset_index(drop=True)
    oos_df = d[d[date_col] >= pd.Timestamp(OOS_START)].reset_index(drop=True)
    return is_df, oos_df


def walk_forward_segments(n: int, *, train=None, test=None, step=None):
    """
    길이 n 시계열에서 (test_start, test_end) 인덱스 구간 목록.
    train개월 학습창 이후 test개월을 평가하고, step개월씩 이동.
    """
    train = WALK_FORWARD["train"] if train is None else train
    test = WALK_FORWARD["test"] if test is None else test
    step = WALK_FORWARD["step"] if step is None else step
    segs = []
    start = train
    while start < n:
        end = min(start + test, n)
        if end > start:
            segs.append((start, end))
        start += step
    return segs


def walk_forward_returns(returns, *, train=None, test=None, step=None):
    """테스트 구간 수익률을 이어붙인 시계열 + 구간 목록."""
    r = pd.Series(returns).reset_index(drop=True)
    segs = walk_forward_segments(len(r), train=train, test=test, step=step)
    if not segs:
        return pd.Series(dtype=float), segs
    idx = np.concatenate([np.arange(s, e) for s, e in segs])
    return r.iloc[idx].reset_index(drop=True), segs


def walk_forward_metrics(returns, *, train=None, test=None, step=None) -> dict:
    """walk-forward 이어붙인 시계열의 성과지표."""
    stitched, segs = walk_forward_returns(returns, train=train, test=test, step=step)
    if len(stitched) == 0:
        return {"n_segments": 0, "n_test_months": 0}
    m = calculate_performance_metrics(stitched)
    return {"n_segments": len(segs), "n_test_months": len(stitched),
            "wf_cagr_pct": m["cagr"] * 100, "wf_mdd_pct": m["mdd"] * 100,
            "wf_sharpe": m["sharpe"], "wf_calmar": m["calmar"]}
