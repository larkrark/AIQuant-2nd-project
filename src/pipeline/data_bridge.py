"""
Self-test 데이터 브릿지 + 하네스.

조원 최종 데이터가 오기 전에, in-repo 자료로 stage_factor/stage_attribution +
규칙 기반 동적 lambda(dynamic_v1)를 실제로 돌려보기 위한 어댑터.
"조원 canonical 파일 있으면 그걸, 없으면 legacy/파생 surrogate" 우선순위.

surrogate: 자산수익률=monthly_factors(market/bond/cash_ret), baseline·HSI상태=main_v2 state5 rank,
조건변수=realized_vol/mom_12m expanding z-score + 069500 rolling drawdown
(macro_risk_score는 외부 금리·환율 미보유 -> 0, 즉 dynamic_v1(비-macro) 기준).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.backtest import align_weights_with_next_returns, calculate_turnover, strategy_monthly_returns
from common.config import ASSETS
from common.io_utils import save_table
from common.metrics import calculate_performance_metrics
from common.paths import PROCESSED_DIR, TABLE_DIR
from pipeline.config import ADOPTION, ASYM_CANDIDATES, DYNAMIC_LAMBDA_RULE, OOS_START
from pipeline.stage_attribution import run_attribution
from pipeline.stage_d_lambda import apply_asymmetric_lambda, apply_lambda_partial_adjustment, rule_based_dynamic_lambda
from pipeline.stage_selection import adoption_decision
from pipeline.validation import walk_forward_metrics
from pipeline.stage_factor import analyze_strategies, build_factor_matrix, expanding_zscore, save_outputs, screen_factors

WCOLS = [f"{a}_weight" for a in ASSETS]
FACTORS_PATH = PROCESSED_DIR / "factors" / "monthly_factors.csv"
CANON_BASELINE = PROCESSED_DIR / "main_final_baseline_rebalance_weights.csv"
SURR_BASELINE = TABLE_DIR / "main_v2_hsi_state5_table_rank.csv"
FACTOR_COLS = ["market_ret", "bond_ret", "realized_vol", "stock_bond_corr_6m"]
COST_RATE = 0.0010
LABEL_LAM = {"default": 0.3, "high_risk": 0.1, "easing": 0.5}


def _to_month_end(s):
    return pd.to_datetime(s) + pd.offsets.MonthEnd(0)


def load_asset_returns() -> pd.DataFrame:
    f = pd.read_csv(FACTORS_PATH)
    f["Date"] = _to_month_end(f["Date"])
    out = pd.DataFrame({"Date": f["Date"], "069500": f["market_ret"], "114260": f["bond_ret"], "153130": f["cash_ret"]})
    return out.dropna().sort_values("Date").reset_index(drop=True)


def load_baseline_weights():
    if CANON_BASELINE.exists():
        df, src = pd.read_csv(CANON_BASELINE), "canonical(조원)"
    else:
        df, src = pd.read_csv(SURR_BASELINE), "surrogate(main_v2 state5 rank)"
    df["Date"] = _to_month_end(df["Date"])
    df = df[["Date"] + WCOLS].dropna().sort_values("Date").reset_index(drop=True)
    s = df[WCOLS].sum(axis=1).replace(0, np.nan)
    for c in WCOLS:
        df[c] = df[c] / s
    return df, src


def load_hsi_states() -> pd.DataFrame:
    df = pd.read_csv(SURR_BASELINE)
    df["Date"] = _to_month_end(df["Date"])
    out = df[["Date"]].copy()
    out["hsi_state"] = df["hsi_state5"].astype(str) if "hsi_state5" in df.columns else ""
    return out.sort_values("Date").reset_index(drop=True)


def build_condition_variables(baseline_w, asset_ret, hsi) -> pd.DataFrame:
    f = pd.read_csv(FACTORS_PATH)
    f["Date"] = _to_month_end(f["Date"])
    d = baseline_w[["Date"]].sort_values("Date").reset_index(drop=True)
    d = d.merge(f[["Date", "realized_vol", "mom_12m", "market_ret"]], on="Date", how="left")
    d["volatility_z"] = expanding_zscore(d["realized_vol"])
    d["momentum_z"] = expanding_zscore(d["mom_12m"])
    cum = (1 + d["market_ret"].fillna(0)).cumprod()
    d["rolling_drawdown"] = cum / cum.cummax() - 1
    d["macro_risk_score"] = 0
    d = d.merge(hsi, on="Date", how="left")
    d["hsi_state"] = d["hsi_state"].fillna("")
    return d


def _candidate_series(weights, asset_ret) -> pd.DataFrame:
    w = weights.sort_values("Date").reset_index(drop=True)
    aligned = align_weights_with_next_returns(w, asset_ret)
    ret = strategy_monthly_returns(aligned)
    tw = w[["Date"]].copy()
    tw["turnover"] = calculate_turnover(w).values
    m = aligned.merge(tw, on="Date", how="left")
    return pd.DataFrame({"Date": aligned["next_return_date"].values,
                         "ret": np.asarray(ret), "turnover": m["turnover"].fillna(0).values})


def _metrics_row(name, cs) -> dict:
    net = pd.Series(cs["ret"].values - cs["turnover"].values * COST_RATE)
    g = calculate_performance_metrics(pd.Series(cs["ret"].values))
    n = calculate_performance_metrics(net)
    return {"strategy": name, "CAGR_pct": g["cagr"] * 100, "MDD_pct": g["mdd"] * 100,
            "Sharpe": g["sharpe"], "Calmar": g["calmar"], "avg_turnover_pct": cs["turnover"].mean() * 100,
            "CAGR_net10bp_pct": n["cagr"] * 100, "Calmar_net10bp": n["calmar"]}


def build_attribution_inputs(baseline_w, asset_ret, lam):
    aligned = align_weights_with_next_returns(baseline_w, asset_ret)
    lam_w = apply_lambda_partial_adjustment(baseline_w, lam)
    lam_ren = lam_w.rename(columns={f"{a}_weight": f"{a}_lamw" for a in ASSETS}).assign(_turn=calculate_turnover(lam_w).values)
    m = aligned.merge(lam_ren[["Date"] + [f"{a}_lamw" for a in ASSETS] + ["_turn"]], on="Date", how="left")
    rm = m["next_return_date"].values
    ret_df, base_wdf, lam_wdf = (pd.DataFrame({"Date": rm}) for _ in range(3))
    for a in ASSETS:
        ret_df[a] = m[f"{a}_next_return"].values
        base_wdf[f"{a}_weight"] = m[f"{a}_weight"].values
        lam_wdf[f"{a}_weight"] = m[f"{a}_lamw"].values
    return ret_df, base_wdf, lam_wdf, pd.Series(m["_turn"].fillna(0).values)



def oos_adoption_table(series, asset_ret, *, oos_start=OOS_START, cost_rate=COST_RATE, tail_q=None):
    """각 후보의 OOS 10bp net 지표(Calmar_net·MDD·tail-month 평균·Turnover)."""
    tail_q = ADOPTION["tail_quantile"] if tail_q is None else tail_q
    risk = asset_ret[["Date", "069500"]].rename(columns={"069500": "risk_ret"})
    rows = []
    for name, cs in series.items():
        d = cs.merge(risk, on="Date", how="left")
        d = d[d["Date"] >= pd.Timestamp(oos_start)].reset_index(drop=True)
        if len(d) == 0:
            continue
        net = d["ret"].values - d["turnover"].values * cost_rate
        m = calculate_performance_metrics(pd.Series(net))
        tail_thr = d["risk_ret"].quantile(tail_q)
        tail_mask = (d["risk_ret"] <= tail_thr).values
        tail_avg = float(np.mean(net[tail_mask])) if tail_mask.any() else np.nan
        rows.append({"strategy": name, "Calmar_net": m["calmar"], "MDD_pct": m["mdd"] * 100,
                     "tail_month_avg_pct": tail_avg * 100, "avg_turnover_pct": d["turnover"].mean() * 100})
    return pd.DataFrame(rows)


def run_selftest() -> dict:
    print("=" * 78)
    print("SELF-TEST: attribution + factor loading + dynamic_v1(규칙형 동적 λ)")
    print("=" * 78)
    asset_ret = load_asset_returns()
    baseline_w, src = load_baseline_weights()
    hsi = load_hsi_states()
    common = set(asset_ret["Date"]) & set(baseline_w["Date"])
    asset_ret = asset_ret[asset_ret["Date"].isin(common)].sort_values("Date").reset_index(drop=True)
    baseline_w = baseline_w[baseline_w["Date"].isin(common)].sort_values("Date").reset_index(drop=True)
    print(f"[입력] 자산 {asset_ret.shape}, baseline {baseline_w.shape} (소스: {src}), 공통 {len(common)}개월")
    print(f"[검증] baseline 비중합 오차 {abs(baseline_w[WCOLS].sum(axis=1) - 1).max():.2e}")
    lam1 = apply_lambda_partial_adjustment(baseline_w, 1.0)
    print(f"[검증] λ=1.0 == baseline: {np.allclose(lam1[WCOLS].to_numpy(), baseline_w[WCOLS].to_numpy())}")

    cond = build_condition_variables(baseline_w, asset_ret, hsi)
    lam_t, labels = rule_based_dynamic_lambda(cond, **DYNAMIC_LAMBDA_RULE)
    dyn_w = apply_lambda_partial_adjustment(baseline_w, lam_t)
    path = pd.DataFrame({"Date": baseline_w["Date"].values, "lambda_t": lam_t, "label": labels})
    save_table(path, TABLE_DIR / "dynamic_lambda_path.csv")
    dist = pd.Series(labels).value_counts()
    print("\n[dynamic_v1] λ_t 규칙 분포: " + ", ".join(f"{k}(λ={LABEL_LAM[k]})={v}개월" for k, v in dist.items()))

    ew = baseline_w[["Date"]].copy()
    for a in ASSETS:
        ew[f"{a}_weight"] = 1 / len(ASSETS)
    cands = {"EW": ew, "HSI_baseline": baseline_w,
             "lambda_0.1": apply_lambda_partial_adjustment(baseline_w, 0.1),
             "lambda_0.3": apply_lambda_partial_adjustment(baseline_w, 0.3),
             "dynamic_v1": dyn_w}
    for _u, _d in ASYM_CANDIDATES:
        cands[f"asym_up{_u}_down{_d}"] = apply_asymmetric_lambda(baseline_w, _u, _d)
    series = {n: _candidate_series(w, asset_ret) for n, w in cands.items()}
    comp = pd.DataFrame([_metrics_row(n, cs) for n, cs in series.items()])
    save_table(comp, TABLE_DIR / "selftest_strategy_comparison.csv")
    print("\n[전략 성과 비교 (net10bp = 비용차감)]")
    print(comp.round(3).to_string(index=False))

    ret_df, base_wdf, lam_wdf, turnover = build_attribution_inputs(baseline_w, asset_ret, 0.3)
    attr = run_attribution(ret_df, base_wdf, lam_wdf, turnover, cost_rate=COST_RATE, save=True)
    print(f"\n[Attribution λ=0.3] residual 최대 {attr['monthly']['residual_check'].abs().max():.2e}")

    fac = pd.read_csv(FACTORS_PATH)
    fac["Date"] = _to_month_end(fac["Date"])
    fm = build_factor_matrix(fac, factor_cols=FACTOR_COLS)
    panel = None
    for n, cs in series.items():
        d = cs[["Date"]].copy()
        d[n] = cs["ret"].values
        panel = d if panel is None else panel.merge(d, on="Date", how="outer")
    merged = panel.merge(fm, on="Date", how="inner").dropna().reset_index(drop=True)
    strat_cols = [c for c in cands if c != "EW"]
    summary, ts = analyze_strategies(merged[["Date"] + list(cands)], merged["EW"],
                                     merged[["Date"] + FACTOR_COLS], strategy_cols=strat_cols, factor_cols=FACTOR_COLS)
    save_outputs(summary, ts)
    vif = screen_factors(merged[["Date"] + FACTOR_COLS], factor_cols=FACTOR_COLS)["vif"].reset_index()
    vif.columns = ["factor", "VIF"]
    save_table(vif, TABLE_DIR / "factor_vif.csv")
    print(f"[Factor loading] 회귀 표본 {len(merged)}개월, 전략 {strat_cols}")
    # Walk-forward 검증 (60→12 이동, net10bp 이어붙인 성과)
    wf_rows = []
    for name, cs in series.items():
        net = cs["ret"].values - cs["turnover"].values * COST_RATE
        wf_rows.append({"strategy": name, **walk_forward_metrics(net)})
    wf_tbl = pd.DataFrame(wf_rows)
    save_table(wf_tbl, TABLE_DIR / "walk_forward_summary.csv")
    print("\n[Walk-forward — 60→12 이동, net10bp 이어붙인 성과]")
    print(wf_tbl.round(3).to_string(index=False))

    # Adoption decision (OOS 10bp net, 사전등록 비열등 4조건)
    oos_tbl = oos_adoption_table(series, asset_ret)
    try:
        adopt = adoption_decision(oos_tbl)
        save_table(adopt, TABLE_DIR / "adoption_decision.csv")
        print("\n[Adoption decision — OOS 10bp net, 비열등 4조건]")
        show = ["strategy", "Calmar_net", "MDD_pct", "tail_month_avg_pct", "avg_turnover_pct",
                "cond1_calmar", "cond2_mdd", "cond3_tail", "cond4_turnover", "non_inferior"]
        print(adopt[show].round(3).to_string(index=False))
    except ValueError as e:
        adopt = None
        print(f"\n[Adoption decision] 스킵: {e}")

    print("\n[저장] dynamic_lambda_path / selftest_strategy_comparison / attribution_* / factor_loading_* / factor_vif")
    print("=" * 78)
    return {"comparison": comp, "lambda_path": path, "attribution": attr, "factor_summary": summary, "adoption": adopt, "walk_forward": wf_tbl}


if __name__ == "__main__":
    run_selftest()
