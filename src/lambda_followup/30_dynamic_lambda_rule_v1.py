# -*- coding: utf-8 -*-
"""
30_dynamic_lambda_rule_v1.py — E30 조건부(동적) λ 규칙 v1

규칙 (v2 §3.7, threshold는 IS에서만 결정):
  고위험   : annualized_volatility_z > 1  또는 rolling_drawdown < -10% 또는 macro_risk_score ≥ 2 → λ=0.1
  안정완화 : risk_relief 3개월 이상 지속 & volatility_z < 0 & momentum_z > 0        → λ=0.5
  그 외    : λ=0.3

상태변수 계산 규약 (게이트 ⑦ 누수 audit):
- 모든 rolling 계산은 t월 말까지의 정보만 사용 (전구간 분위수·z 금지)
- annualized_annualized_volatility_z: 위험자산(069500) 12개월 rolling 연환산 변동성(std×√12)을
  36개월 rolling 평균·표준편차로 z-score 화
- rolling_drawdown: 069500 누적지수의 12개월 rolling 고점 대비 낙폭
- momentum_z: 069500 12-1 모멘텀의 36개월 rolling z-score
- macro_risk_score: data/processed/factor_inputs_monthly.csv 에 macro_risk_score
  열이 있으면 사용, 없으면 해당 조건 비활성(0 처리)하고 그 사실을 기록

출력:
  output/tables/main_final_dynamic_lambda_comparison.csv
  output/tables/flex_dynamic_lambda_path.csv
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
import common as X

R = C.E30_RULE_V1


def rolling_z(s: pd.Series, window: int) -> pd.Series:
    mu = s.rolling(window, min_periods=window // 2).mean()
    sd = s.rolling(window, min_periods=window // 2).std(ddof=1)
    return (s - mu) / sd


def build_state_variables(returns: pd.DataFrame, target_w: pd.DataFrame) -> pd.DataFrame:
    """신호월 index 의 조건부 λ 판단용 상태변수 (전부 과거 정보만 사용)."""
    r = returns[C.RISK_TICKER]
    idx_series = (1 + r).cumprod()

    ann_vol = r.rolling(R["vol_window"]).std(ddof=1) * np.sqrt(12)
    annualized_volatility_z = rolling_z(ann_vol, R["z_window"])

    rolling_dd = idx_series / idx_series.rolling(R["drawdown_window"], min_periods=1).max() - 1

    mom = idx_series.pct_change(R["momentum_lookback"]).shift(R["momentum_skip"])
    momentum_z = rolling_z(mom, R["z_window"])

    sv = pd.DataFrame({
        "annualized_volatility_z": annualized_volatility_z,
        "rolling_drawdown": rolling_dd,
        "momentum_z": momentum_z,
    })

    # macro_risk_score (선택 입력)
    sv["macro_risk_score"] = 0.0
    sv["macro_available"] = False
    if C.FACTORS_FILE.exists():
        f = pd.read_csv(C.FACTORS_FILE, index_col=0, parse_dates=True).sort_index()
        if "macro_risk_score" in f.columns:
            sv["macro_risk_score"] = f["macro_risk_score"].reindex(sv.index).fillna(0.0)
            sv["macro_available"] = True

    # risk_relief 지속 개월 수 (hsi_state 열이 있을 때)
    if "hsi_state" in target_w.columns:
        st = target_w["hsi_state"].reindex(sv.index)
        persist, run = [], 0
        for s in st:
            run = run + 1 if s == "risk_relief" else 0
            persist.append(run)
        sv["relief_persist"] = persist
    else:
        sv["relief_persist"] = 0
        print("※ hsi_state 열이 없어 '안정 완화' 조건의 상태 지속 판정이 비활성입니다.")

    return sv


def assign_lambda(sv: pd.DataFrame) -> pd.Series:
    high_risk = (
        (sv["annualized_volatility_z"] > R["volatility_z_high"])
        | (sv["rolling_drawdown"] < R["drawdown_low"])
        | (sv["macro_available"] & (sv["macro_risk_score"] >= R["macro_risk_high"]))
    )
    stable_relief = (
        (sv["relief_persist"] >= R["relief_persist_months"])
        & (sv["annualized_volatility_z"] < R["volatility_z_calm"])
        & (sv["momentum_z"] > R["momentum_z_positive"])
    )
    lam = pd.Series(R["lambda_base"], index=sv.index, name="lambda_t")
    lam[stable_relief] = R["lambda_stable_relief"]
    lam[high_risk] = R["lambda_high_risk"]          # 고위험이 안정완화에 우선
    label = pd.Series("base", index=sv.index)
    label[stable_relief] = "stable_relief"
    label[high_risk] = "high_risk"
    return lam, label


def main() -> None:
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()

    sv = build_state_variables(returns, target_w)
    lam_t, cond_label = assign_lambda(sv)

    # 초기 rolling 미충족 구간은 기본 λ
    lam_t = lam_t.fillna(R["lambda_base"])

    bt_dyn = X.run_lambda_backtest(returns, target_w,
                                   lambda_up=np.nan, lambda_down=np.nan,
                                   lambda_series=lam_t)

    # 비교군: 대칭 0.1 / 0.3
    rows = [X.perf_metrics(bt_dyn["strategy_return_gross"], bt_dyn["turnover"], "dynamic_v1")]
    for lam in (0.1, 0.3):
        bt = X.run_lambda_backtest(returns, target_w, lambda_up=lam, lambda_down=lam)
        rows.append(X.perf_metrics(bt["strategy_return_gross"], bt["turnover"], f"lambda_{lam}"))
    comp = pd.DataFrame(rows)
    for i, bt in enumerate([bt_dyn]):
        for bps in C.COST_BPS_GRID:
            net = bt["strategy_return_gross"] - bt["turnover"] * (bps / 10000.0)
            comp.loc[0, f"cagr_net_{bps}bp"] = ((1 + net).prod() ** (12 / len(net)) - 1) * 100

    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    comp.to_csv(C.TABLE_DIR / f"{C.FINAL_PREFIX}dynamic_lambda_comparison.csv",
                index=False, encoding="utf-8-sig")
    path_df = pd.concat([sv, lam_t, cond_label.rename("condition")], axis=1)
    path_df.to_csv(C.TABLE_DIR / f"{C.INTERIM_PREFIX}dynamic_lambda_path.csv",
                   encoding="utf-8-sig")

    print("[완료] E30 — 규칙 v1")
    print("조건 분포:", cond_label.value_counts().to_dict())
    if not sv["macro_available"].any():
        print("※ macro_risk_score 미확보 → 고위험 조건에서 macro 항 비활성 (기록됨)")
    print(comp[["strategy", "cagr_pct", "mdd_pct", "calmar",
                "avg_turnover_pct", "max_turnover_pct"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
