"""
Stage G (리포트 17): Benchmark alignment.

Fixed 70/20/10 BM(메인 BM)을 추가해 Lambda 후보/EW/HSI baseline을 동일 기준으로 비교.
새 후보를 만드는 단계가 아니라 비교 기준을 정렬하는 단계.
"""

import pandas as pd

from common.config import ASSETS
from pipeline.config import FIXED_BM_WEIGHTS


def fixed_benchmark_weights(dates) -> pd.DataFrame:
    """주어진 날짜 시계열에 Fixed 70/20/10 고정비중을 부여한 표."""
    df = pd.DataFrame({"Date": pd.to_datetime(pd.Series(dates)).reset_index(drop=True)})
    for a in ASSETS:
        df[f"{a}_weight"] = FIXED_BM_WEIGHTS[a]
    df["strategy_name"] = "Fixed_70_20_10_BM"
    return df
