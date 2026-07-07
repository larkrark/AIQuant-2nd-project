"""
Stage A (리포트 00~01): 데이터 기준 정리.

ETF 3종 가격 로드 → 월말 리샘플링 → 월간 수익률(decimal) → 유니버스 확정.
참고 소스: legacy/00_check_korea_etf_data.py, legacy/10_build_hsi_signal_inputs.py,
data/processed/korea_etf_price_clean.csv
리포트 데이터: main_final_monthly_return_decimal.csv (현재 repo에 없음)
"""

import pandas as pd

from common.paths import PROCESSED_DIR


def load_prices() -> pd.DataFrame:
    raise NotImplementedError(
        f"load_prices: 가격 소스 확정 후 구현. 후보: {PROCESSED_DIR / 'korea_etf_price_clean.csv'}"
    )


def to_monthly_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """일별 가격 → 월말 → 월간 수익률(decimal, Date + ASSETS)."""
    raise NotImplementedError("to_monthly_returns: 월말 리샘플링·수익률 로직 구현 필요.")
