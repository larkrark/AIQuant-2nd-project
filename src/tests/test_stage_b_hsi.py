"""
Stage B (HSI 신호·5상태·baseline 비중) 테스트.

- 분류 규칙 단위 테스트 (컷오프 명시)
- legacy 산출물(main_v2_hsi_state5_table_*.csv)과의 골든 비교
- build_signal_inputs 출력 범위/형식 검증

실행: cd src && python3 -m pytest tests/test_stage_b_hsi.py -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline import config  # noqa: E402
from pipeline.stage_b_hsi import (  # noqa: E402
    allocation_rule_table,
    baseline_target_weights,
    build_signal_inputs,
    classify_hsi_states,
    classify_state5_row,
)

PROJECT_ROOT = SRC_DIR.parent
TABLE_DIR = PROJECT_ROOT / "output" / "tables"

HIGH_CUT = 0.40   # 테스트용 고강도 컷오프
ACC_CUT = 0.50    # 테스트용 accident 방향 컷오프


# ============================================================
# 1. 분류 규칙 단위 테스트
# ============================================================

def _cls(direction, intensity, conflict=False):
    state, _ = classify_state5_row(direction, intensity, HIGH_CUT, ACC_CUT, conflict)
    return state


def test_insufficient_data_on_nan():
    assert _cls(np.nan, 0.5) == "insufficient_data"
    assert _cls(0.5, np.nan) == "insufficient_data"


def test_cross_asset_conflict_takes_priority():
    # 방향·강도가 accident 수준이어도 교차 신호 충돌이 우선
    assert _cls(0.9, 0.9, conflict=True) == "conflict"


def test_conflict_weak_direction_high_intensity():
    assert _cls(0.10, 0.45) == "conflict"   # |0.10| <= 0.15, intensity >= 0.40
    assert _cls(-0.15, 0.40) == "conflict"  # 경계 포함


def test_accident_zone_requires_both_cutoffs():
    assert _cls(0.50, 0.40) == "accident_zone"   # 두 컷오프 동시 충족(경계 포함)
    assert _cls(0.49, 0.90) == "risk_warning"    # 방향 미달 → warning
    assert _cls(0.60, 0.39) == "risk_warning"    # 강도 미달 → warning


def test_risk_warning_and_relief_band():
    assert _cls(0.16, 0.10) == "risk_warning"    # direction > 0.15
    assert _cls(-0.16, 0.10) == "risk_relief"    # direction < -0.15


def test_neutral_watch_inside_band():
    assert _cls(0.15, 0.10) == "neutral_watch"   # 밴드 경계는 중립
    assert _cls(-0.15, 0.10) == "neutral_watch"
    assert _cls(0.0, 0.0) == "neutral_watch"


# ============================================================
# 2. classify_hsi_states 통합 (컷오프 계산·교차 충돌)
# ============================================================

def _signal_inputs():
    n = 20
    direction = [0.0] * 16 + [0.70, 0.70, 0.20, -0.30]
    intensity = list(np.linspace(0.01, 0.16, 16)) + [0.70, 0.70, 0.20, 0.30]
    return pd.DataFrame({
        "Date": pd.date_range("2020-01-31", periods=n, freq="ME"),
        "069500_direction": direction,
        "069500_intensity": intensity,
        "069500_signal": ["watch"] * n,
        "114260_direction": [0.0] * n,
        "114260_intensity": [0.0] * n,
        "114260_signal": ["watch"] * n,
    })


def test_classify_hsi_states_cutoffs_and_states():
    out = classify_hsi_states(_signal_inputs())

    exp_high = out["069500_intensity"].quantile(config.HSI_HIGH_INTENSITY_QUANTILE)
    pos = out.loc[out["069500_direction"] > 0, "069500_direction"]
    exp_acc = pos.quantile(config.HSI_ACCIDENT_DIRECTION_QUANTILE)
    assert np.isclose(out["high_intensity_cutoff"].iloc[0], exp_high)
    assert np.isclose(out["accident_direction_cutoff"].iloc[0], exp_acc)

    # direction=0.70 & intensity=0.70 → 두 컷오프 모두 상회 → accident_zone
    assert out["hsi_state5"].iloc[16] == "accident_zone"
    assert out["hsi_state5"].iloc[18] == "risk_warning"   # 0.20 > 밴드, 컷오프 미달
    assert out["hsi_state5"].iloc[19] == "risk_relief"    # -0.30 < -밴드
    assert out["hsi_state5"].iloc[0] == "neutral_watch"


def test_classify_cross_asset_conflict():
    df = _signal_inputs()
    df.loc[16, "069500_signal"] = "caution"
    df.loc[16, "114260_signal"] = "buy"
    out = classify_hsi_states(df)
    assert out["hsi_state5"].iloc[16] == "conflict"
    assert bool(out["cross_asset_conflict"].iloc[16])


# ============================================================
# 3. 골든 비교: legacy 산출물 재현
# ============================================================

@pytest.mark.parametrize("method", ["rank", "zscore"])
def test_golden_vs_legacy_output(method):
    input_path = TABLE_DIR / f"flex_hsi_monthly_state_{method}.csv"
    golden_path = TABLE_DIR / f"main_v2_hsi_state5_table_{method}.csv"
    if not (input_path.exists() and golden_path.exists()):
        pytest.skip(f"legacy 산출물 없음: {method}")

    signal_inputs = pd.read_csv(input_path, parse_dates=["Date"])
    golden = pd.read_csv(golden_path, parse_dates=["Date"])

    out = classify_hsi_states(signal_inputs)
    merged = out.merge(golden[["Date", "hsi_state5", "high_intensity_cutoff",
                               "accident_direction_cutoff"]],
                       on="Date", suffixes=("", "_golden"))

    assert len(merged) == len(golden)
    assert np.isclose(merged["high_intensity_cutoff"].iloc[0],
                      merged["high_intensity_cutoff_golden"].iloc[0])
    assert np.isclose(merged["accident_direction_cutoff"].iloc[0],
                      merged["accident_direction_cutoff_golden"].iloc[0])

    mismatch = merged[merged["hsi_state5"] != merged["hsi_state5_golden"]]
    assert mismatch.empty, f"{method} 상태 불일치 {len(mismatch)}건:\n{mismatch[['Date', 'hsi_state5', 'hsi_state5_golden']].head()}"

    # 비중 규칙도 legacy와 동일해야 한다
    weights = baseline_target_weights(out)
    gw = golden[["Date", "069500_weight", "114260_weight", "153130_weight"]]
    mw = weights.merge(gw, on="Date", suffixes=("", "_golden"))
    for a in ["069500", "114260", "153130"]:
        assert np.allclose(mw[f"{a}_weight"], mw[f"{a}_weight_golden"]), f"{method} {a} 비중 불일치"


# ============================================================
# 4. baseline 목표비중 규칙
# ============================================================

def test_allocation_rule_sums_to_one():
    rule = allocation_rule_table()
    assert np.allclose(rule["weight_sum"], 1.0)
    assert set(rule["hsi_state5"]) == set(config.STATE5_ALLOCATION)


def test_baseline_target_weights_mapping():
    states = pd.DataFrame({
        "Date": pd.date_range("2020-01-31", periods=3, freq="ME"),
        "hsi_state5": ["accident_zone", "neutral_watch", "risk_warning"],
    })
    w = baseline_target_weights(states)
    assert np.allclose(w["069500_weight"], [0.10, 1 / 3, 0.20])
    assert np.allclose(w["114260_weight"], [0.45, 1 / 3, 0.40])
    total = w["069500_weight"] + w["114260_weight"] + w["153130_weight"]
    assert np.allclose(total, 1.0)


def test_baseline_target_weights_unknown_state_raises():
    states = pd.DataFrame({
        "Date": pd.to_datetime(["2020-01-31"]),
        "hsi_state5": ["unknown_state"],
    })
    with pytest.raises(ValueError):
        baseline_target_weights(states)


# ============================================================
# 5. build_signal_inputs (합성 데이터 스모크)
# ============================================================

def test_build_signal_inputs_ranges():
    rng = np.random.default_rng(0)
    n = 500
    dates = pd.bdate_range("2020-01-01", periods=n)
    prices = pd.DataFrame(
        {t: 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
         for t in ["069500", "114260", "153130"]},
        index=dates,
    )
    prices.index.name = "Date"

    out = build_signal_inputs(prices)

    assert "Date" in out.columns
    for t in ["069500", "114260", "153130"]:
        assert {f"{t}_direction", f"{t}_intensity", f"{t}_signal"} <= set(out.columns)
        d, i = out[f"{t}_direction"], out[f"{t}_intensity"]
        assert d.between(-1, 1).all()
        assert i.between(0, 1).all()
        assert (i >= d.abs() - 1e-12).all()  # intensity >= |direction|
        assert set(out[f"{t}_signal"].unique()) <= {"buy", "watch", "caution"}

    # 월말 리샘플: 월당 1행
    assert out["Date"].dt.to_period("M").is_unique

    # 분류·비중까지 end-to-end로 오류 없이 연결되는지 확인
    states = classify_hsi_states(out)
    weights = baseline_target_weights(states)
    assert len(weights) == len(out)
