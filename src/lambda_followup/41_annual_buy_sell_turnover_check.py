# -*- coding: utf-8 -*-
"""
41_annual_buy_sell_turnover_check.py

목적
----
연단위 매수/매도 기준 Turnover를 분리 산출한다.

기존 보고서의 Turnover:
    one-way turnover = Σ|Δw| / 2

추가 산출:
    buy_turnover  = Σ max(Δw, 0)
    sell_turnover = Σ max(-Δw, 0)
    double_sided  = buy_turnover + sell_turnover = Σ|Δw|

비중 합계가 1로 유지되면 buy_turnover와 sell_turnover는 거의 같고,
one-way turnover와도 거의 같다.
"""

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
import common as X

dyn = importlib.import_module("30_dynamic_lambda_rule_v1")
dyn_macro = importlib.import_module("30_dynamic_lambda_rule_v1_macro")


def build_backtests() -> dict:
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()

    bts = {}

    bts["lambda_0.1"] = X.run_lambda_backtest(returns, target_w, 0.1, 0.1)
    bts["lambda_0.3"] = X.run_lambda_backtest(returns, target_w, 0.3, 0.3)
    bts["asym_up0.1_down0.3"] = X.run_lambda_backtest(returns, target_w, 0.1, 0.3)

    sv = dyn.build_state_variables(returns, target_w)
    lam_dyn, _ = dyn.assign_lambda(sv)
    lam_dyn = lam_dyn.fillna(C.E30_RULE_V1["lambda_base"])
    bts["dynamic_v1"] = X.run_lambda_backtest(
        returns,
        target_w,
        np.nan,
        np.nan,
        lambda_series=lam_dyn,
    )

    sv_macro = dyn_macro.build_state_variables_macro(returns, target_w)
    lam_macro, _, _ = dyn_macro.assign_lambda_macro(sv_macro)
    lam_macro = lam_macro.fillna(C.E30_RULE_V1["lambda_base"])
    bts["dynamic_v1_macro"] = X.run_lambda_backtest(
        returns,
        target_w,
        np.nan,
        np.nan,
        lambda_series=lam_macro,
    )

    return bts


def annual_buy_sell_turnover(bt: pd.DataFrame, strategy: str) -> pd.DataFrame:
    weight_cols = [f"w_{t}" for t in C.TICKERS]
    missing = [c for c in weight_cols if c not in bt.columns]
    if missing:
        raise ValueError(f"{strategy}: weight columns missing: {missing}")

    w = bt[weight_cols].copy()
    w = w.sort_index()

    # 리밸런싱 전후 비중 변화
    # 첫 행은 이전 비중이 없으므로 0으로 처리
    dw = w.diff().fillna(0.0)

    buy = dw.clip(lower=0).sum(axis=1)
    sell = (-dw.clip(upper=0)).sum(axis=1)

    calc_oneway = (dw.abs().sum(axis=1) / 2)
    double_sided = dw.abs().sum(axis=1)

    detail = pd.DataFrame({
        "date": w.index,
        "year": w.index.year,
        "strategy": strategy,
        "buy_turnover": buy,
        "sell_turnover": sell,
        "oneway_turnover_from_weights": calc_oneway,
        "double_sided_turnover": double_sided,
    })

    if "turnover" in bt.columns:
        detail["turnover_from_backtest"] = bt["turnover"].reindex(w.index).values
        detail["turnover_diff"] = (
            detail["oneway_turnover_from_weights"]
            - detail["turnover_from_backtest"]
        )

    annual = detail.groupby(["year", "strategy"], as_index=False).agg(
        annual_buy_turnover_pct=("buy_turnover", lambda x: x.sum() * 100),
        annual_sell_turnover_pct=("sell_turnover", lambda x: x.sum() * 100),
        annual_oneway_turnover_pct=("oneway_turnover_from_weights", lambda x: x.sum() * 100),
        annual_double_sided_turnover_pct=("double_sided_turnover", lambda x: x.sum() * 100),
        max_monthly_oneway_turnover_pct=("oneway_turnover_from_weights", lambda x: x.max() * 100),
    )

    if "turnover_from_backtest" in detail.columns:
        annual_check = detail.groupby(["year", "strategy"], as_index=False).agg(
            annual_backtest_turnover_pct=("turnover_from_backtest", lambda x: x.sum() * 100),
            max_abs_turnover_diff=("turnover_diff", lambda x: x.abs().max()),
        )
        annual = annual.merge(annual_check, on=["year", "strategy"], how="left")

    return annual, detail


def main() -> None:
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)

    bts = build_backtests()

    annual_list = []
    detail_list = []

    for strategy, bt in bts.items():
        annual, detail = annual_buy_sell_turnover(bt, strategy)
        annual_list.append(annual)
        detail_list.append(detail)

    annual_df = pd.concat(annual_list, ignore_index=True)
    detail_df = pd.concat(detail_list, ignore_index=True)

    annual_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}annual_buy_sell_turnover.csv"
    detail_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}monthly_buy_sell_turnover_detail.csv"

    annual_df.to_csv(annual_path, index=False, encoding="utf-8-sig")
    detail_df.to_csv(detail_path, index=False, encoding="utf-8-sig")

    summary = (
        annual_df
        .groupby("strategy", as_index=False)
        .agg(
            avg_annual_buy_turnover_pct=("annual_buy_turnover_pct", "mean"),
            avg_annual_sell_turnover_pct=("annual_sell_turnover_pct", "mean"),
            avg_annual_oneway_turnover_pct=("annual_oneway_turnover_pct", "mean"),
            max_annual_oneway_turnover_pct=("annual_oneway_turnover_pct", "max"),
            max_annual_double_sided_turnover_pct=("annual_double_sided_turnover_pct", "max"),
        )
        .sort_values("avg_annual_oneway_turnover_pct")
    )

    summary_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}annual_buy_sell_turnover_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print("[완료] 41_annual_buy_sell_turnover_check")
    print(f"- annual: {annual_path}")
    print(f"- detail: {detail_path}")
    print(f"- summary: {summary_path}")
    print()
    print(summary.round(3).to_string(index=False))


if __name__ == "__main__":
    main()