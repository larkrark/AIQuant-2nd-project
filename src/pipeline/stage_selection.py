"""
Stage Selection (리포트 20~23): 최종 후보 선별.

00~11 백테스트 시계열을 모아 거래비용 민감도 → Turnover 필터 →
MDD/Sharpe/Calmar/비용 기준 판단으로 최종 후보군을 압축한다.
(조원 20_select_final_candidates 로직을 common/pipeline.config 기반으로 이식)

주의: 실제 실행에는 `data/processed/main_final_*backtest_timeseries.csv` 입력이 필요하며
현재 repo에는 없다. 아래 함수들은 DataFrame을 인자로 받으므로 합성 데이터로 단위 검증 가능.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common.io_utils import save_table
from common.paths import DOCS_DIR, PROCESSED_DIR, TABLE_DIR
from pipeline.config import (
    COST_RATE_GRID,
    FINAL_COST_LABEL,
    FLEX_AVG_TURNOVER_PCT,
    FLEX_MAX_TURNOVER_PCT,
    MAX_COST_DRAG_20BP_PCT,
    MDD_WORSE_THAN_EW_ALLOWANCE_PCT,
    MIN_CAGR_GAP_VS_EW_PCT,
    MIN_CALMAR,
    MIN_MONTHS_RATIO,
    MIN_SHARPE,
    SELECTION_SCORE_WEIGHTS,
    STRICT_AVG_TURNOVER_PCT,
    STRICT_MAX_TURNOVER_PCT,
)

BACKTEST_GLOB = "main_final_*backtest_timeseries.csv"
REQUIRED_COLS = {"strategy_name", "strategy_return", "turnover"}


# ------------------------------------------------------------
# 성과지표 (비용 반영, % 단위)
# ------------------------------------------------------------

def calc_performance_from_returns(returns: pd.Series, turnover: pd.Series, *, cost_label: str, cost_rate: float) -> dict:
    r = pd.to_numeric(returns, errors="coerce")
    t = pd.to_numeric(turnover, errors="coerce").fillna(0.0)
    valid = r.notna()
    r, t = r[valid], t[valid]
    months = len(r)
    if months == 0:
        return {"cost_label": cost_label, "cost_rate": cost_rate, "months": 0}

    r_net = r - t * cost_rate
    cumulative = (1.0 + r_net).cumprod()
    drawdown = cumulative / cumulative.cummax() - 1.0

    final_cum = float(cumulative.iloc[-1])
    cagr = final_cum ** (12 / months) - 1 if months > 0 else np.nan
    ann_vol = r_net.std(ddof=1) * np.sqrt(12) if months > 1 else np.nan
    ann_mean = r_net.mean() * 12
    sharpe = ann_mean / ann_vol if pd.notna(ann_vol) and ann_vol != 0 else np.nan
    downside = r_net[r_net < 0]
    dvol = downside.std(ddof=1) * np.sqrt(12) if len(downside) > 1 else np.nan
    sortino = ann_mean / dvol if pd.notna(dvol) and dvol != 0 else np.nan
    mdd = drawdown.min()
    calmar = cagr / abs(mdd) if pd.notna(mdd) and mdd < 0 else np.nan

    return {
        "cost_label": cost_label, "cost_rate": cost_rate, "months": months,
        "final_cumulative_return": final_cum,
        "CAGR_pct": cagr * 100,
        "annual_volatility_pct": ann_vol * 100 if pd.notna(ann_vol) else np.nan,
        "MDD_pct": mdd * 100 if pd.notna(mdd) else np.nan,
        "Sharpe": sharpe, "Sortino": sortino, "Calmar": calmar,
        "WinRate_pct": (r_net > 0).mean() * 100,
        "avg_turnover_pct": t.mean() * 100,
        "max_turnover_pct": t.max() * 100,
        "total_turnover_pct": t.sum() * 100,
    }


def build_cost_sensitivity_table(backtest_all: pd.DataFrame) -> pd.DataFrame:
    """candidate_key별로 비용률 그리드 전체에 대한 성과지표 표."""
    rows = []
    for candidate_key, g in backtest_all.groupby("candidate_key"):
        base = {
            "candidate_key": candidate_key,
            "source_type": g["source_type"].iloc[0] if "source_type" in g else "other",
            "strategy_name": g["strategy_name"].iloc[0],
        }
        for label, rate in COST_RATE_GRID.items():
            rows.append({**base, **calc_performance_from_returns(g["strategy_return"], g["turnover"], cost_label=label, cost_rate=rate)})
    return pd.DataFrame(rows)


def add_cost_drag_columns(cost_table: pd.DataFrame) -> pd.DataFrame:
    zero = (
        cost_table[cost_table["cost_label"] == "cost_0bp"][["candidate_key", "CAGR_pct"]]
        .rename(columns={"CAGR_pct": "CAGR_0bp_pct"})
    )
    out = cost_table.merge(zero, on="candidate_key", how="left")
    out["CAGR_cost_drag_pct"] = out["CAGR_0bp_pct"] - out["CAGR_pct"]
    return out


# ------------------------------------------------------------
# Turnover 필터 & 최종 판단
# ------------------------------------------------------------

def _percentile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.notna().sum() <= 1:
        return pd.Series(0.5, index=series.index)
    return s.rank(pct=True) if higher_is_better else (-s).rank(pct=True)


def build_turnover_filtered_table(cost_table: pd.DataFrame) -> pd.DataFrame:
    final = cost_table[cost_table["cost_label"] == FINAL_COST_LABEL].copy()
    max_months = final["months"].max()
    min_months = int(max_months * MIN_MONTHS_RATIO) if pd.notna(max_months) else 0
    final["months_pass"] = final["months"] >= min_months
    final["strict_turnover_pass"] = (
        (final["avg_turnover_pct"] <= STRICT_AVG_TURNOVER_PCT)
        & (final["max_turnover_pct"] <= STRICT_MAX_TURNOVER_PCT)
    )
    final["flex_turnover_pass"] = (
        (final["avg_turnover_pct"] <= FLEX_AVG_TURNOVER_PCT)
        & (final["max_turnover_pct"] <= FLEX_MAX_TURNOVER_PCT)
    )
    final["turnover_filter_status"] = np.select(
        [final["strict_turnover_pass"], final["flex_turnover_pass"]],
        ["strict_pass", "flex_pass"], default="fail",
    )
    return final


def _ew_row(cost_table: pd.DataFrame):
    ew = cost_table[(cost_table["strategy_name"] == "EW") & (cost_table["cost_label"] == FINAL_COST_LABEL)]
    return None if ew.empty else ew.iloc[0]


def build_final_judgement(cost_table: pd.DataFrame) -> pd.DataFrame:
    final = build_turnover_filtered_table(cost_table)
    ew = _ew_row(cost_table)
    ew_cagr = np.nan if ew is None else ew["CAGR_pct"]
    ew_mdd = np.nan if ew is None else ew["MDD_pct"]

    cost20 = (
        cost_table[cost_table["cost_label"] == "cost_20bp"][["candidate_key", "CAGR_pct", "CAGR_cost_drag_pct"]]
        .rename(columns={"CAGR_pct": "CAGR_20bp_pct", "CAGR_cost_drag_pct": "CAGR_cost_drag_20bp_pct"})
        if "CAGR_cost_drag_pct" in cost_table.columns else pd.DataFrame(columns=["candidate_key"])
    )
    out = final.merge(cost20, on="candidate_key", how="left")

    out["CAGR_gap_vs_EW_pct"] = out["CAGR_pct"] - ew_cagr
    out["performance_pass"] = out["CAGR_gap_vs_EW_pct"] >= MIN_CAGR_GAP_VS_EW_PCT
    out["mdd_pass"] = out["MDD_pct"] >= (ew_mdd - MDD_WORSE_THAN_EW_ALLOWANCE_PCT)
    out["sharpe_pass"] = out["Sharpe"] >= MIN_SHARPE
    out["calmar_pass"] = out["Calmar"] >= MIN_CALMAR
    out["risk_metric_pass"] = out["mdd_pass"] & out["sharpe_pass"] & out["calmar_pass"]
    if "CAGR_20bp_pct" in out.columns:
        out["cost_sensitivity_pass"] = (out["CAGR_20bp_pct"] >= ew_cagr) & (out["CAGR_cost_drag_20bp_pct"] <= MAX_COST_DRAG_20BP_PCT)
    else:
        out["cost_sensitivity_pass"] = True

    w = SELECTION_SCORE_WEIGHTS
    out["selection_score"] = (
        w["CAGR_pct"] * _percentile(out["CAGR_pct"], True)
        + w["MDD_pct"] * _percentile(out["MDD_pct"], True)
        + w["Calmar"] * _percentile(out["Calmar"], True)
        + w["Sharpe"] * _percentile(out["Sharpe"], True)
        + w["avg_turnover_pct"] * _percentile(out["avg_turnover_pct"], False)
    )

    decisions, reasons = [], []
    for _, row in out.iterrows():
        if row["strategy_name"] == "EW":
            decisions.append("benchmark"); reasons.append("동일가중 비교 기준"); continue
        if not row["months_pass"]:
            decisions.append("exclude_short_sample"); reasons.append("백테스트 월 수 부족"); continue
        if not row["flex_turnover_pass"]:
            decisions.append("exclude_turnover"); reasons.append("Turnover 기준 초과"); continue
        if not row["performance_pass"]:
            decisions.append("exclude_return"); reasons.append("비용 반영 후 CAGR이 EW 미달"); continue
        if not row["risk_metric_pass"]:
            decisions.append("exclude_risk_metric"); reasons.append("MDD/Sharpe/Calmar 기준 미달"); continue
        if not row["cost_sensitivity_pass"]:
            decisions.append("review_cost_sensitive"); reasons.append("20bp 비용에서 성과 훼손 검토 필요"); continue
        if row["strict_turnover_pass"]:
            decisions.append("final_candidate"); reasons.append("Turnover·비용·MDD·Sharpe·Calmar 통과")
        else:
            decisions.append("reserve_candidate"); reasons.append("핵심 조건 통과, Turnover는 유연 기준")
    out["final_decision"] = decisions
    out["decision_reason"] = reasons

    order = {"final_candidate": 1, "reserve_candidate": 2, "review_cost_sensitive": 3,
             "exclude_risk_metric": 4, "exclude_turnover": 5, "exclude_return": 6,
             "exclude_short_sample": 7, "benchmark": 9}
    out["decision_order"] = out["final_decision"].map(order).fillna(99)
    return out.sort_values(["decision_order", "selection_score", "CAGR_pct"], ascending=[True, False, False]).reset_index(drop=True)


# ------------------------------------------------------------
# 파일 기반 실행 (입력 존재 시)
# ------------------------------------------------------------

def _infer_source_type(name: str) -> str:
    s = name.lower()
    for key in ("signal_combo", "event_balance_filter", "lambda", "theta", "baseline", "grid"):
        if key in s:
            return key
    return "other"


def run_from_files() -> pd.DataFrame:
    """PROCESSED_DIR의 main_final_*backtest_timeseries.csv 를 모아 최종 판단표를 만들고 저장."""
    files = [p for p in sorted(PROCESSED_DIR.glob(BACKTEST_GLOB))
             if not any(k in p.name.lower() for k in ("candidate", "selection", "cost_sensitivity"))]
    if not files:
        raise FileNotFoundError(f"{PROCESSED_DIR}에서 {BACKTEST_GLOB} 를 찾지 못했습니다(05~11 백테스트 필요).")

    frames = []
    for p in files:
        df = pd.read_csv(p, encoding="utf-8-sig")
        if not REQUIRED_COLS <= set(df.columns):
            continue
        df["source_file"] = p.name
        df["source_type"] = _infer_source_type(p.name)
        df["strategy_name"] = df["strategy_name"].astype(str)
        df["strategy_return"] = pd.to_numeric(df["strategy_return"], errors="coerce")
        df["turnover"] = pd.to_numeric(df["turnover"], errors="coerce").fillna(0.0)
        df["candidate_key"] = p.stem + "|" + df["strategy_name"]
        frames.append(df)

    backtest_all = pd.concat(frames, ignore_index=True)
    cost_table = add_cost_drag_columns(build_cost_sensitivity_table(backtest_all))
    judgement = build_final_judgement(cost_table)

    save_table(cost_table, TABLE_DIR / "main_final_candidate_all_cost_sensitivity.csv")
    save_table(judgement, TABLE_DIR / "main_final_candidate_final_judgement.csv")
    return judgement


if __name__ == "__main__":
    print(run_from_files().head(20).to_string(index=False))
