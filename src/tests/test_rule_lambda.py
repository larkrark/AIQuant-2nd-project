"""
rule_based_dynamic_lambda (E30-M 규칙형 동적 λ) 단위 테스트.
실행: cd src && python3 -m pytest tests/test_rule_lambda.py -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline.stage_d_lambda import rule_based_dynamic_lambda  # noqa: E402

RULE = dict(lam_default=0.3, lam_high_risk=0.1, lam_easing=0.5,
            vol_z_high=1.0, drawdown_low=-0.10, macro_risk_high=2, relief_persist_months=3)


def _cond(vol_z=0.0, dd=0.0, macro=0, state="neutral_watch", mom_z=0.0, n=1):
    return pd.DataFrame({"volatility_z": [vol_z] * n, "rolling_drawdown": [dd] * n,
                         "macro_risk_score": [macro] * n, "hsi_state": [state] * n, "momentum_z": [mom_z] * n})


def test_default_is_03():
    lam, lab = rule_based_dynamic_lambda(_cond(), **RULE)
    assert lam[0] == 0.3 and lab[0] == "default"


def test_high_risk_by_volatility():
    lam, lab = rule_based_dynamic_lambda(_cond(vol_z=1.5), **RULE)
    assert lam[0] == 0.1 and lab[0] == "high_risk"


def test_high_risk_by_drawdown():
    lam, _ = rule_based_dynamic_lambda(_cond(dd=-0.15), **RULE)
    assert lam[0] == 0.1


def test_high_risk_by_macro():
    lam, _ = rule_based_dynamic_lambda(_cond(macro=2), **RULE)
    assert lam[0] == 0.1  # rate_up+fx_up>=2


def test_easing_requires_all_three():
    # risk_relief 3개월 지속 + vol_z<0 + mom_z>0
    c = pd.DataFrame({"volatility_z": [-0.5, -0.5, -0.5], "rolling_drawdown": [0, 0, 0],
                      "macro_risk_score": [0, 0, 0], "hsi_state": ["risk_relief"] * 3, "momentum_z": [0.5, 0.5, 0.5]})
    lam, lab = rule_based_dynamic_lambda(c, **RULE)
    assert lab[2] == "easing" and lam[2] == 0.5   # 3개월째 지속
    assert lab[0] != "easing"                     # 1개월째는 미충족


def test_high_risk_overrides_easing():
    # 완화 조건 + 고위험(vol_z>1) 동시 → 고위험 우선
    c = pd.DataFrame({"volatility_z": [1.5], "rolling_drawdown": [0], "macro_risk_score": [0],
                      "hsi_state": ["risk_relief"], "momentum_z": [1.0]})
    lam, lab = rule_based_dynamic_lambda(c, **RULE)
    assert lab[0] == "high_risk" and lam[0] == 0.1


def test_nan_conditions_default():
    c = _cond(vol_z=np.nan, mom_z=np.nan)
    lam, lab = rule_based_dynamic_lambda(c, **RULE)
    assert lam[0] == 0.3  # NaN 비교는 False → 기본


def test_all_lambda_in_valid_range():
    rng = np.random.default_rng(0)
    n = 50
    c = pd.DataFrame({"volatility_z": rng.normal(0, 1, n), "rolling_drawdown": rng.uniform(-0.2, 0, n),
                      "macro_risk_score": rng.integers(0, 3, n),
                      "hsi_state": rng.choice(["risk_relief", "neutral_watch", "risk_warning"], n),
                      "momentum_z": rng.normal(0, 1, n)})
    lam, lab = rule_based_dynamic_lambda(c, **RULE)
    assert set(np.unique(lam)) <= {0.1, 0.3, 0.5}
    assert ((lam > 0) & (lam <= 1)).all()


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
