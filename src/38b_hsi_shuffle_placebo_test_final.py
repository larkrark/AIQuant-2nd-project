# -*- coding: utf-8 -*-
"""
38b_hsi_shuffle_placebo_test_final.py

HSI 목표비중 Shuffle Placebo Test — 보고서 산출물 포함 최종 합본

목적
----
HSI 목표비중의 '시간 배치'가 실제로 성과와 방어력에 유리했는지 확인하는
ablation / placebo test를 수행한다.

37번 실험과의 연결
-----------------
37_cagr_gap_attribution_dynamic_v1_vs_fixedbm.py는 dynamic_v1과 FixedBM_70_20_10의
월별 산술 초과수익을 다음 두 항으로 분해했다.

    excess_t = exposure_effect_t + timing_effect_t

- exposure_effect: 시간평균 비중 차이로 설명되는 부분
- timing_effect  : 평균 대비 월별 비중 편차가 실제 월수익률과 만나 발생한 부분

38b는 이 중 timing_effect가 HSI 목표비중의 실제 시간 배치에서 나온 것인지,
아니면 목표비중을 무작위 배치해도 비슷하게 재현되는지 확인하는 후속 검정이다.

방법
----
1. dynamic_v1의 실현 lambda_t 시퀀스는 그대로 고정한다.
2. HSI 목표비중 w*_t의 시간 배치만 block permutation 방식으로 무작위 재배열한다.
3. 셔플된 목표비중과 실제 lambda_t로 실제비중을 재귀적으로 다시 계산한다.

       w_t = w_(t-1) + lambda_t * (w*_shuffled,t - w_(t-1))

4. 이 placebo 포트폴리오 성과를 N_SIMULATIONS회 반복하여 귀무분포를 만든다.
5. 실제 dynamic_v1 성과가 귀무분포에서 어느 위치에 있는지 percentile과 p-value로 확인한다.

주의
----
이 검정은 HSI 전체의 독립 기여를 완전히 분리하는 최종 증명이 아니다.
실제 lambda_used 경로 자체에도 risk_relief 지속 조건처럼 HSI 상태와 연결된 정보가 일부
포함될 수 있기 때문이다. 따라서 본 검정은 'HSI 목표비중의 시간 배치가 무작위 배치보다
유리했는지'를 확인하는 보조 검증으로 해석한다.

주요 출력
---------
output/tables/main_final_38b_hsi_shuffle_actual_metrics.csv
output/tables/flex_38b_hsi_shuffle_placebo_runs.csv
output/tables/main_final_38b_hsi_shuffle_summary.csv
output/tables/main_final_38b_hsi_shuffle_report_comparison.csv
output/figures/main_final_fig_38b_oos_<metric>_distribution.png
output/figures/main_final_fig_38b_oos_advantage_percentile_bar.png
docs/main_final_38b_hsi_shuffle_placebo_report_section.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import final_project_config as cfg


# =============================================================================
# 0. 실험 설정
# =============================================================================
STRATEGY_NAME = "dynamic_v1"
COMPOSITION_FILE = cfg.TABLE_DIR / "main_final_portfolio_composition_dynamic_v1.csv"

# 기본값: 팀 논의에서 제안한 3~6개월 범위 중 중간값 성격. 필요 시 4로 바꿔도 됨.
BLOCK_SIZE = 4
N_SIMULATIONS = 1000
RANDOM_SEED = 42
COST_BPS = 10.0

IS_START = "2012-04-30"
IS_END = "2020-12-31"
OOS_START = "2021-01-31"
OOS_END = "2026-06-30"

PROJECT_DIR = getattr(cfg, "PROJECT_DIR", Path(__file__).resolve().parents[1])
TABLE_DIR = getattr(cfg, "TABLE_DIR", PROJECT_DIR / "output" / "tables")
FIGURE_DIR = getattr(cfg, "FIGURE_DIR", PROJECT_DIR / "output" / "figures")
DOCS_DIR = getattr(cfg, "DOCS_DIR", PROJECT_DIR / "docs")

OUTPUT_ACTUAL = TABLE_DIR / "main_final_38b_hsi_shuffle_actual_metrics.csv"
OUTPUT_RUNS = TABLE_DIR / "flex_38b_hsi_shuffle_placebo_runs.csv"
OUTPUT_SUMMARY = TABLE_DIR / "main_final_38b_hsi_shuffle_summary.csv"
OUTPUT_REPORT_COMPARISON = TABLE_DIR / "main_final_38b_hsi_shuffle_report_comparison.csv"
OUTPUT_NOTE = DOCS_DIR / "main_final_38b_hsi_shuffle_placebo_report_section.md"

DEFAULT_STATE_TARGET_WEIGHTS: Dict[str, Dict[str, float]] = {
    "risk_relief": {},
    "neutral_watch": {},
    "conflict": {},
    "risk_warning": {},
    "accident_zone": {},
    "insufficient_data": {},
}

TICKERS = list(cfg.TICKERS)
RISK_TICKER = getattr(cfg, "RISK_TICKER", TICKERS[0])
BOND_TICKER = getattr(cfg, "BOND_TICKER", TICKERS[1])
CASH_TICKER = getattr(cfg, "CASH_TICKER", TICKERS[2])
PERIODS_PER_YEAR = getattr(cfg, "PERIODS_PER_YEAR", 12)

# fallback 목표비중. cfg.FINAL_BASELINE_ALLOCATION_RULES가 있으면 그 값을 우선 사용한다.
DEFAULT_TARGET_BY_STATE: Dict[str, List[float]] = {
    "risk_relief": [0.70, 0.20, 0.10],
    "neutral_watch": [0.50, 0.35, 0.15],
    "conflict": [0.35, 0.40, 0.25],
    "risk_warning": [0.20, 0.45, 0.35],
    "accident_zone": [0.00, 0.30, 0.70],
    "insufficient_data": [np.nan, np.nan, np.nan],
}

# 지표별 방향. higher = 클수록 좋음, lower = 작을수록 좋음.
# 실제 백분위(raw percentile)와 별도로, 해석용 advantage_percentile을 계산한다.
METRIC_INFO: Dict[str, Tuple[str, str, str]] = {
    "gross_cum_return_pct": ("Gross 누적수익률", "%", "higher"),
    "gross_cagr_pct": ("Gross CAGR", "%", "higher"),
    "gross_ann_vol_pct": ("Gross 연환산 변동성", "%", "lower"),
    "gross_mdd_pct": ("Gross MDD", "%", "higher"),
    "gross_sharpe": ("Gross Sharpe", "ratio", "higher"),
    "gross_calmar": ("Gross Calmar", "ratio", "higher"),
    "gross_tail_strategy_avg_pct": ("Gross tail-month 평균수익", "%", "higher"),
    "gross_win_rate_pct": ("Gross 월 승률", "%", "higher"),
    "net10_cum_return_pct": ("Net10bp 누적수익률", "%", "higher"),
    "net10_cagr_pct": ("Net10bp CAGR", "%", "higher"),
    "net10_ann_vol_pct": ("Net10bp 연환산 변동성", "%", "lower"),
    "net10_mdd_pct": ("Net10bp MDD", "%", "higher"),
    "net10_sharpe": ("Net10bp Sharpe", "ratio", "higher"),
    "net10_calmar": ("Net10bp Calmar", "ratio", "higher"),
    "net10_tail_strategy_avg_pct": ("Net10bp tail-month 평균수익", "%", "higher"),
    "net10_win_rate_pct": ("Net10bp 월 승률", "%", "higher"),
    "avg_monthly_turnover_pct": ("평균 월 Turnover", "%", "lower"),
    "avg_annual_turnover_pct": ("평균 연환산 Turnover", "%", "lower"),
    "max_monthly_turnover_pct": ("최대 월 Turnover", "%", "lower"),
}

# 보고서에 우선 노출할 핵심 지표. 방어형 RA 기준으로 net10bp 중심.
CORE_REPORT_METRICS = [
    "net10_cagr_pct",
    "net10_ann_vol_pct",
    "net10_mdd_pct",
    "net10_sharpe",
    "net10_calmar",
    "net10_tail_strategy_avg_pct",
    "avg_annual_turnover_pct",
    "net10_win_rate_pct",
]

PLOT_METRICS = [
    "net10_cagr_pct",
    "net10_ann_vol_pct",
    "net10_mdd_pct",
    "net10_sharpe",
    "net10_calmar",
    "net10_tail_strategy_avg_pct",
    "avg_annual_turnover_pct",
    "net10_win_rate_pct",
]


# =============================================================================
# 1. 데이터 로딩
# =============================================================================
def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} 파일이 없습니다: {path}")


def ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)


def load_monthly_returns() -> pd.DataFrame:
    """hsi_data_bundle.xlsx의 월수익률 decimal 시트를 로드한다."""
    bundle_path = cfg.find_data_bundle()
    ret = pd.read_excel(bundle_path, sheet_name=cfg.BACKTEST_RETURN_SHEET)
    date_col = ret.columns[0]
    ret[date_col] = pd.to_datetime(ret[date_col])
    ret = ret.set_index(date_col).sort_index()
    missing = [t for t in TICKERS if t not in ret.columns]
    if missing:
        raise ValueError(f"월수익률 파일에 필요한 티커 열이 없습니다: {missing}")
    ret = ret[TICKERS].astype(float)
    ret.index = ret.index + pd.offsets.MonthEnd(0)
    ret.index.name = "Date"
    return ret


def load_dynamic_composition() -> pd.DataFrame:
    """dynamic_v1 구성비중 파일을 로드한다."""
    require_file(COMPOSITION_FILE, "dynamic_v1 포트폴리오 구성")
    comp = pd.read_csv(COMPOSITION_FILE)
    if "apply_date" not in comp.columns:
        comp = comp.rename(columns={comp.columns[0]: "apply_date"})
    comp["apply_date"] = pd.to_datetime(comp["apply_date"])
    if "signal_date" in comp.columns:
        comp["signal_date"] = pd.to_datetime(comp["signal_date"])
    comp = comp.set_index("apply_date").sort_index()
    comp.index.name = "Date"

    weight_cols = [f"w_{t}" for t in TICKERS]
    missing_w = [c for c in weight_cols if c not in comp.columns]
    if missing_w:
        raise ValueError(f"dynamic_v1 구성 파일에 실제 비중 열이 없습니다: {missing_w}")
    if "lambda_used" not in comp.columns:
        raise ValueError("dynamic_v1 구성 파일에 lambda_used 열이 필요합니다.")
    return comp


def extract_actual_weights(comp: pd.DataFrame) -> pd.DataFrame:
    w = comp[[f"w_{t}" for t in TICKERS]].copy()
    w.columns = TICKERS
    return w.astype(float)


def extract_lambdas(comp: pd.DataFrame) -> pd.Series:
    return comp["lambda_used"].astype(float).rename("lambda_used")


def get_state_rule_from_cfg() -> Dict[str, List[float]]:
    """cfg의 목표비중 규칙을 최대한 유연하게 읽는다."""
    raw = getattr(cfg, "FINAL_BASELINE_ALLOCATION_RULES", None)
    if raw is None:
        raw = getattr(cfg, "STATE_TARGET_WEIGHTS", None)
    if raw is None:
        return DEFAULT_TARGET_BY_STATE

    out: Dict[str, List[float]] = {}
    for state, rule in raw.items():
        if isinstance(rule, dict):
            try:
                out[state] = [float(rule[RISK_TICKER]), float(rule[BOND_TICKER]), float(rule[CASH_TICKER])]
            except KeyError:
                # 혹시 ticker key가 아닌 위치기반 dict인 경우를 대비
                vals = list(rule.values())
                if len(vals) >= 3:
                    out[state] = [float(vals[0]), float(vals[1]), float(vals[2])]
        else:
            vals = list(rule)
            if len(vals) >= 3:
                out[state] = [float(vals[0]), float(vals[1]), float(vals[2])]
    out.setdefault("insufficient_data", [np.nan, np.nan, np.nan])
    for k, v in DEFAULT_TARGET_BY_STATE.items():
        out.setdefault(k, v)
    return out


def extract_target_weights(comp: pd.DataFrame) -> pd.DataFrame:
    """
    HSI 목표비중 w*_t를 추출한다.
    1) w_star_<ticker> 열이 있으면 그것을 우선 사용한다.
    2) 없으면 hsi_state를 목표비중 규칙으로 매핑한다.
    insufficient_data는 NaN으로 두고 replay에서 직전 비중 유지로 처리한다.
    """
    w_star_cols = [f"w_star_{t}" for t in TICKERS]
    if all(c in comp.columns for c in w_star_cols):
        tw = comp[w_star_cols].copy()
        tw.columns = TICKERS
        return tw.astype(float)

    # 일부 코드에서 target_w_<ticker> 형식을 쓸 가능성도 지원
    target_cols = [f"target_w_{t}" for t in TICKERS]
    if all(c in comp.columns for c in target_cols):
        tw = comp[target_cols].copy()
        tw.columns = TICKERS
        return tw.astype(float)

    if "hsi_state" not in comp.columns:
        raise ValueError("구성 파일에 w_star_* / target_w_* / hsi_state 중 하나가 필요합니다.")

    rules = get_state_rule_from_cfg()
    rows: List[List[float]] = []
    unknown_states = set()
    for state in comp["hsi_state"].astype(str):
        if state not in rules:
            unknown_states.add(state)
            rows.append([np.nan] * len(TICKERS))
        else:
            rows.append(rules[state])

    if unknown_states:
        print(f"[주의] 목표비중 매핑 불가 상태: {sorted(unknown_states)}")
        print("       해당 행은 replay 과정에서 직전 비중 유지로 처리합니다.")

    tw = pd.DataFrame(rows, index=comp.index, columns=TICKERS).astype(float)
    return tw


# =============================================================================
# 2. 비중 재생, 셔플, 성과 계산
# =============================================================================
def normalize_weight_vector(w: np.ndarray) -> np.ndarray:
    """비중 벡터를 [0,1] 범위와 합계 1로 정리한다."""
    w = np.asarray(w, dtype=float)
    w = np.where(np.isfinite(w), w, 0.0)
    w = np.clip(w, 0.0, 1.0)
    s = w.sum()
    if s <= 0:
        return np.array([1.0 / len(w)] * len(w), dtype=float)
    return w / s


def compute_turnover(weights: pd.DataFrame) -> pd.Series:
    turnover = weights.diff().abs().sum(axis=1) * 0.5
    if len(turnover) > 0:
        turnover.iloc[0] = 0.0
    return turnover.rename("turnover")


def block_permute_targets(target_w: pd.DataFrame, block_size: int, rng: np.random.Generator) -> pd.DataFrame:
    """
    목표비중을 block_size개월 단위로 나누고 블록 순서만 무작위 재배열한다.

    첫 번째 월은 실제 dynamic_v1의 첫 적용비중을 시작점으로 쓰기 때문에
    replay에서 목표비중이 사용되지 않는다. 따라서 첫 번째 행은 고정하고,
    두 번째 행부터 블록 셔플한다. 이렇게 해야 매 시뮬레이션에서 무작위로
    하나의 목표비중이 누락되는 문제를 피할 수 있다.
    """
    n = len(target_w)
    if n <= 1:
        return target_w.copy()

    body_positions = list(range(1, n))
    blocks = [body_positions[i:i + block_size] for i in range(0, len(body_positions), block_size)]
    permuted_block_order = rng.permutation(len(blocks))
    shuffled_body = [idx for block_id in permuted_block_order for idx in blocks[block_id]]
    shuffled_positions = [0] + shuffled_body

    shuffled = target_w.iloc[shuffled_positions].copy()
    shuffled.index = target_w.index
    return shuffled


def replay_with_fixed_lambda(
    returns: pd.DataFrame,
    target_w: pd.DataFrame,
    lambda_used: pd.Series,
    initial_weight: pd.Series,
    cost_bps: float = COST_BPS,
) -> pd.DataFrame:
    """
    고정된 lambda_used 경로와 주어진 목표비중으로 월별 실제 비중을 재계산한다.
    첫 달은 실제 dynamic_v1의 첫 적용비중을 그대로 사용한다.
    두 번째 달부터 w_t = w_(t-1) + lambda_t * (w*_t - w_(t-1))를 적용한다.
    """
    idx = returns.index.intersection(target_w.index).intersection(lambda_used.index).sort_values()
    if len(idx) == 0:
        raise ValueError("returns, target_w, lambda_used의 공통 날짜가 없습니다.")

    r = returns.loc[idx, TICKERS]
    tw = target_w.loc[idx, TICKERS]
    lam = lambda_used.loc[idx]
    prev = normalize_weight_vector(initial_weight.reindex(TICKERS).astype(float).values)

    records: List[Dict[str, float]] = []
    for k, date in enumerate(idx):
        if k == 0:
            new_w = prev.copy()
            turnover = 0.0
        else:
            target = tw.loc[date].values.astype(float)
            if np.isnan(target).any():
                target = prev.copy()  # insufficient_data 또는 매핑 불가: 이전 비중 유지
            else:
                target = normalize_weight_vector(target)
            lmbd = float(lam.loc[date])
            new_w = prev + lmbd * (target - prev)
            new_w = normalize_weight_vector(new_w)
            turnover = float(np.abs(new_w - prev).sum() * 0.5)

        gross_ret = float(np.dot(new_w, r.loc[date, TICKERS].values.astype(float)))
        net_ret = gross_ret - turnover * (cost_bps / 10000.0)

        rec: Dict[str, float] = {
            "gross_return": gross_ret,
            "net10_return": net_ret,
            "turnover": turnover,
        }
        for ticker, weight in zip(TICKERS, new_w):
            rec[f"w_{ticker}"] = float(weight)
        records.append(rec)
        prev = new_w

    out = pd.DataFrame(records, index=idx)
    out.index.name = "Date"
    return out


def actual_path_from_saved_weights(
    returns: pd.DataFrame,
    actual_weights: pd.DataFrame,
    cost_bps: float = COST_BPS,
) -> pd.DataFrame:
    idx = returns.index.intersection(actual_weights.index).sort_values()
    w = actual_weights.loc[idx, TICKERS]
    r = returns.loc[idx, TICKERS]
    turnover = compute_turnover(w)
    gross = (w * r).sum(axis=1)
    net = gross - turnover * (cost_bps / 10000.0)
    out = pd.DataFrame({
        "gross_return": gross,
        "net10_return": net,
        "turnover": turnover,
    }, index=idx)
    for ticker in TICKERS:
        out[f"w_{ticker}"] = w[ticker]
    out.index.name = "Date"
    return out


def period_slice(df: pd.DataFrame, period: str) -> pd.DataFrame:
    if period == "IS":
        return df.loc[IS_START:IS_END]
    if period == "OOS":
        return df.loc[OOS_START:OOS_END]
    return df


def compute_return_metrics(ret: pd.Series, risk_ret: pd.Series) -> Dict[str, float]:
    ret = ret.dropna().astype(float)
    if len(ret) == 0:
        return {
            "cum_return_pct": np.nan,
            "cagr_pct": np.nan,
            "ann_vol_pct": np.nan,
            "mdd_pct": np.nan,
            "sharpe": np.nan,
            "calmar": np.nan,
            "tail_strategy_avg_pct": np.nan,
            "win_rate_pct": np.nan,
        }

    n_months = len(ret)
    years = n_months / PERIODS_PER_YEAR
    wealth = (1.0 + ret).cumprod()
    cum_return = wealth.iloc[-1] - 1.0
    cagr = (wealth.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 else np.nan
    drawdown = wealth / wealth.cummax() - 1.0
    mdd = drawdown.min()
    ann_vol = ret.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR) if len(ret) > 1 else np.nan
    ann_ret_arith = ret.mean() * PERIODS_PER_YEAR
    sharpe = ann_ret_arith / ann_vol if ann_vol and ann_vol > 0 else np.nan
    calmar = cagr / abs(mdd) if pd.notna(mdd) and mdd < 0 else np.nan
    win_rate = (ret > 0).mean()

    # risk_ret의 하위 10% 월을 tail-month로 정의한다. 기간별로 분포를 다시 잡는다.
    risk_ret = risk_ret.reindex(ret.index).dropna().astype(float)
    common_idx = ret.index.intersection(risk_ret.index)
    if len(common_idx) > 0:
        q10 = risk_ret.loc[common_idx].quantile(0.10)
        tail_mask = risk_ret.loc[common_idx] <= q10
        tail_avg = ret.loc[common_idx][tail_mask].mean() if tail_mask.any() else np.nan
    else:
        tail_avg = np.nan

    return {
        "cum_return_pct": cum_return * 100.0,
        "cagr_pct": cagr * 100.0,
        "ann_vol_pct": ann_vol * 100.0 if pd.notna(ann_vol) else np.nan,
        "mdd_pct": mdd * 100.0,
        "sharpe": sharpe,
        "calmar": calmar,
        "tail_strategy_avg_pct": tail_avg * 100.0 if pd.notna(tail_avg) else np.nan,
        "win_rate_pct": win_rate * 100.0,
    }


def compute_strategy_metrics(path: pd.DataFrame, returns: pd.DataFrame, period: str) -> Dict[str, float]:
    p = period_slice(path, period)
    r_period = period_slice(returns, period)
    risk_ret = r_period[RISK_TICKER]

    gross = compute_return_metrics(p["gross_return"], risk_ret)
    net10 = compute_return_metrics(p["net10_return"], risk_ret)

    row: Dict[str, float] = {"n_months": float(len(p))}
    for key, value in gross.items():
        row[f"gross_{key}"] = value
    for key, value in net10.items():
        row[f"net10_{key}"] = value

    if len(p) > 0:
        row["avg_monthly_turnover_pct"] = p["turnover"].mean() * 100.0
        row["avg_annual_turnover_pct"] = p["turnover"].mean() * PERIODS_PER_YEAR * 100.0
        row["max_monthly_turnover_pct"] = p["turnover"].max() * 100.0
    else:
        row["avg_monthly_turnover_pct"] = np.nan
        row["avg_annual_turnover_pct"] = np.nan
        row["max_monthly_turnover_pct"] = np.nan
    return row


def build_metrics_row(path: pd.DataFrame, returns: pd.DataFrame, period: str, label: str, sim_id: int | None = None) -> Dict[str, float | str | int | None]:
    row = compute_strategy_metrics(path, returns, period)
    row.update({
        "strategy": label,
        "period": period,
        "sim_id": sim_id,
        "cost_bps": COST_BPS,
        "block_size": BLOCK_SIZE,
    })
    return row


# =============================================================================
# 3. 시뮬레이션, 요약, sanity check
# =============================================================================
def sanity_check_replay(
    returns: pd.DataFrame,
    actual_weights: pd.DataFrame,
    target_w: pd.DataFrame,
    lambda_used: pd.Series,
) -> float:
    """원래 목표비중과 lambda_used로 실제 저장 비중을 재생했을 때 최대 오차를 확인한다."""
    idx = returns.index.intersection(actual_weights.index).intersection(target_w.index).intersection(lambda_used.index).sort_values()
    initial = actual_weights.loc[idx[0], TICKERS]
    replay = replay_with_fixed_lambda(returns.loc[idx], target_w.loc[idx], lambda_used.loc[idx], initial)
    replay_w = replay[[f"w_{t}" for t in TICKERS]].copy()
    replay_w.columns = TICKERS
    actual_w = actual_weights.loc[idx, TICKERS]
    max_diff = float((replay_w - actual_w).abs().max().max())
    return max_diff


def run_placebo_simulations(
    returns: pd.DataFrame,
    actual_weights: pd.DataFrame,
    target_w: pd.DataFrame,
    lambda_used: pd.Series,
) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    idx = returns.index.intersection(actual_weights.index).intersection(target_w.index).intersection(lambda_used.index).sort_values()
    returns = returns.loc[idx]
    actual_weights = actual_weights.loc[idx]
    target_w = target_w.loc[idx]
    lambda_used = lambda_used.loc[idx]
    initial = actual_weights.loc[idx[0], TICKERS]

    rows: List[Dict[str, float | str | int | None]] = []
    periods = ["FULL", "IS", "OOS"]
    for sim in range(N_SIMULATIONS):
        shuffled_target = block_permute_targets(target_w, BLOCK_SIZE, rng)
        placebo_path = replay_with_fixed_lambda(returns, shuffled_target, lambda_used, initial)
        for period in periods:
            rows.append(build_metrics_row(placebo_path, returns, period, label="shuffle_placebo", sim_id=sim))
        if (sim + 1) % max(1, N_SIMULATIONS // 10) == 0:
            print(f"    simulation progress: {sim + 1}/{N_SIMULATIONS}")
    return pd.DataFrame(rows)


def compute_actual_metrics(returns: pd.DataFrame, actual_weights: pd.DataFrame) -> pd.DataFrame:
    idx = returns.index.intersection(actual_weights.index).sort_values()
    actual_path = actual_path_from_saved_weights(returns.loc[idx], actual_weights.loc[idx])
    rows = [build_metrics_row(actual_path, returns.loc[idx], period, label=STRATEGY_NAME, sim_id=None) for period in ["FULL", "IS", "OOS"]]
    return pd.DataFrame(rows)


def summarize_placebo(runs: pd.DataFrame, actual: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, float | str | int]] = []
    for period in ["FULL", "IS", "OOS"]:
        actual_row = actual.loc[actual["period"].eq(period)].iloc[0]
        null_rows = runs.loc[runs["period"].eq(period)]
        for metric, (display_name, unit, direction) in METRIC_INFO.items():
            if metric not in null_rows.columns or metric not in actual_row.index:
                continue
            vals = null_rows[metric].dropna().astype(float).values
            if len(vals) == 0:
                continue
            actual_value = float(actual_row[metric])
            p05 = float(np.percentile(vals, 5))
            p50 = float(np.percentile(vals, 50))
            p95 = float(np.percentile(vals, 95))
            raw_percentile = float((vals <= actual_value).mean() * 100.0)
            if direction == "higher":
                advantage_percentile = raw_percentile
                one_sided_p = float((1 + np.sum(vals >= actual_value)) / (len(vals) + 1))
            else:
                advantage_percentile = float((vals >= actual_value).mean() * 100.0)
                one_sided_p = float((1 + np.sum(vals <= actual_value)) / (len(vals) + 1))

            rows.append({
                "period": period,
                "metric": metric,
                "display_name": display_name,
                "unit": unit,
                "better_direction": direction,
                "actual": actual_value,
                "null_mean": float(np.mean(vals)),
                "null_std": float(np.std(vals, ddof=1)),
                "null_p05": p05,
                "null_p50": p50,
                "null_p95": p95,
                "actual_minus_null_p50": actual_value - p50,
                "actual_raw_percentile": raw_percentile,
                "actual_advantage_percentile": advantage_percentile,
                "one_sided_p_value": one_sided_p,
                "n_simulations": len(vals),
                "block_size": BLOCK_SIZE,
                "cost_bps": COST_BPS,
            })
    return pd.DataFrame(rows)


def verdict_text(row: pd.Series) -> str:
    pctl = float(row["actual_advantage_percentile"])
    direction = str(row["better_direction"])
    if pctl >= 95:
        return "실제값이 유리한 극단 5% 이내: 무작위 배치 대비 매우 유리"
    if pctl >= 80:
        return "실제값이 유리한 상위권: 무작위 배치 대비 유리"
    if 40 <= pctl <= 60:
        return "placebo 중앙부: HSI 목표비중 타이밍 우위가 뚜렷하지 않음"
    if direction == "lower" and pctl < 40:
        return "실제값이 유리하지 않은 구간: 비용·변동성·회전율 측면 추가 해석 필요"
    return "placebo 중하위권: 추가 해석 필요"


def build_report_comparison(summary: pd.DataFrame) -> pd.DataFrame:
    out = summary.loc[summary["period"].isin(["OOS", "FULL"]) & summary["metric"].isin(CORE_REPORT_METRICS)].copy()
    out["difference_display"] = out.apply(
        lambda r: f"{r['actual_minus_null_p50']:+.2f}%p" if r["unit"] == "%" else f"{r['actual_minus_null_p50']:+.3f}", axis=1
    )
    out["verdict"] = out.apply(verdict_text, axis=1)
    cols = [
        "period", "display_name", "unit", "actual", "null_p50", "null_p95",
        "actual_minus_null_p50", "difference_display", "actual_advantage_percentile",
        "one_sided_p_value", "verdict",
    ]
    return out[cols].sort_values(["period", "display_name"])


# =============================================================================
# 4. 그림 저장
# =============================================================================
def save_distribution_figures(actual: pd.DataFrame, runs: pd.DataFrame) -> Dict[str, Path]:
    figure_paths: Dict[str, Path] = {}
    oos_actual = actual.loc[actual["period"].eq("OOS")].iloc[0]
    oos_runs = runs.loc[runs["period"].eq("OOS")]

    for metric in PLOT_METRICS:
        if metric not in oos_runs.columns:
            continue
        display_name, unit, _direction = METRIC_INFO[metric]
        vals = oos_runs[metric].dropna().astype(float)
        if len(vals) == 0:
            continue
        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        ax.hist(vals, bins=40)
        ax.axvline(float(oos_actual[metric]), linestyle="--", linewidth=2, label="actual dynamic_v1")
        ax.axvline(float(vals.median()), linestyle=":", linewidth=1.5, label="placebo median")
        xlabel = f"{display_name} ({unit})" if unit == "%" else display_name
        ax.set_title(f"38b. HSI shuffle placebo — OOS {display_name}")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("count")
        ax.legend()
        fig.tight_layout()
        out = FIGURE_DIR / f"main_final_fig_38b_oos_{metric}_distribution.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        figure_paths[metric] = out
    return figure_paths


def save_percentile_bar(summary: pd.DataFrame) -> Path:
    oos = summary.loc[summary["period"].eq("OOS") & summary["metric"].isin(CORE_REPORT_METRICS)].copy()
    oos = oos.sort_values("actual_advantage_percentile")
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.bar(oos["display_name"], oos["actual_advantage_percentile"])
    ax.axhline(95, linestyle="--", linewidth=1, label="95% advantage percentile")
    ax.axhline(80, linestyle=":", linewidth=1, label="80% advantage percentile")
    ax.axhline(50, linestyle="-.", linewidth=1, label="median")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Advantage percentile")
    ax.set_title("38b. OOS actual dynamic_v1 position in placebo distribution")
    ax.tick_params(axis="x", rotation=35)
    ax.legend()
    fig.tight_layout()
    out = FIGURE_DIR / "main_final_fig_38b_oos_advantage_percentile_bar.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


# =============================================================================
# 5. 보고서용 Markdown 생성
# =============================================================================
def relpath_for_docs(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(DOCS_DIR.resolve())).replace("\\", "/")
    except Exception:
        try:
            return str(Path("..") / path.resolve().relative_to(PROJECT_DIR.resolve())).replace("\\", "/")
        except Exception:
            return str(path).replace("\\", "/")


def fmt(v: float, unit: str = "") -> str:
    if pd.isna(v):
        return ""
    if unit == "%":
        return f"{v:.2f}%"
    if unit == "p":
        return f"{v:.1f}p"
    return f"{v:.3f}"


def simple_markdown_table(df: pd.DataFrame) -> str:
    """tabulate 의존성 없이 Markdown 표를 만든다."""
    if df.empty:
        return ""
    columns = list(df.columns)
    rows = []
    rows.append("| " + " | ".join(columns) + " |")
    rows.append("|" + "|".join(["---"] * len(columns)) + "|")
    for _, r in df.iterrows():
        rows.append("| " + " | ".join(str(r[c]) for c in columns) + " |")
    return "\n".join(rows)


def select_summary_row(summary: pd.DataFrame, period: str, metric: str) -> pd.Series | None:
    tmp = summary.loc[summary["period"].eq(period) & summary["metric"].eq(metric)]
    if tmp.empty:
        return None
    return tmp.iloc[0]


def build_report_section(
    summary: pd.DataFrame,
    report_comp: pd.DataFrame,
    figure_paths: Dict[str, Path],
    percentile_fig: Path,
    max_replay_weight_diff: float,
) -> str:
    def s(metric: str) -> pd.Series | None:
        return select_summary_row(summary, "OOS", metric)

    cagr = s("net10_cagr_pct")
    mdd = s("net10_mdd_pct")
    calmar = s("net10_calmar")
    tail = s("net10_tail_strategy_avg_pct")
    turnover = s("avg_annual_turnover_pct")

    # 보고서 표 2는 OOS 핵심 지표만 깔끔하게 노출
    oos_table = report_comp.loc[report_comp["period"].eq("OOS")].copy()
    display_rows = []
    for _, r in oos_table.iterrows():
        display_rows.append({
            "지표": r["display_name"],
            "실제값": fmt(float(r["actual"]), str(r["unit"])),
            "Placebo 중앙값": fmt(float(r["null_p50"]), str(r["unit"])),
            "차이": r["difference_display"],
            "유리 백분위": f"{float(r['actual_advantage_percentile']):.1f}%ile",
            "p-value": f"{float(r['one_sided_p_value']):.3f}",
            "해석": r["verdict"],
        })
    table2 = pd.DataFrame(display_rows)

    lines: List[str] = []
    lines.append("## 13.X HSI 목표비중 Shuffle Placebo Test")
    lines.append("")
    lines.append("### 목적")
    lines.append("")
    lines.append(
        "37번 실험에서는 Final_RA_dynamic_v1과 FixedBM_70_20_10의 수익률 격차를 "
        "exposure effect와 timing effect로 분해하였다. 그 결과 BM 대비 CAGR 열위는 주로 "
        "평균 위험자산 노출 축소에서 발생했고, timing effect는 양(+)의 방향으로 나타났다. "
        "38b 실험은 이 positive timing effect가 HSI 목표비중의 실제 시간 배치에서 나온 것인지, "
        "아니면 목표비중을 무작위로 배치해도 비슷하게 재현되는지 확인하기 위한 ablation/placebo test이다."
    )
    lines.append("")
    lines.append("### 37번 exposure/timing 분해와의 연결")
    lines.append("")
    lines.append(
        "37번의 exposure effect는 전략이 평균적으로 FixedBM보다 위험자산을 적게 보유한 데서 발생한 효과이다. "
        "반면 timing effect는 실제 월별 비중이 자기 평균비중에서 벗어난 부분이 해당 월 수익률과 만나 발생한 효과이다. "
        "따라서 HSI 목표비중의 시간 배치를 무작위로 섞으면 평균 노출 구조는 대체로 유지하면서도, "
        "어느 시점에 어떤 목표비중을 사용했는지에 해당하는 timing 정보를 훼손할 수 있다. "
        "이 점에서 38b 실험은 37번에서 관찰된 positive timing effect가 우연한 배치인지 확인하는 후속 검정이다."
    )
    lines.append("")
    lines.append("### 방법")
    lines.append("")
    lines.append("1. dynamic_v1의 실현 λ_t 시퀀스는 그대로 고정한다. 변동성·rolling drawdown 기반 λ 조절 경로는 손대지 않는다.")
    lines.append(f"2. HSI 목표비중 시퀀스를 {BLOCK_SIZE}개월 블록 단위로 무작위 셔플한다. 이는 상태의 시간적 지속성 구조를 일부 보존하기 위한 처리이다.")
    lines.append("3. 셔플된 HSI 목표비중 w*_shuffled,t와 실제 λ_t를 이용해 placebo 포트폴리오 비중을 재귀적으로 재계산한다.")
    lines.append("")
    lines.append("```text")
    lines.append("w_t = w_(t-1) + λ_t × (w*_shuffled,t - w_(t-1))")
    lines.append("```")
    lines.append("")
    lines.append(f"4. 위 과정을 {N_SIMULATIONS}회 반복하여 placebo 귀무분포를 만들고, 실제 dynamic_v1의 성과가 이 분포에서 몇 백분위에 위치하는지 확인한다.")
    lines.append("")
    lines.append("### 해석상 주의")
    lines.append("")
    lines.append(
        "이 검정은 HSI 전체의 독립 기여를 완전히 분리하는 최종 증명이 아니다. "
        "실제 λ_t 경로 자체에도 risk_relief 지속 조건처럼 HSI 상태와 연결된 정보가 일부 포함될 수 있기 때문이다. "
        "따라서 본 검정은 HSI 단독 효과를 확정하기보다, HSI 목표비중의 시간 배치가 무작위 배치보다 유리했는지 확인하는 보조 검증으로 해석한다."
    )
    lines.append("")
    lines.append("### 표와 그림")
    lines.append("")
    lines.append("[표 1. 38b 실험 설계 요약]")
    lines.append("")
    lines.append("| 구분 | 처리 방식 | 해석 |")
    lines.append("|---|---|---|")
    lines.append("| 고정한 정보 | 실제 dynamic_v1의 λ_t 경로 | 변동성·drawdown 기반 실행속도 경로는 유지 |")
    lines.append("| 무작위화한 정보 | HSI 목표비중의 시간 배치 | HSI 방향 정보의 시점성을 제거 |")
    lines.append(f"| 셔플 방식 | {BLOCK_SIZE}개월 블록 셔플 | 상태 지속성을 일부 보존 |")
    lines.append(f"| 반복 횟수 | {N_SIMULATIONS}회 | 단일 셔플 우연성 방지 |")
    lines.append(f"| 재구성 점검 | 최대 비중 오차 {max_replay_weight_diff:.2e} | 실제 비중 경로와 replay 가정의 정합성 확인 |")
    lines.append("| 판정 기준 | 유리 백분위, 단측 p-value | 실제 dynamic_v1이 placebo 분포에서 어디에 있는지 확인 |")
    lines.append("")
    lines.append("표 1은 38b 실험에서 무엇을 고정하고 무엇을 무작위화했는지 정리한 것이다. 이 실험은 λ 실행속도 조절 자체를 제거하지 않고, HSI 목표비중의 시간 배치만 깨는 방식으로 설계하였다.")
    lines.append("")

    fig_specs = [
        ("net10_cagr_pct", "그림 1. OOS Net10bp CAGR placebo 분포와 실제 dynamic_v1 위치"),
        ("net10_mdd_pct", "그림 2. OOS Net10bp MDD placebo 분포와 실제 dynamic_v1 위치"),
        ("net10_calmar", "그림 3. OOS Net10bp Calmar placebo 분포와 실제 dynamic_v1 위치"),
        ("net10_tail_strategy_avg_pct", "그림 4. OOS Net10bp tail-month 평균수익 placebo 분포와 실제 dynamic_v1 위치"),
    ]

    for metric, title in fig_specs:
        if metric in figure_paths:
            lines.append(f"![{title}]({relpath_for_docs(figure_paths[metric])})")
            lines.append("")
            lines.append(f"[{title}]")
            r = s(metric)
            if r is not None:
                lines.append(
                    f"{title.split('. ', 1)[0]}은 해당 지표의 placebo 분포와 실제 dynamic_v1의 위치를 비교한 것이다. "
                    f"실제값은 {fmt(float(r['actual']), str(r['unit']))}, placebo 중앙값은 {fmt(float(r['null_p50']), str(r['unit']))}이며, "
                    f"유리 백분위는 {float(r['actual_advantage_percentile']):.1f}%ile, 단측 p-value는 {float(r['one_sided_p_value']):.3f}로 계산되었다. "
                    "실제값이 유리한 상위 구간에 위치할수록 HSI 목표비중의 시간 배치가 무작위 배치보다 유리했음을 시사한다."
                )
            lines.append("")

    lines.append(f"![그림 5. OOS 핵심 지표별 유리 백분위 요약]({relpath_for_docs(percentile_fig)})")
    lines.append("")
    lines.append("[그림 5. OOS 핵심 지표별 유리 백분위 요약]")
    lines.append(
        "그림 5는 OOS 구간의 핵심 지표별 유리 백분위를 요약한 것이다. 수익률 지표와 방어 지표는 값이 클수록 유리하게, "
        "변동성과 Turnover는 값이 낮을수록 유리하게 계산하였다. 따라서 여러 지표가 동시에 높은 유리 백분위에 위치하면, "
        "실제 HSI 목표비중의 시간 배치가 단순 무작위 배치보다 방어형 RA 관점에서 더 안정적으로 작동했을 가능성이 커진다."
    )
    lines.append("")
    lines.append("[표 2. OOS 핵심 지표별 actual dynamic_v1과 placebo 분포 비교]")
    lines.append("")
    lines.append(simple_markdown_table(table2))
    lines.append("")
    lines.append("표 2는 OOS 구간에서 실제 dynamic_v1의 핵심 지표와 placebo 분포의 중앙값을 비교한 것이다. 차이는 실제값에서 placebo 중앙값을 뺀 값이다. % 단위 지표는 %p 차이로, Sharpe와 Calmar는 ratio 차이로 해석한다.")
    lines.append("")
    lines.append("### 결과 해석 기준")
    lines.append("")
    lines.append("- 실제 dynamic_v1이 Calmar, MDD, tail-month 평균수익에서 placebo 유리 백분위 95% 이상이면, HSI 목표비중의 시간 배치가 무작위 배치보다 매우 유리했음을 시사한다.")
    lines.append("- 80~95% 구간이면 HSI 목표비중 타이밍이 유리했을 가능성이 있으나, 보조 근거로 해석한다.")
    lines.append("- 40~60% 중앙부라면 HSI 목표비중 타이밍 우위가 뚜렷하다고 보기 어렵다.")
    lines.append("- Turnover와 변동성은 낮을수록 좋은 지표이므로, 이 두 지표의 유리 백분위는 값이 낮은 쪽을 좋게 평가한다.")
    lines.append("")
    lines.append("### 종합 해석 문장")
    lines.append("")

    def interpret_metric(r: pd.Series | None, name: str) -> str:
        if r is None:
            return f"{name} 결과는 산출되지 않았다."
        return (
            f"{name}의 실제값은 {fmt(float(r['actual']), str(r['unit']))}, placebo 중앙값은 {fmt(float(r['null_p50']), str(r['unit']))}, "
            f"유리 백분위는 {float(r['actual_advantage_percentile']):.1f}%ile이다."
        )

    lines.append(interpret_metric(cagr, "OOS Net10bp CAGR"))
    lines.append(interpret_metric(mdd, "OOS Net10bp MDD"))
    lines.append(interpret_metric(calmar, "OOS Net10bp Calmar"))
    lines.append(interpret_metric(tail, "OOS Net10bp tail-month 평균수익"))
    lines.append(interpret_metric(turnover, "OOS 평균 연환산 Turnover"))
    lines.append("")
    lines.append(
        "종합하면, 38b 실험은 37번에서 확인된 positive timing effect가 단순한 우연 배치였는지 확인하기 위한 placebo 검정이다. "
        "실제 dynamic_v1이 여러 핵심 지표에서 placebo 분포의 유리한 구간에 위치한다면, HSI 목표비중의 시간 배치가 무작위 배치보다 더 나은 방어 성과를 만들었을 가능성이 있다. "
        "다만 실제 λ_t 경로를 고정했기 때문에 이 결과를 HSI 단독 효과의 최종 증명으로 해석하지 않고, HSI 목표비중 타이밍의 유효성을 확인하는 보조 검증으로 해석한다."
    )
    lines.append("")
    return "\n".join(lines)


# =============================================================================
# 6. main
# =============================================================================
def main() -> None:
    print("=" * 80)
    print("38b_hsi_shuffle_placebo_test_final.py 실행 시작")
    print("=" * 80)

    ensure_dirs()

    print("[1] 데이터 로드")
    returns = load_monthly_returns()
    comp = load_dynamic_composition()
    actual_weights = extract_actual_weights(comp)
    lambda_used = extract_lambdas(comp)
    target_w = extract_target_weights(comp)

    common_idx = returns.index.intersection(actual_weights.index).intersection(lambda_used.index).intersection(target_w.index).sort_values()
    returns = returns.loc[common_idx, TICKERS]
    actual_weights = actual_weights.loc[common_idx, TICKERS]
    lambda_used = lambda_used.loc[common_idx]
    target_w = target_w.loc[common_idx, TICKERS]
    print(f"    OK: 공통 {len(common_idx)}개월 ({common_idx.min().date()} ~ {common_idx.max().date()})")

    print("[2] replay sanity check")
    max_diff = sanity_check_replay(returns, actual_weights, target_w, lambda_used)
    print(f"    원본 target_w + lambda_used 재생 비중 최대 오차: {max_diff:.6e}")
    if max_diff > 1e-3:
        print("    [주의] 재생 오차가 큽니다. w_star_* 또는 hsi_state 목표비중 매핑을 확인하세요.")

    print("[3] 실제 dynamic_v1 성과 계산")
    actual_metrics = compute_actual_metrics(returns, actual_weights)
    print(actual_metrics[["period", "gross_cagr_pct", "net10_cagr_pct", "gross_mdd_pct", "net10_mdd_pct", "net10_calmar", "avg_annual_turnover_pct"]].to_string(index=False))

    print(f"[4] placebo Monte Carlo 실행: {N_SIMULATIONS}회, block_size={BLOCK_SIZE}, cost_bps={COST_BPS}")
    runs = run_placebo_simulations(returns, actual_weights, target_w, lambda_used)
    print(f"    OK: {len(runs)}개 metric rows 생성")

    print("[5] percentile / p-value 요약")
    summary = summarize_placebo(runs, actual_metrics)
    report_comp = build_report_comparison(summary)
    print(report_comp.to_string(index=False))

    print("[6] 그림 생성")
    figure_paths = save_distribution_figures(actual_metrics, runs)
    percentile_fig = save_percentile_bar(summary)
    print(f"    분포 그림 {len(figure_paths)}개 저장")
    print(f"    백분위 요약 그림 저장: {percentile_fig}")

    print("[7] 저장")
    actual_metrics.to_csv(OUTPUT_ACTUAL, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_ACTUAL}")
    runs.to_csv(OUTPUT_RUNS, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_RUNS}")
    summary.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_SUMMARY}")
    report_comp.to_csv(OUTPUT_REPORT_COMPARISON, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_REPORT_COMPARISON}")

    report_section = build_report_section(summary, report_comp, figure_paths, percentile_fig, max_diff)
    OUTPUT_NOTE.write_text(report_section, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("=" * 80)
    print("38b_hsi_shuffle_placebo_test_final.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
