"""
공통 모듈 및 백테스트 파이프라인 회귀 테스트.

목적
----
- src/common 의 핵심 함수(정렬/turnover/성과지표)가 기대 동작을 유지하는지 확인.
- 17(main_v2), 19(main_v2b) 백테스트 스크립트의 build 로직이
  합성 데이터에서 정상 동작하고 look-ahead(t→t+1) 정렬을 지키는지 확인.

실행
----
    cd src && python3 -m pytest tests/test_common_pipeline.py -q
또는
    cd src && python3 tests/test_common_pipeline.py
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# src 를 import 경로에 추가 (this file: src/tests/..., parents[1] == src)
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import backtest, config, metrics  # noqa: E402


# ------------------------------------------------------------
# 합성 데이터
# ------------------------------------------------------------

def _make_monthly_returns() -> pd.DataFrame:
    dates = pd.to_datetime(
        ["2020-01-31", "2020-02-29", "2020-03-31", "2020-04-30", "2020-05-31"]
    )
    return pd.DataFrame(
        {
            "Date": dates,
            "069500": [0.01, -0.05, 0.03, 0.02, -0.01],
            "114260": [0.002, 0.003, 0.001, 0.002, 0.0015],
            "153130": [0.001, 0.001, 0.001, 0.001, 0.001],
        }
    )


def _make_state5() -> pd.DataFrame:
    dates = pd.to_datetime(
        ["2020-01-31", "2020-02-29", "2020-03-31", "2020-04-30", "2020-05-31"]
    )
    return pd.DataFrame(
        {
            "Date": dates,
            "hsi_state5": [
                "risk_relief",
                "risk_warning",
                "neutral_watch",
                "accident_zone",
                "conflict",
            ],
            "state_name_kr": ["a", "b", "c", "d", "e"],
            "state_reason": ["", "", "", "", ""],
            "action": ["", "", "", "", ""],
            "069500_weight": [1 / 3, 0.20, 1 / 3, 0.10, 0.25],
            "114260_weight": [1 / 3, 0.40, 1 / 3, 0.45, 0.375],
            "153130_weight": [1 / 3, 0.40, 1 / 3, 0.45, 0.375],
        }
    )


# ------------------------------------------------------------
# common.backtest
# ------------------------------------------------------------

def test_align_applies_state_t_to_return_t_plus_1():
    """Date=t 상태가 Date=t+1 수익률에 정렬되는지(look-ahead 방어) 확인."""
    returns = _make_monthly_returns()
    state5 = _make_state5()

    aligned = backtest.align_state_with_next_returns(state5, returns, method="rank")

    # 마지막 달은 next_return이 없어 제외 → 5행 - 1 = 4행
    assert len(aligned) == 4

    # 첫 신호행(2020-01-31)의 069500_next_return 은 2020-02 수익률(-0.05)
    first = aligned.iloc[0]
    assert first["Date"] == pd.Timestamp("2020-01-31")
    assert first["next_return_date"] == pd.Timestamp("2020-02-29")
    assert np.isclose(first["069500_next_return"], -0.05)


def test_turnover_first_month_zero_and_half_abs_diff():
    weights = pd.DataFrame(
        {
            "method": ["rank"] * 3,
            "strategy": ["S"] * 3,
            "Date": pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"]),
            "069500_weight": [0.5, 0.3, 0.3],
            "114260_weight": [0.25, 0.35, 0.35],
            "153130_weight": [0.25, 0.35, 0.35],
        }
    )
    t = backtest.calculate_turnover(weights).sort_values("Date").reset_index(drop=True)

    assert t.loc[0, "turnover"] == 0.0  # 첫 달은 0
    # 2월: 0.5*(|0.3-0.5|+|0.35-0.25|+|0.35-0.25|) = 0.5*0.4 = 0.2
    assert np.isclose(t.loc[1, "turnover"], 0.2)
    # 3월: 비중 변화 없음 → 0
    assert np.isclose(t.loc[2, "turnover"], 0.0)


def test_turnover_summary_columns():
    weights = pd.DataFrame(
        {
            "method": ["rank", "rank"],
            "strategy": ["S", "S"],
            "Date": pd.to_datetime(["2020-01-31", "2020-02-29"]),
            "069500_weight": [0.5, 0.3],
            "114260_weight": [0.25, 0.35],
            "153130_weight": [0.25, 0.35],
        }
    )
    s = backtest.make_turnover_summary(backtest.calculate_turnover(weights))
    assert {"method", "strategy", "months", "avg_turnover", "max_turnover", "total_turnover"} <= set(s.columns)


# ------------------------------------------------------------
# common.metrics
# ------------------------------------------------------------

def test_metrics_known_values():
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"]),
            "monthly_return": [0.10, -0.05, 0.02],
        }
    )
    m = metrics.calculate_performance_metrics(df)

    # 정본 지표는 sortino/std_monthly_return 을 포함한다(20의 드리프트 수정 확인)
    assert "sortino" in m.index
    assert "std_monthly_return" in m.index

    total = (1.10 * 0.95 * 1.02) - 1
    assert np.isclose(m["total_return"], total)
    assert m["months"] == 3
    # 하락월이 1개뿐이면 표본표준편차(ddof=1)는 계산 불가 → sortino NaN
    assert np.isnan(m["sortino"])


def test_metrics_empty_raises():
    df = pd.DataFrame({"Date": pd.to_datetime([]), "monthly_return": []})
    try:
        metrics.calculate_performance_metrics(df)
        raised = False
    except ValueError:
        raised = True
    assert raised


# ------------------------------------------------------------
# 17 / 19 build 로직 (합성 데이터)
# ------------------------------------------------------------

def _load_script(module_alias: str, filename: str):
    path = SRC_DIR / filename
    spec = importlib.util.spec_from_file_location(module_alias, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_v2_build_backtest_runs_and_is_consistent():
    mod = _load_script("mod17", "17_main_v2_backtest_hsi_state5_overlay.py")
    returns = _make_monthly_returns()
    state5 = _make_state5()

    aligned = backtest.align_state_with_next_returns(state5, returns, method="rank")
    bt, w = mod.build_backtest_for_method(aligned, method="rank")

    # EW와 overlay 두 전략이 있어야 한다
    assert set(bt["strategy"]) == {"EW", "HSI_state5_overlay"}
    # 각 전략 비중 합 == 1
    wsum = w[["069500_weight", "114260_weight", "153130_weight"]].sum(axis=1)
    assert np.allclose(wsum, 1.0)
    # 누적수익률/낙폭 컬럼 생성 확인
    assert {"cumulative_return", "drawdown"} <= set(bt.columns)


def test_v2b_relaxed_treats_conflict_as_equal_weight():
    mod = _load_script("mod19", "19_main_v2b_backtest_state5_overlay_relaxed.py")
    rule = mod.make_v2b_allocation_rule_table()

    conflict = rule[rule["hsi_state5"] == "conflict"].iloc[0]
    # v2b 규칙: conflict 는 방어하지 않고 동일비중(1/3)
    assert np.isclose(conflict["069500_weight"], 1 / 3)
    assert np.isclose(conflict["weight_sum"], 1.0)

    # apply → align → build 파이프라인이 합성 데이터에서 동작
    state5 = _make_state5()
    applied = mod.apply_v2b_weights(state5, method="rank")
    aligned = backtest.align_state_with_next_returns(applied, _make_monthly_returns(), method="rank")
    bt, w = mod.build_backtest_for_method(aligned, method="rank")
    assert set(bt["strategy"]) == {"EW", "HSI_state5_overlay_v2b"}


def test_config_constants():
    assert config.ASSETS == ["069500", "114260", "153130"]
    assert config.WEIGHT_COLS == {a: f"{a}_weight" for a in config.ASSETS}
    assert config.INITIAL_CAPITAL == 1.0


if __name__ == "__main__":
    # pytest 없이도 실행 가능
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
