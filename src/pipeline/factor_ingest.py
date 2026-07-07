"""
팩터 데이터 인제스트 (0단계).

목표: data/processed/factors/monthly_factors.csv (Date + 팩터 원자료, RAW) 생성.
- ETF 파생 팩터: repo 내 data/processed/korea_etf_price_clean.csv(일별 종가)에서 계산.
- 외부 팩터(VKOSPI·거래대금·신용스프레드·term spread·미국 스필오버): 사용자 제공 CSV
  (data/raw/external_factors.csv, Date + 컬럼)가 있으면 병합, 없으면 생략(안내).

주의: 여기서는 표준화하지 않는다(RAW). 표준화·시차·룩어헤드 차단은 stage_factor.build_factor_matrix 담당.
의존성: numpy/pandas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.config import ASSETS
from common.io_utils import save_table
from common.paths import PROCESSED_DIR, RAW_DIR

CLEAN_PRICE_PATH = PROCESSED_DIR / "korea_etf_price_clean.csv"
EXTERNAL_RAW_PATH = RAW_DIR / "external_factors.csv"
OUTPUT_PATH = PROCESSED_DIR / "factors" / "monthly_factors.csv"

EXTERNAL_FACTOR_COLS = ["vkospi", "liquidity", "credit_spread", "term_spread", "us_spillover"]
TRADING_DAYS_PER_MONTH = 21


# ------------------------------------------------------------
# 가격 로드
# ------------------------------------------------------------

def load_clean_prices(path=None) -> pd.DataFrame:
    """일별 종가(wide: Date + 티커) 로드. 첫 컬럼을 Date로 간주."""
    path = path or CLEAN_PRICE_PATH
    df = pd.read_csv(path)
    df = df.rename(columns={df.columns[0]: "Date"})
    df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values("Date").reset_index(drop=True)


# ------------------------------------------------------------
# ETF 파생 팩터
# ------------------------------------------------------------

def build_etf_factors(prices: pd.DataFrame, assets=None) -> pd.DataFrame:
    """
    일별 종가 → 월별 ETF 파생 팩터(RAW).
    반환 컬럼: Date, market_ret, bond_ret, cash_ret, mom_3m, mom_12m,
              realized_vol, downside_semidev, stock_bond_corr_6m
    """
    assets = assets or ASSETS
    px = prices.set_index("Date")[assets].astype(float)

    dret = px.pct_change()
    me = px.resample("ME").last()
    mret = me.pct_change()

    risk, bond, cash = assets[0], assets[1], assets[2]  # 069500, 114260, 153130

    out = pd.DataFrame(index=me.index)
    out["market_ret"] = mret[risk]
    out["bond_ret"] = mret[bond]
    out["cash_ret"] = mret[cash]
    out["mom_3m"] = me[risk].pct_change(3)
    out["mom_12m"] = me[risk].pct_change(12)
    # 월별 실현변동성(일별 수익률 → 월 표준편차 연율화 근사)
    out["realized_vol"] = dret[risk].resample("ME").std() * np.sqrt(TRADING_DAYS_PER_MONTH)
    # 하방 반편차(음수 일수익률만)
    neg = dret[risk].where(dret[risk] < 0)
    out["downside_semidev"] = neg.resample("ME").std() * np.sqrt(TRADING_DAYS_PER_MONTH)
    # 주식-채권 6개월 rolling 상관(레짐)
    out["stock_bond_corr_6m"] = mret[risk].rolling(6).corr(mret[bond])

    out = out.reset_index().rename(columns={"index": "Date"})
    if "Date" not in out.columns:
        out = out.rename(columns={out.columns[0]: "Date"})
    return out


# ------------------------------------------------------------
# 외부 팩터 병합
# ------------------------------------------------------------

def load_external_factors(path=None) -> pd.DataFrame | None:
    """외부 팩터 CSV(Date + 컬럼) 로드. 없으면 None."""
    path = path or EXTERNAL_RAW_PATH
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df = df.rename(columns={df.columns[0]: "Date"}) if "Date" not in df.columns else df
    df["Date"] = pd.to_datetime(df["Date"])
    # 월말 정렬
    df = df.sort_values("Date")
    df["Date"] = df["Date"] + pd.offsets.MonthEnd(0)
    return df.groupby("Date").last().reset_index()


# ------------------------------------------------------------
# 오케스트레이션
# ------------------------------------------------------------

def build_monthly_factors(*, save: bool = True, price_path=None, external_path=None) -> pd.DataFrame:
    """
    ETF 파생 팩터 + (있으면) 외부 팩터를 병합해 monthly_factors.csv 생성.
    반환: 병합된 팩터 DataFrame.
    """
    prices = load_clean_prices(price_path)
    factors = build_etf_factors(prices)

    ext = load_external_factors(external_path)
    if ext is not None:
        factors = factors.merge(ext, on="Date", how="left")
        present = [c for c in EXTERNAL_FACTOR_COLS if c in factors.columns]
        note = f"외부 팩터 병합: {present}" if present else "외부 파일에 알려진 팩터 컬럼 없음"
    else:
        note = ("외부 팩터 파일 없음(data/raw/external_factors.csv). "
                "VKOSPI·거래대금·신용스프레드·term spread·미국 스필오버는 ECOS/KRX 인제스트 후 병합.")

    if save:
        save_table(factors, OUTPUT_PATH)
    return factors, note


def summarize_factors(factors: pd.DataFrame) -> pd.DataFrame:
    """생성된 팩터의 커버리지·결측 요약(품질 점검용)."""
    rows = []
    for c in [x for x in factors.columns if x != "Date"]:
        s = factors[c]
        rows.append({
            "factor": c,
            "n": int(s.notna().sum()),
            "n_missing": int(s.isna().sum()),
            "first_valid": factors.loc[s.first_valid_index(), "Date"] if s.notna().any() else None,
            "mean": float(s.mean()) if s.notna().any() else np.nan,
            "std": float(s.std()) if s.notna().any() else np.nan,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    factors, note = build_monthly_factors(save=True)
    print(note)
    print(f"생성: {OUTPUT_PATH}  shape={factors.shape}")
    print(summarize_factors(factors).to_string(index=False))
