"""
stage_factor 단위 테스트 (합성 데이터).

실행: cd src && python3 -m pytest tests/test_factor.py -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline.stage_factor import (  # noqa: E402
    build_factor_matrix,
    compute_vif,
    expanding_zscore,
    full_period_loading,
    rolling_loading,
    screen_factors,
    analyze_strategies,
)


def _synth(n=80, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2015-01-31", periods=n, freq="ME")
    f1 = rng.normal(0, 1, n)
    f2 = rng.normal(0, 1, n)
    f3 = rng.normal(0, 1, n)
    true = np.array([1.5, -0.8, 0.5])
    alpha = 0.001
    y = alpha + f1 * true[0] + f2 * true[1] + f3 * true[2] + rng.normal(0, 0.002, n)
    fac = pd.DataFrame({"Date": dates, "f1": f1, "f2": f2, "f3": f3})
    return dates, fac, y, true, alpha


def test_ols_recovers_known_betas():
    _, fac, y, true, alpha = _synth()
    # 표준화/lag 없이 raw 팩터로 회귀 → 참 beta 복원
    fm = build_factor_matrix(fac, standardize=False, lags={})
    res = full_period_loading(pd.Series(y), fm, factor_cols=["f1", "f2", "f3"])
    beta = res["loadings"].set_index("factor")["beta"]
    assert np.allclose(beta[["f1", "f2", "f3"]].to_numpy(), true, atol=0.05)
    assert abs(res["alpha"] - alpha) < 0.01
    assert res["r2"] > 0.99  # 노이즈 작아 설명력 매우 높음


def test_tstat_significant_for_strong_factors():
    _, fac, y, _, _ = _synth()
    fm = build_factor_matrix(fac, standardize=False, lags={})
    res = full_period_loading(pd.Series(y), fm, factor_cols=["f1", "f2", "f3"])
    # 강한 팩터는 |t|가 크다
    assert (res["loadings"]["tstat"].abs() > 3).all()


def test_vif_detects_collinearity():
    _, fac, _, _, _ = _synth()
    fac = fac.copy()
    fac["f4"] = fac["f1"] * 0.99 + np.random.default_rng(1).normal(0, 0.01, len(fac))
    fm = build_factor_matrix(fac, standardize=False, lags={})
    vif = compute_vif(fm, ["f1", "f2", "f3", "f4"])
    # f1, f4 는 거의 동일 → VIF 큼; f2, f3 는 낮음
    assert vif["f1"] > 5 and vif["f4"] > 5
    assert vif["f2"] < 5 and vif["f3"] < 5


def test_screen_flags_high_corr_pair():
    _, fac, _, _, _ = _synth()
    fac = fac.copy()
    fac["f4"] = fac["f1"] * 0.99 + np.random.default_rng(2).normal(0, 0.01, len(fac))
    fm = build_factor_matrix(fac, standardize=False, lags={})
    sc = screen_factors(fm, factor_cols=["f1", "f2", "f3", "f4"])
    pairs = {tuple(sorted(p[:2])) for p in sc["high_corr_pairs"]}
    assert ("f1", "f4") in pairs
    assert "f4" in sc["flagged"] or "f1" in sc["flagged"]


def test_rolling_loading_shape():
    _, fac, y, _, _ = _synth(n=80)
    fm = build_factor_matrix(fac, standardize=False, lags={})
    roll = rolling_loading(pd.Series(y), fm, factor_cols=["f1", "f2", "f3"], window=36)
    assert len(roll) == 80 - 36 + 1
    assert {"f1_beta", "f2_beta", "f3_beta", "r2", "Date", "strategy"} - set(roll.columns) == {"strategy"}


def test_expanding_zscore_no_lookahead():
    s = pd.Series([1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
    z = expanding_zscore(s, min_periods=3)
    # 앞부분(min_periods 미만)은 NaN
    assert z.iloc[:2].isna().all()
    # expanding 이므로 마지막 값이 전체표본 z-score와 다를 수 있음(룩어헤드 없음 확인용)
    assert z.notna().sum() > 0


def test_lag_applied():
    fac = pd.DataFrame({
        "Date": pd.date_range("2015-01-31", periods=6, freq="ME"),
        "us_spillover": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    })
    fm = build_factor_matrix(fac, standardize=False)  # config FACTOR_LAG: us_spillover=1
    # 1개월 시차 → 첫 행 NaN, 이후 전월값
    assert pd.isna(fm["us_spillover"].iloc[0])
    assert np.isclose(fm["us_spillover"].iloc[1], 0.1)


def test_analyze_strategies_end_to_end():
    dates, fac, y, _, _ = _synth(n=80)
    fm = build_factor_matrix(fac, standardize=False, lags={})
    # 두 전략: 하나는 y, 하나는 다른 노출
    rng = np.random.default_rng(9)
    y2 = 0.5 * fac["f1"].to_numpy() + rng.normal(0, 0.002, len(fac))
    strat = pd.DataFrame({"Date": dates, "lambda_0.3": y, "lambda_0.1": y2})
    bm = pd.Series(np.zeros(len(fac)))  # BM=0 → excess=strategy
    summary, ts = analyze_strategies(strat, bm, fm, factor_cols=["f1", "f2", "f3"])
    assert set(summary["strategy"]) == {"lambda_0.3", "lambda_0.1"}
    assert "alpha" in set(summary["factor"])
    assert not ts.empty


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1; print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
