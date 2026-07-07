"""
Tests for RA input adapters.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline.stage_attribution import run_attribution  # noqa: E402
from pipeline.stage_ra_inputs import (  # noqa: E402
    build_proxy_factor_source_from_candidates,
    load_attribution_inputs_from_candidates,
    load_candidate_return_matrix,
    load_candidate_strategy,
)


def _candidate_csv(tmp_path: Path) -> Path:
    rows = []
    for ym, ret_m, ew_ret, base_ret, lam_ret in [
        ("2020-01", "2020-02", 0.01, 0.012, 0.011),
        ("2020-02", "2020-03", -0.02, -0.018, -0.019),
        ("2020-03", "2020-04", 0.03, 0.034, 0.032),
    ]:
        asset_returns = {"return_069500": 0.02, "return_114260": 0.005, "return_153130": 0.002}
        for duplicate_rule in ["", "equal_weight"]:
            rows.append({
                "strategy_name": "EW",
                "year_month": ym,
                "return_year_month": ret_m,
                "allocation_rule_name": duplicate_rule,
                "strategy_return": ew_ret,
                "turnover": 0.0,
                "weight_069500": 1 / 3,
                "weight_114260": 1 / 3,
                "weight_153130": 1 / 3,
                **asset_returns,
            })
        rows.append({
            "strategy_name": "HSI_final_baseline_overlay",
            "year_month": ym,
            "return_year_month": ret_m,
            "allocation_rule_name": "baseline",
            "strategy_return": base_ret,
            "turnover": 0.20,
            "weight_069500": 0.20,
            "weight_114260": 0.40,
            "weight_153130": 0.40,
            **asset_returns,
        })
        rows.append({
            "strategy_name": "lambda_0.3",
            "year_month": ym,
            "return_year_month": ret_m,
            "allocation_rule_name": "lambda",
            "strategy_return": lam_ret,
            "turnover": 0.10,
            "weight_069500": 0.30,
            "weight_114260": 0.36,
            "weight_153130": 0.34,
            **asset_returns,
        })
    path = tmp_path / "candidate.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_candidate_strategy_normalizes_dates_weights_and_turnover(tmp_path):
    path = _candidate_csv(tmp_path)
    loaded = load_candidate_strategy(path, strategy_name="lambda_0.3")

    assert list(loaded["returns"].columns) == ["Date", "069500", "114260", "153130"]
    assert list(loaded["weights"].columns) == ["Date", "069500_weight", "114260_weight", "153130_weight"]
    assert loaded["returns"]["Date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2020-02-29", "2020-03-31", "2020-04-30"
    ]
    assert np.allclose(loaded["turnover"].to_numpy(), [0.10, 0.10, 0.10])


def test_candidate_return_matrix_dedupes_strategy_rows(tmp_path):
    path = _candidate_csv(tmp_path)
    matrix = load_candidate_return_matrix(path, strategy_names=["EW", "lambda_0.3"])

    assert len(matrix) == 3
    assert list(matrix.columns) == ["Date", "EW", "lambda_0.3"]
    assert np.allclose(matrix["EW"], [0.01, -0.02, 0.03])


def test_attribution_inputs_feed_identity_calculation(tmp_path):
    path = _candidate_csv(tmp_path)
    inputs = load_attribution_inputs_from_candidates(path, lambda_strategy="lambda_0.3")
    result = run_attribution(
        inputs["returns"],
        inputs["baseline_weights"],
        inputs["lambda_weights"],
        inputs["turnover"],
        cost_rate=0.0010,
        save=False,
    )

    monthly = result["monthly"]
    assert len(monthly) == 3
    assert np.allclose(monthly["residual_check"], 0.0)
    assert (monthly["cost_effect"] <= 0).all()


def test_proxy_factor_source_from_candidate_returns(tmp_path):
    path = _candidate_csv(tmp_path)
    factors = build_proxy_factor_source_from_candidates(path)

    assert list(factors.columns) == [
        "Date",
        "market",
        "bond",
        "liquidity",
        "equity_bond_spread",
        "downside_risk",
        "vkospi",
    ]
    assert len(factors) == 3
    assert np.allclose(factors["market"], [0.02, 0.02, 0.02])
    assert np.allclose(factors["equity_bond_spread"], [0.015, 0.015, 0.015])
    assert factors["vkospi"].isna().iloc[:2].all()
