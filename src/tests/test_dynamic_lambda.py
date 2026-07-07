"""
동적 lambda(감마) 프리미티브 테스트.
실행: cd src && python3 -m pytest tests/test_dynamic_lambda.py -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline.stage_d_lambda import (  # noqa: E402
    apply_lambda_partial_adjustment,
    dynamic_lambda_series,
)

WCOLS = ["069500_weight", "114260_weight", "153130_weight"]


def _targets(n=6):
    dates = pd.date_range("2020-01-31", periods=n, freq="ME")
    a = np.linspace(0.2, 0.7, n)
    return pd.DataFrame({"Date": dates, "069500_weight": a,
                         "114260_weight": (1 - a) * 0.5, "153130_weight": (1 - a) * 0.5})


def test_scalar_equals_constant_array():
    tgt = _targets()
    out_scalar = apply_lambda_partial_adjustment(tgt, 0.3, WCOLS)
    out_array = apply_lambda_partial_adjustment(tgt, np.full(len(tgt), 0.3), WCOLS)
    assert np.allclose(out_scalar[WCOLS].to_numpy(), out_array[WCOLS].to_numpy())


def test_array_length_mismatch_raises():
    tgt = _targets()
    try:
        apply_lambda_partial_adjustment(tgt, np.array([0.3, 0.3]), WCOLS); raised = False
    except ValueError:
        raised = True
    assert raised


def test_array_weights_sum_preserved():
    tgt = _targets()
    lam = np.linspace(0.1, 0.5, len(tgt))
    out = apply_lambda_partial_adjustment(tgt, lam, WCOLS)
    assert np.allclose(out[WCOLS].sum(axis=1).to_numpy(), 1.0)


def test_dynamic_lambda_clip_bounds():
    risk = np.array([-3, 0, 3, 10, -10], dtype=float)
    lam = dynamic_lambda_series(risk, lambda_base=0.3, gamma=-0.05, lam_min=0.1, lam_max=0.5)
    assert (lam >= 0.1 - 1e-12).all() and (lam <= 0.5 + 1e-12).all()


def test_dynamic_lambda_risk_decreases_lambda():
    """gamma<0: 위험점수 높을수록 lambda 낮음(방어)."""
    risk = np.array([-2, 0, 2], dtype=float)
    lam = dynamic_lambda_series(risk, lambda_base=0.3, gamma=-0.05, lam_min=0.05, lam_max=0.6)
    assert lam[0] > lam[1] > lam[2]


def test_dynamic_lambda_bad_bounds_raise():
    try:
        dynamic_lambda_series([0.0], lambda_base=0.3, gamma=-0.05, lam_min=0.5, lam_max=0.1)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_dynamic_lambda_end_to_end():
    """동적 lambda_t 를 부분조정에 실제로 적용."""
    tgt = _targets(8)
    rng = np.random.default_rng(0)
    risk = rng.normal(0, 1, len(tgt))
    lam_t = dynamic_lambda_series(risk, lambda_base=0.3, gamma=-0.05, lam_min=0.1, lam_max=0.5)
    out = apply_lambda_partial_adjustment(tgt, lam_t, WCOLS)
    assert np.allclose(out[WCOLS].sum(axis=1), 1.0)
    assert len(out) == len(tgt)


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
