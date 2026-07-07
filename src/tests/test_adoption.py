"""
adoption_decision (사전등록 비열등 4조건) 단위 테스트.
실행: cd src && python3 -m pytest tests/test_adoption.py -q
"""

import sys
from pathlib import Path

import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline.stage_selection import adoption_decision  # noqa: E402
from pipeline.config import ADOPTION  # noqa: E402


def _metrics(cand_row):
    # 대칭 참조: λ0.1(Calmar 0.60, MDD -14, tail -3.0, turn 2.5), λ0.3(Calmar 0.58, MDD -15, tail -3.1, turn 6.0)
    rows = [
        {"strategy": "lambda_0.1", "Calmar_net": 0.60, "MDD_pct": -14.0, "tail_month_avg_pct": -3.0, "avg_turnover_pct": 2.5},
        {"strategy": "lambda_0.3", "Calmar_net": 0.58, "MDD_pct": -15.0, "tail_month_avg_pct": -3.1, "avg_turnover_pct": 6.0},
        cand_row,
    ]
    return pd.DataFrame(rows)


def test_reference_values():
    out = adoption_decision(_metrics({"strategy": "c", "Calmar_net": 0.60, "MDD_pct": -14, "tail_month_avg_pct": -3.0, "avg_turnover_pct": 2.5}))
    r = out[out["strategy"] == "c"].iloc[0]
    # 참조: max(0.60,0.58)*0.9=0.54, MDD floor -14-2=-16, tail floor -3.0-0.3=-3.3, turnover cap 6.0*1.5=9.0
    assert r["ref_calmar_x0.9"] == 0.54
    assert r["ref_mdd_floor"] == -16.0
    assert r["ref_tail_floor"] == -3.3
    assert r["ref_turnover_cap"] == 9.0


def test_passing_candidate():
    out = adoption_decision(_metrics({"strategy": "dyn", "Calmar_net": 0.77, "MDD_pct": -12.6, "tail_month_avg_pct": -3.0, "avg_turnover_pct": 4.8}))
    r = out[out["strategy"] == "dyn"].iloc[0]
    assert r["cond1_calmar"] and r["cond2_mdd"] and r["cond3_tail"] and r["cond4_turnover"]
    assert bool(r["non_inferior"]) is True


def test_fail_calmar():
    out = adoption_decision(_metrics({"strategy": "c", "Calmar_net": 0.50, "MDD_pct": -12, "tail_month_avg_pct": -3.0, "avg_turnover_pct": 4.0}))
    r = out[out["strategy"] == "c"].iloc[0]
    assert not r["cond1_calmar"] and not r["non_inferior"]  # 0.50 < 0.54


def test_fail_mdd():
    out = adoption_decision(_metrics({"strategy": "c", "Calmar_net": 0.77, "MDD_pct": -17, "tail_month_avg_pct": -3.0, "avg_turnover_pct": 4.0}))
    r = out[out["strategy"] == "c"].iloc[0]
    assert not r["cond2_mdd"] and not r["non_inferior"]  # -17 < -16 floor


def test_fail_turnover():
    out = adoption_decision(_metrics({"strategy": "c", "Calmar_net": 0.77, "MDD_pct": -12, "tail_month_avg_pct": -3.0, "avg_turnover_pct": 12.0}))
    r = out[out["strategy"] == "c"].iloc[0]
    assert not r["cond4_turnover"] and not r["non_inferior"]  # 12 > 9 cap


def test_fail_tail():
    out = adoption_decision(_metrics({"strategy": "c", "Calmar_net": 0.77, "MDD_pct": -12, "tail_month_avg_pct": -3.8, "avg_turnover_pct": 4.0}))
    r = out[out["strategy"] == "c"].iloc[0]
    assert not r["cond3_tail"] and not r["non_inferior"]  # -3.8 < -3.3 floor


def test_missing_reference_raises():
    m = pd.DataFrame([{"strategy": "x", "Calmar_net": 0.6, "MDD_pct": -12, "tail_month_avg_pct": -3, "avg_turnover_pct": 3}])
    try:
        adoption_decision(m); raised = False
    except ValueError:
        raised = True
    assert raised


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
