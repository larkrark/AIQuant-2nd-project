"""
Input adapters for RA analysis stages.

The reporting scripts already produce candidate backtest CSV files, but their
column names are report-oriented (for example weight_069500 and return_069500).
This module converts those files into the normalized inputs expected by
stage_factor and stage_attribution.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from common.config import ASSETS
from common.io_utils import read_csv_with_date, save_table
from common.paths import HSI_CANDIDATE_DIR, PROCESSED_DIR

DEFAULT_CANDIDATE_TIMESERIES = HSI_CANDIDATE_DIR / "23_main_final_report_candidate_timeseries_subset.csv"
DEFAULT_FACTOR_SOURCE = PROCESSED_DIR / "factors" / "monthly_factors.csv"


def _month_end_from_year_month(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values.astype(str) + "-01") + pd.offsets.MonthEnd(0)


def _candidate_date(df: pd.DataFrame) -> pd.Series:
    if "Date" in df.columns:
        return pd.to_datetime(df["Date"])
    if "return_year_month" in df.columns:
        return _month_end_from_year_month(df["return_year_month"])
    if "year_month" in df.columns:
        return _month_end_from_year_month(df["year_month"])
    raise ValueError("candidate timeseries needs Date, return_year_month, or year_month.")


def _dedupe_strategy_rows(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Date"] = _candidate_date(out)
    if "allocation_rule_name" in out.columns:
        out["_has_rule"] = out["allocation_rule_name"].fillna("").astype(str).ne("")
        out = out.sort_values(["Date", "_has_rule"], ascending=[True, False])
        out = out.drop(columns="_has_rule")
    else:
        out = out.sort_values("Date")
    return out.drop_duplicates(subset=["Date"], keep="first").reset_index(drop=True)


def load_candidate_strategy(
    path: Path | str = DEFAULT_CANDIDATE_TIMESERIES,
    *,
    strategy_name: str,
    assets: list[str] | None = None,
) -> dict:
    """
    Load one strategy from the final candidate timeseries CSV.

    Returns a dict with normalized DataFrames/Series:
    - returns: Date + asset return columns (069500, 114260, ...)
    - weights: Date + weight columns (069500_weight, ...)
    - strategy_returns: Date + strategy_return
    - turnover: monthly turnover Series aligned to Date
    """
    assets = assets or ASSETS
    df = read_csv_with_date(Path(path))
    if "strategy_name" not in df.columns:
        raise ValueError(f"strategy_name column is missing: {path}")

    sub = df[df["strategy_name"] == strategy_name].copy()
    if sub.empty:
        choices = ", ".join(map(str, sorted(df["strategy_name"].dropna().unique())))
        raise ValueError(f"strategy not found: {strategy_name}. Available: {choices}")

    sub = _dedupe_strategy_rows(sub)
    missing_returns = [f"return_{a}" for a in assets if f"return_{a}" not in sub.columns]
    missing_weights = [f"weight_{a}" for a in assets if f"weight_{a}" not in sub.columns]
    missing = missing_returns + missing_weights
    if missing:
        raise ValueError(f"required candidate columns are missing: {missing}")

    returns = sub[["Date"]].copy()
    for asset in assets:
        returns[asset] = pd.to_numeric(sub[f"return_{asset}"], errors="coerce")

    weights = sub[["Date"]].copy()
    for asset in assets:
        weights[f"{asset}_weight"] = pd.to_numeric(sub[f"weight_{asset}"], errors="coerce")

    strategy_returns = sub[["Date"]].copy()
    strategy_returns["strategy_return"] = pd.to_numeric(sub["strategy_return"], errors="coerce")

    turnover = pd.to_numeric(sub.get("turnover", pd.Series(0.0, index=sub.index)), errors="coerce").fillna(0.0)
    turnover = pd.Series(turnover.to_numpy(), index=sub["Date"], name="turnover")

    return {
        "returns": returns,
        "weights": weights,
        "strategy_returns": strategy_returns,
        "turnover": turnover,
    }


def load_candidate_return_matrix(
    path: Path | str = DEFAULT_CANDIDATE_TIMESERIES,
    *,
    strategy_names: list[str] | None = None,
) -> pd.DataFrame:
    """Load candidate strategy returns as Date + one column per strategy."""
    df = read_csv_with_date(Path(path))
    if "strategy_name" not in df.columns or "strategy_return" not in df.columns:
        raise ValueError(f"candidate file needs strategy_name and strategy_return: {path}")

    names = strategy_names or sorted(df["strategy_name"].dropna().unique())
    frames = []
    for name in names:
        sub = df[df["strategy_name"] == name].copy()
        if sub.empty:
            continue
        sub = _dedupe_strategy_rows(sub)
        frames.append(sub[["Date", "strategy_return"]].rename(columns={"strategy_return": name}))

    if not frames:
        raise ValueError("no strategy return series could be loaded.")

    out = frames[0]
    for frame in frames[1:]:
        out = out.merge(frame, on="Date", how="outer")
    return out.sort_values("Date").reset_index(drop=True)


def load_attribution_inputs_from_candidates(
    path: Path | str = DEFAULT_CANDIDATE_TIMESERIES,
    *,
    baseline_strategy: str = "HSI_final_baseline_overlay",
    lambda_strategy: str = "lambda_0.3",
    assets: list[str] | None = None,
) -> dict:
    """Load normalized inputs for stage_attribution from candidate CSV output."""
    assets = assets or ASSETS
    baseline = load_candidate_strategy(path, strategy_name=baseline_strategy, assets=assets)
    lam = load_candidate_strategy(path, strategy_name=lambda_strategy, assets=assets)

    returns = lam["returns"]
    baseline_weights = baseline["weights"]
    lambda_weights = lam["weights"]
    turnover_df = pd.DataFrame({"Date": lam["turnover"].index, "turnover": lam["turnover"].to_numpy()})

    common_dates = set(returns["Date"]).intersection(baseline_weights["Date"]).intersection(lambda_weights["Date"])
    returns = returns[returns["Date"].isin(common_dates)].sort_values("Date").reset_index(drop=True)
    baseline_weights = baseline_weights[baseline_weights["Date"].isin(common_dates)].sort_values("Date").reset_index(drop=True)
    lambda_weights = lambda_weights[lambda_weights["Date"].isin(common_dates)].sort_values("Date").reset_index(drop=True)
    turnover = (
        turnover_df[turnover_df["Date"].isin(common_dates)]
        .sort_values("Date")["turnover"]
        .reset_index(drop=True)
    )

    return {
        "returns": returns,
        "baseline_weights": baseline_weights,
        "lambda_weights": lambda_weights,
        "turnover": turnover,
    }


def build_proxy_factor_source_from_candidates(
    path: Path | str = DEFAULT_CANDIDATE_TIMESERIES,
    *,
    source_strategy: str = "EW",
) -> pd.DataFrame:
    """
    Build a minimal monthly factor source from ETF candidate returns.

    This is a fallback execution source until external ECOS/KRX/macro factors are
    ingested. The columns are intentionally transparent proxies:
    - market: KODEX 200 monthly return
    - bond: KODEX 3Y government bond monthly return
    - liquidity: short-term bond ETF monthly return
    - equity_bond_spread: market minus bond return
    - downside_risk: negative part of market return
    - vkospi: 6-month realized market volatility proxy
    """
    loaded = load_candidate_strategy(path, strategy_name=source_strategy)
    returns = loaded["returns"].copy()
    market = pd.to_numeric(returns["069500"], errors="coerce")
    bond = pd.to_numeric(returns["114260"], errors="coerce")
    liquidity = pd.to_numeric(returns["153130"], errors="coerce")

    out = returns[["Date"]].copy()
    out["market"] = market
    out["bond"] = bond
    out["liquidity"] = liquidity
    out["equity_bond_spread"] = market - bond
    out["downside_risk"] = np.minimum(market, 0.0)
    out["vkospi"] = market.rolling(6, min_periods=3).std(ddof=1) * np.sqrt(12)
    return out


def save_proxy_factor_source(
    path: Path | str = DEFAULT_FACTOR_SOURCE,
    *,
    candidate_path: Path | str = DEFAULT_CANDIDATE_TIMESERIES,
    source_strategy: str = "EW",
) -> pd.DataFrame:
    """Create data/processed/factors/monthly_factors.csv from ETF return proxies."""
    factors = build_proxy_factor_source_from_candidates(candidate_path, source_strategy=source_strategy)
    save_table(factors, Path(path))
    return factors
