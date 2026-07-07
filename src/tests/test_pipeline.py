"""
새 파이프라인 로직 단위 테스트 (common + pipeline).

실행: cd src && python3 -m pytest tests/test_pipeline.py -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import backtest, metrics  # noqa: E402
from pipeline import config  # noqa: E402
from pipeline.stage_d_lambda import apply_lambda_partial_adjustment, apply_transaction_cost  # noqa: E402
from pipeline.stage_g_benchmark import fixed_benchmark_weights  # noqa: E402
from pipeline.stage_selection import build_cost_sensitivity_table, build_final_judgement, add_cost_drag_columns  # noqa: E402

WCOLS = ["069500_weight", "114260_weight", "153130_weight"]


def _targets():
    return pd.DataFrame({
        "Date": pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"]),
        "069500_weight": [0.70, 0.20, 0.20],
        "114260_weight": [0.20, 0.40, 0.40],
        "153130_weight": [0.10, 0.40, 0.40],
    })


# --- common.metrics ---
def test_metrics_basic():
    m = metrics.calculate_performance_metrics(pd.Series([0.10, -0.05, 0.02]))
    assert m["months"] == 3
    assert np.isclose(m["total_return"], 1.10 * 0.95 * 1.02 - 1)
    assert "sortino" in m and "calmar" in m


# --- common.backtest ---
def test_align_and_turnover():
    w = pd.DataFrame({
        "Date": pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"]),
        "069500_weight": [0.5, 0.3, 0.3], "114260_weight": [0.25, 0.35, 0.35], "153130_weight": [0.25, 0.35, 0.35],
    })
    ret = pd.DataFrame({
        "Date": pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"]),
        "069500": [0.01, -0.05, 0.03], "114260": [0.002, 0.003, 0.001], "153130": [0.001, 0.001, 0.001],
    })
    aligned = backtest.align_weights_with_next_returns(w, ret)
    assert len(aligned) == 2  # 마지막 달 제외
    assert np.isclose(aligned.iloc[0]["069500_next_return"], -0.05)  # t → t+1
    t = backtest.calculate_turnover(w)
    assert t.iloc[0] == 0.0
    assert np.isclose(t.iloc[1], 0.2)


# --- lambda ---
def test_lambda_1_equals_target():
    out = apply_lambda_partial_adjustment(_targets(), 1.0, WCOLS)
    assert np.allclose(out[WCOLS].to_numpy(), _targets()[WCOLS].to_numpy())


def test_lambda_half():
    out = apply_lambda_partial_adjustment(_targets(), 0.5, WCOLS)
    exp = np.array([0.70, 0.20, 0.10]) + 0.5 * (np.array([0.20, 0.40, 0.40]) - np.array([0.70, 0.20, 0.10]))
    assert np.allclose(out.loc[1, WCOLS].to_numpy(dtype=float), exp)
    assert np.allclose(out[WCOLS].sum(axis=1), 1.0)


def test_lambda_guard():
    try:
        apply_lambda_partial_adjustment(_targets(), 0.0, WCOLS); raised = False
    except ValueError:
        raised = True
    assert raised


def test_transaction_cost():
    net = apply_transaction_cost(pd.Series([0.02, -0.01]), pd.Series([0.10, 0.20]), 0.0010)
    assert np.allclose(net.to_numpy(), [0.02 - 0.0001, -0.01 - 0.0002])


# --- benchmark ---
def test_fixed_bm():
    bm = fixed_benchmark_weights(pd.to_datetime(["2020-01-31", "2020-02-29"]))
    assert np.allclose(bm["069500_weight"], 0.70)
    assert (bm["strategy_name"] == "Fixed_70_20_10_BM").all()


# --- selection ---
def _synth_backtest_all():
    # 두 후보(EW, lambda_0.3) × 24개월 합성 시계열
    n = 24
    dates = pd.date_range("2020-01-31", periods=n, freq="ME").strftime("%Y-%m")
    rng = np.random.default_rng(0)
    rows = []
    for key, sname, mean, turn in [("baseline|EW", "EW", 0.005, 0.0),
                                   ("lambda|lambda_0.3", "lambda_0.3", 0.007, 0.05)]:
        rets = rng.normal(mean, 0.02, n)
        for i in range(n):
            rows.append({"candidate_key": key, "strategy_name": sname, "source_type": key.split("|")[0],
                         "strategy_return": rets[i], "turnover": turn})
    return pd.DataFrame(rows)


def test_selection_pipeline_runs():
    ba = _synth_backtest_all()
    cost = add_cost_drag_columns(build_cost_sensitivity_table(ba))
    # 비용 그리드 4개 × 후보 2개 = 8행
    assert len(cost) == 8
    assert set(cost["cost_label"]) == set(config.COST_RATE_GRID)
    judge = build_final_judgement(cost)
    assert "final_decision" in judge.columns
    # EW는 benchmark로 분류
    assert (judge.loc[judge["strategy_name"] == "EW", "final_decision"] == "benchmark").all()
    # selection_score 는 0~1 범위
    assert judge["selection_score"].between(0, 1).all()


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
