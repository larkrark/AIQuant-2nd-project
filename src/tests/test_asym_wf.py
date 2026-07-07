"""
비대칭 λ + walk-forward/IS-OOS 검증 단위 테스트.
실행: cd src && python3 -m pytest tests/test_asym_wf.py -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline.stage_d_lambda import apply_asymmetric_lambda, apply_lambda_partial_adjustment  # noqa: E402
from pipeline.validation import split_is_oos, walk_forward_metrics, walk_forward_segments  # noqa: E402

WCOLS = ["069500_weight", "114260_weight", "153130_weight"]


def _targets(n=8):
    dates = pd.date_range("2020-01-31", periods=n, freq="ME")
    # 069500 목표를 오르내리게
    a = np.array([0.7, 0.2, 0.5, 0.2, 0.7, 0.35, 0.2, 0.5])[:n]
    return pd.DataFrame({"Date": dates, "069500_weight": a,
                         "114260_weight": (1 - a) * 0.6, "153130_weight": (1 - a) * 0.4})


# --- 비대칭 λ ---
def test_asym_weights_sum_one():
    out = apply_asymmetric_lambda(_targets(), 0.1, 0.3)
    assert np.allclose(out[WCOLS].sum(axis=1).to_numpy(), 1.0, atol=1e-9)


def test_asym_equals_symmetric_when_equal():
    tgt = _targets()
    a = apply_asymmetric_lambda(tgt, 0.3, 0.3)[WCOLS].to_numpy()
    b = apply_lambda_partial_adjustment(tgt, 0.3)[WCOLS].to_numpy()
    assert np.allclose(a, b)  # 대각선(λ_up=λ_down)=대칭


def _one(a):
    dates = pd.date_range("2020-01-31", periods=len(a), freq="ME")
    a = np.array(a, dtype=float)
    return pd.DataFrame({"Date": dates, "069500_weight": a,
                         "114260_weight": (1 - a) * 0.6, "153130_weight": (1 - a) * 0.4})


def test_asym_direction_labels():
    # 위험자산 목표가 이전 실현비중보다 낮아지면 down, 높아지면 up (target vs 실현비중)
    down = apply_asymmetric_lambda(_one([0.8, 0.2]), 0.1, 0.3)
    assert down.loc[1, "dir_label"] == "down"
    up = apply_asymmetric_lambda(_one([0.2, 0.8]), 0.1, 0.3)
    assert up.loc[1, "dir_label"] == "up"


def test_asym_range_guard():
    try:
        apply_asymmetric_lambda(_targets(), 0.0, 0.3); raised = False
    except ValueError:
        raised = True
    assert raised


# --- walk-forward / IS-OOS ---
def test_walk_forward_segments_count():
    segs = walk_forward_segments(147, train=60, test=12, step=12)
    assert len(segs) == 8
    assert segs[0] == (60, 72) and segs[-1][1] == 147


def test_walk_forward_metrics_keys():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.005, 0.03, 100))
    m = walk_forward_metrics(r, train=60, test=12, step=12)
    assert m["n_segments"] >= 1 and m["n_test_months"] > 0
    assert set(["wf_cagr_pct", "wf_mdd_pct", "wf_calmar"]) <= set(m)


def test_walk_forward_too_short():
    m = walk_forward_metrics(pd.Series(np.zeros(30)), train=60, test=12, step=12)
    assert m["n_segments"] == 0


def test_split_is_oos():
    df = pd.DataFrame({"Date": pd.date_range("2019-01-31", periods=40, freq="ME"), "x": range(40)})
    is_df, oos_df = split_is_oos(df)
    assert (is_df["Date"] <= pd.Timestamp("2020-12-31")).all()
    assert (oos_df["Date"] >= pd.Timestamp("2021-01-01")).all()
    assert len(is_df) + len(oos_df) == len(df)


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
