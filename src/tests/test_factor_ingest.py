"""
pipeline.factor_ingest 단위 테스트 (합성 가격 + 실제 파일 스모크).
실행: cd src && python3 -m pytest tests/test_factor_ingest.py -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline.factor_ingest import build_etf_factors, load_external_factors, CLEAN_PRICE_PATH, load_clean_prices  # noqa: E402
from pipeline.stage_factor import build_factor_matrix, full_period_loading  # noqa: E402


def _synth_prices(days=90, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2018-01-01", periods=days)
    def walk(p0, mu, sig):
        r = rng.normal(mu, sig, days)
        return p0 * np.cumprod(1 + r)
    return pd.DataFrame({
        "Date": dates,
        "069500": walk(20000, 0.0004, 0.012),
        "114260": walk(50000, 0.0001, 0.003),
        "153130": walk(90000, 0.00005, 0.0005),
    })


def test_etf_factor_columns_and_types():
    fac = build_etf_factors(_synth_prices())
    expected = {"Date", "market_ret", "bond_ret", "cash_ret", "mom_3m", "mom_12m",
                "realized_vol", "downside_semidev", "stock_bond_corr_6m"}
    assert expected <= set(fac.columns)
    assert len(fac) >= 3  # 최소 3개월


def test_realized_vol_nonnegative_and_downside_le_vol():
    fac = build_etf_factors(_synth_prices(days=250))
    assert (fac["realized_vol"].dropna() >= 0).all()
    # 하방 반편차는 전체 실현변동성보다 크지 않아야 한다(대체로)
    both = fac.dropna(subset=["realized_vol", "downside_semidev"])
    assert (both["downside_semidev"] <= both["realized_vol"] + 1e-9).mean() > 0.8


def test_market_ret_matches_month_end_pct_change():
    prices = _synth_prices(days=200)
    fac = build_etf_factors(prices)
    me = prices.set_index("Date")["069500"].resample("ME").last()
    expected = me.pct_change().reset_index(drop=True)
    got = fac["market_ret"].reset_index(drop=True)
    # 길이 정렬 후 비교(둘 다 첫 달 NaN)
    m = pd.concat([expected, got], axis=1).dropna()
    assert np.allclose(m.iloc[:, 0].to_numpy(), m.iloc[:, 1].to_numpy(), atol=1e-9)


def test_external_absent_returns_none(tmp_path):
    assert load_external_factors(tmp_path / "nope.csv") is None


def test_real_file_chain_smoke():
    """실제 monthly_factors 소스가 있으면 build_factor_matrix→회귀까지 연결 확인."""
    if not CLEAN_PRICE_PATH.exists():
        return  # 데이터 없으면 skip
    fac = build_etf_factors(load_clean_prices())
    cols = ["market_ret", "bond_ret", "realized_vol"]
    fm = build_factor_matrix(fac, factor_cols=cols)  # expanding z-score + lag
    # 합성 전략수익률로 회귀가 도는지(에러 없이 결과 반환)
    rng = np.random.default_rng(1)
    y = pd.Series(rng.normal(0, 0.03, len(fm)))
    res = full_period_loading(y, fm, factor_cols=cols)
    assert "loadings" in res and len(res["loadings"]) == 3


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            import inspect
            if "tmp_path" in inspect.signature(fn).parameters:
                import tempfile
                fn(Path(tempfile.mkdtemp()))
            else:
                fn()
            print(f"PASS {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1; print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
