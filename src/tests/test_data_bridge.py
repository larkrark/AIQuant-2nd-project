"""
data_bridge self-test 검증 (repo 파일 있을 때만; 없으면 skip).
실행: cd src && python3 -m pytest tests/test_data_bridge.py -q
"""

import sys
from pathlib import Path

import numpy as np

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline import data_bridge as db  # noqa: E402
from pipeline.stage_attribution import monthly_attribution  # noqa: E402
from pipeline.stage_d_lambda import apply_lambda_partial_adjustment, rule_based_dynamic_lambda  # noqa: E402
from pipeline.config import DYNAMIC_LAMBDA_RULE  # noqa: E402

WCOLS = db.WCOLS
_HAVE = db.FACTORS_PATH.exists() and (db.CANON_BASELINE.exists() or db.SURR_BASELINE.exists())


def _prep():
    ar = db.load_asset_returns()
    bw, _ = db.load_baseline_weights()
    common = set(ar["Date"]) & set(bw["Date"])
    ar = ar[ar["Date"].isin(common)].sort_values("Date").reset_index(drop=True)
    bw = bw[bw["Date"].isin(common)].sort_values("Date").reset_index(drop=True)
    return ar, bw


def test_inputs_load_and_align():
    if not _HAVE:
        return
    ar, bw = _prep()
    assert {"Date", *db.ASSETS} <= set(ar.columns)
    assert {"Date", *WCOLS} <= set(bw.columns)
    assert np.allclose(bw[WCOLS].sum(axis=1).to_numpy(), 1.0, atol=1e-9)


def test_lambda1_equals_baseline():
    if not _HAVE:
        return
    _, bw = _prep()
    lam1 = apply_lambda_partial_adjustment(bw, 1.0)
    assert np.allclose(lam1[WCOLS].to_numpy(), bw[WCOLS].to_numpy())


def test_attribution_identity_on_real_bridge():
    if not _HAVE:
        return
    ar, bw = _prep()
    ret, base_w, lam_w, turn = db.build_attribution_inputs(bw, ar, 0.3)
    m = monthly_attribution(ret, base_w, lam_w, turn, cost_rate=0.0010)
    assert m["residual_check"].abs().max() < 1e-10
    assert (m["cost_effect"] <= 0).all()


def test_candidate_series_turnover_order():
    if not _HAVE:
        return
    ar, bw = _prep()
    cs_base = db._candidate_series(bw, ar)                                   # baseline(λ=1)
    cs_01 = db._candidate_series(apply_lambda_partial_adjustment(bw, 0.1), ar)
    assert len(cs_01) > 0 and {"Date", "ret", "turnover"} <= set(cs_01.columns)
    # λ=0.1은 baseline보다 저회전
    assert cs_01["turnover"].mean() <= cs_base["turnover"].mean() + 1e-9


def test_dynamic_v1_builds_and_valid():
    if not _HAVE:
        return
    ar, bw = _prep()
    cond = db.build_condition_variables(bw, ar, db.load_hsi_states())
    lam_t, labels = rule_based_dynamic_lambda(cond, **DYNAMIC_LAMBDA_RULE)
    assert len(lam_t) == len(bw)
    assert set(np.unique(lam_t)) <= {0.1, 0.3, 0.5}
    dyn_w = apply_lambda_partial_adjustment(bw, lam_t)
    assert np.allclose(dyn_w[WCOLS].sum(axis=1).to_numpy(), 1.0, atol=1e-9)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1; print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
