"""
stage_attribution 단위 테스트 (합성 데이터).
실행: cd src && python3 -m pytest tests/test_attribution.py -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline.stage_attribution import (  # noqa: E402
    monthly_attribution,
    attribution_summary,
    cumulative_attribution,
    run_attribution,
)

ASSETS = ["069500", "114260", "153130"]
WCOLS = [f"{a}_weight" for a in ASSETS]


def _synth(n=36, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-31", periods=n, freq="ME")
    returns = pd.DataFrame({"Date": dates})
    returns["069500"] = rng.normal(0.006, 0.04, n)
    returns["114260"] = rng.normal(0.002, 0.01, n)
    returns["153130"] = rng.normal(0.001, 0.002, n)
    # baseline(즉시비중): 상태에 따라 변동, 합 1
    base = pd.DataFrame({"Date": dates})
    a = rng.uniform(0.1, 0.7, n)
    b = (1 - a) * 0.5
    base["069500_weight"] = a
    base["114260_weight"] = b
    base["153130_weight"] = 1 - a - b
    # lambda 실현비중: baseline을 0.3으로 부분조정한 형태(여기선 단순히 baseline과 EW의 가중평균)
    lam = base.copy()
    for c, ewv in zip(WCOLS, [1/3, 1/3, 1/3]):
        lam[c] = 0.5 * base[c] + 0.5 * ewv
    turnover = pd.Series(rng.uniform(0, 0.08, n))
    return returns, base, lam, turnover


def test_additive_identity_holds():
    """4효과 합 == 초과수익 (residual ≈ 0)."""
    returns, base, lam, turn = _synth()
    m = monthly_attribution(returns, base, lam, turn, cost_rate=0.0010)
    assert np.allclose(m["residual_check"].to_numpy(), 0.0, atol=1e-12)


def test_total_equals_lambda_net_minus_ew():
    returns, base, lam, turn = _synth()
    m = monthly_attribution(returns, base, lam, turn, cost_rate=0.0010)
    assert np.allclose(m["total_excess_vs_ew"], m["R_lambda_net"] - m["R_ew"], atol=1e-12)


def test_cost_effect_nonpositive():
    returns, base, lam, turn = _synth()
    m = monthly_attribution(returns, base, lam, turn, cost_rate=0.0010)
    assert (m["cost_effect"] <= 0).all()  # 비용은 항상 드래그
    # cost_effect == -turnover*rate
    assert np.allclose(m["cost_effect"].to_numpy(), -turn.to_numpy() * 0.0010, atol=1e-15)


def test_saa_effect_matches_bm_minus_ew():
    """SAA효과 = (70/20/10 − EW)·수익률."""
    returns, base, lam, turn = _synth()
    m = monthly_attribution(returns, base, lam, turn, cost_rate=0.0)
    bm = np.array([0.70, 0.20, 0.10]); ew = np.array([1/3, 1/3, 1/3])
    r = returns[ASSETS].to_numpy()
    expected = ((bm - ew) * r).sum(axis=1)
    assert np.allclose(m["saa_effect"].to_numpy(), expected, atol=1e-12)


def test_summary_shares_and_total():
    returns, base, lam, turn = _synth()
    res = run_attribution(returns, base, lam, turn, cost_rate=0.0010)
    summ = res["summary"]
    # 4효과 합계 == total 행
    eff_sum = summ[summ["effect"].isin(["saa", "timing", "lambda", "cost"])]["sum_contribution"].sum()
    total = summ[summ["effect"] == "total_excess_vs_ew"]["sum_contribution"].iloc[0]
    assert np.isclose(eff_sum, total, atol=1e-10)


def test_cumulative_monotonic_length():
    returns, base, lam, turn = _synth(n=24)
    m = monthly_attribution(returns, base, lam, turn)
    cum = cumulative_attribution(m)
    assert len(cum) == 24
    # 누적 total 마지막값 == 월별 total 합
    assert np.isclose(cum["cum_total_excess_vs_ew"].iloc[-1], m["total_excess_vs_ew"].sum(), atol=1e-12)


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
