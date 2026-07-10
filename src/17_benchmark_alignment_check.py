# -*- coding: utf-8 -*-
"""
17_benchmark_alignment_check.py

목적
----
강사님 RA 개발 기준에 맞춰 메인 BM인 Fixed 70/20/10 BM을 추가하고,
EW Benchmark·HSI baseline·Lambda 0.1·Lambda 0.3을 같은 표에서 비교한다.

핵심 원칙
---------
1. 새 후보를 만드는 실험이 아니라, BM 체계를 정렬하고 기존 후보를 같은 기준에서 검증하는 실험이다.
2. 비교 대상은 소수로 제한한다.
   - Fixed 70/20/10 BM
   - EW Benchmark
   - HSI baseline
   - Lambda 0.1
   - Lambda 0.3
3. HSI는 미래수익률 예측기가 아니라 시장상태 번역기다.
4. 상태별 분석은 실제 연속 운용 경로가 아니라, 해당 HSI 상태 월만 모아 본 조건부 진단표로 해석한다.

입력
----
data/processed/main_final_baseline_rebalance_weights.csv
 또는 data/processed/main_final_hsi_state5_baseline_weights.csv

data/processed/main_final_monthly_return_decimal.csv
 또는 data/processed/main_final_monthly_return_pct.csv

출력
----
output/tables/main_final_benchmark_alignment_summary.csv
output/tables/main_final_benchmark_alignment_by_period.csv
output/tables/main_final_benchmark_alignment_by_hsi_state.csv
output/tables/main_final_benchmark_alignment_tail_event_summary.csv
output/tables/main_final_benchmark_alignment_tail_months.csv
output/tables/main_final_benchmark_alignment_decision_note.csv

output/figures/main_final_benchmark_alignment_period_cagr.png
output/figures/main_final_benchmark_alignment_period_mdd.png
output/figures/main_final_benchmark_alignment_state_avg_return_heatmap.png

docs/main_final_benchmark_alignment_note.md
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# 0. 설정
# ============================================================

@dataclass(frozen=True)
class Config:
    risk_asset: str = "069500"
    bond_asset: str = "114260"
    cash_asset: str = "153130"

    lambdas: tuple[float, ...] = (0.1, 0.3)
    periods_per_year: int = 12

    # 큰 손실월 기준: 위험자산 069500 월별 수익률 하위 10%
    tail_quantile: float = 0.10

    # 기간 구간. 데이터가 없는 구간은 자동으로 제외된다.
    period_bins: tuple[tuple[str, str, str], ...] = (
        ("2012-2015", "2012-01-01", "2015-12-31"),
        ("2016-2019", "2016-01-01", "2019-12-31"),
        ("2020-2022", "2020-01-01", "2022-12-31"),
        ("2023-2026", "2023-01-01", "2026-12-31"),
    )


CFG = Config()

STRATEGY_ORDER = [
    "Fixed 70/20/10 BM",
    "EW Benchmark",
    "HSI baseline",
    "Lambda 0.1",
    "Lambda 0.3",
]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUT_TABLES = PROJECT_ROOT / "output" / "tables"
OUTPUT_FIGURES = PROJECT_ROOT / "output" / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"

BASELINE_WEIGHT_CANDIDATES = [
    DATA_PROCESSED / "main_final_baseline_rebalance_weights.csv",
    DATA_PROCESSED / "main_final_hsi_state5_baseline_weights.csv",
    DATA_PROCESSED / "main_final_baseline_weights.csv",
]

RETURN_CANDIDATES = [
    DATA_PROCESSED / "main_final_monthly_return_decimal.csv",
    DATA_PROCESSED / "main_final_monthly_returns_decimal.csv",
    DATA_PROCESSED / "main_final_monthly_return_pct.csv",
]

OUTPUT_STRATEGY_TS = DATA_PROCESSED / "main_final_benchmark_alignment_strategy_timeseries.csv"
OUTPUT_SUMMARY = OUTPUT_TABLES / "main_final_benchmark_alignment_summary.csv"
OUTPUT_BY_PERIOD = OUTPUT_TABLES / "main_final_benchmark_alignment_by_period.csv"
OUTPUT_BY_STATE = OUTPUT_TABLES / "main_final_benchmark_alignment_by_hsi_state.csv"
OUTPUT_TAIL_SUMMARY = OUTPUT_TABLES / "main_final_benchmark_alignment_tail_event_summary.csv"
OUTPUT_TAIL_MONTHS = OUTPUT_TABLES / "main_final_benchmark_alignment_tail_months.csv"
OUTPUT_DECISION = OUTPUT_TABLES / "main_final_benchmark_alignment_decision_note.csv"

OUTPUT_FIG_PERIOD_CAGR = OUTPUT_FIGURES / "main_final_benchmark_alignment_period_cagr.png"
OUTPUT_FIG_PERIOD_MDD = OUTPUT_FIGURES / "main_final_benchmark_alignment_period_mdd.png"
OUTPUT_FIG_STATE_HEATMAP = OUTPUT_FIGURES / "main_final_benchmark_alignment_state_avg_return_heatmap.png"
OUTPUT_NOTE = DOCS_DIR / "main_final_benchmark_alignment_note.md"


# ============================================================
# 1. 공통 유틸
# ============================================================

def ensure_dirs() -> None:
    for p in [DATA_PROCESSED, OUTPUT_TABLES, OUTPUT_FIGURES, DOCS_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def first_existing(paths: list[Path]) -> Path:
    for p in paths:
        if p.exists():
            return p
    raise FileNotFoundError("입력 후보 파일을 찾지 못했습니다:\n" + "\n".join(map(str, paths)))


def read_csv_safely(path: Path) -> pd.DataFrame:
    for enc in ["utf-8-sig", "utf-8", "cp949"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def parse_month(s: pd.Series) -> pd.Series:
    text = s.astype(str).str.strip()
    parsed = pd.to_datetime(text, errors="coerce")

    # 2025-07 형식 보정
    need_fix = parsed.isna() & text.str.match(r"^\d{4}-\d{1,2}$", na=False)
    if need_fix.any():
        parsed.loc[need_fix] = pd.to_datetime(text.loc[need_fix] + "-01", errors="coerce")

    return parsed.dt.to_period("M").dt.to_timestamp("M")


def find_date_col(df: pd.DataFrame, prefer_return_month: bool = False) -> str:
    if prefer_return_month:
        candidates = [
            "return_year_month", "return_month", "Date", "date", "month", "Month",
            "year_month", "YearMonth", "Unnamed: 0",
        ]
    else:
        candidates = [
            "year_month", "signal_month", "Date", "date", "month", "Month",
            "return_year_month", "return_month", "YearMonth", "Unnamed: 0",
        ]

    for c in candidates:
        if c in df.columns:
            return c

    for c in df.columns:
        parsed = pd.to_datetime(df[c], errors="coerce")
        if parsed.notna().mean() > 0.80:
            return c

    raise ValueError(f"날짜 컬럼을 찾지 못했습니다. columns={list(df.columns)}")


def find_col_by_ticker(df: pd.DataFrame, ticker: str, kind: str) -> str:
    if kind == "weight":
        candidates = [
            f"base_weight_{ticker}", f"target_weight_{ticker}", f"weight_{ticker}",
            f"base_w_{ticker}", f"target_w_{ticker}", f"w_{ticker}", ticker,
            f"{ticker}.KS", f"{ticker}_weight",
        ]
        reject_words = ["return", "ret"]
    else:
        candidates = [
            f"return_{ticker}", f"ret_{ticker}", f"monthly_return_{ticker}",
            f"{ticker}_return", f"{ticker}.KS", ticker,
        ]
        reject_words = ["weight", "w_"]

    for c in candidates:
        if c in df.columns:
            return c

    contains = []
    for c in df.columns:
        name = str(c)
        if ticker not in name:
            continue
        lowered = name.lower()
        if any(w in lowered for w in reject_words):
            continue
        contains.append(c)

    if contains:
        return contains[0]

    raise ValueError(f"{ticker} {kind} 컬럼을 찾지 못했습니다. columns={list(df.columns)}")


def find_state_col(df: pd.DataFrame) -> str | None:
    candidates = [
        "hsi_state", "hsi_state5", "state5", "state", "hsi_regime",
        "regime", "hsi_state_label",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def normalize_weight_units(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    max_abs = out[cols].abs().max().max()
    if pd.notna(max_abs) and max_abs > 1.5:
        out[cols] = out[cols] / 100.0
    return out


def normalize_return_units(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    max_abs = out[cols].abs().max().max()
    if pd.notna(max_abs) and max_abs > 1.0:
        out[cols] = out[cols] / 100.0
    return out


def safe_div(a: float, b: float) -> float:
    if b == 0 or pd.isna(b):
        return np.nan
    return a / b


# ============================================================
# 2. 입력 로드 및 전략 수익률 생성
# ============================================================

def load_target_weights() -> pd.DataFrame:
    path = first_existing(BASELINE_WEIGHT_CANDIDATES)
    df = read_csv_safely(path)

    signal_col = find_date_col(df, prefer_return_month=False)
    df["signal_month"] = parse_month(df[signal_col])

    if "return_year_month" in df.columns:
        df["return_month"] = parse_month(df["return_year_month"])
    elif "return_month" in df.columns:
        df["return_month"] = parse_month(df["return_month"])
    else:
        warnings.warn(
            "baseline weights에 return_year_month가 없어 signal_month를 return_month로 사용합니다. "
            "월말 신호→다음월 수익률 정렬이 이미 반영되어 있는지 확인하세요.",
            RuntimeWarning,
        )
        df["return_month"] = df["signal_month"]

    w_risk = find_col_by_ticker(df, CFG.risk_asset, "weight")
    w_bond = find_col_by_ticker(df, CFG.bond_asset, "weight")
    w_cash = find_col_by_ticker(df, CFG.cash_asset, "weight")

    state_col = find_state_col(df)

    keep = ["signal_month", "return_month", w_risk, w_bond, w_cash]
    if state_col is not None:
        keep.append(state_col)

    out = df[keep].copy()
    out = out.rename(
        columns={
            w_risk: "target_w_069500",
            w_bond: "target_w_114260",
            w_cash: "target_w_153130",
        }
    )
    if state_col is not None:
        out = out.rename(columns={state_col: "hsi_state"})
    else:
        out["hsi_state"] = "unknown"

    out = normalize_weight_units(out, ["target_w_069500", "target_w_114260", "target_w_153130"])
    out = out.dropna(subset=["signal_month", "return_month"])
    out = out.drop_duplicates("signal_month").sort_values("signal_month").reset_index(drop=True)

    return out


def load_monthly_returns() -> pd.DataFrame:
    path = first_existing(RETURN_CANDIDATES)
    df = read_csv_safely(path)

    date_col = find_date_col(df, prefer_return_month=True)
    df["return_month"] = parse_month(df[date_col])

    r_risk = find_col_by_ticker(df, CFG.risk_asset, "return")
    r_bond = find_col_by_ticker(df, CFG.bond_asset, "return")
    r_cash = find_col_by_ticker(df, CFG.cash_asset, "return")

    out = df[["return_month", r_risk, r_bond, r_cash]].copy()
    out = out.rename(
        columns={
            r_risk: "ret_069500",
            r_bond: "ret_114260",
            r_cash: "ret_153130",
        }
    )
    out = normalize_return_units(out, ["ret_069500", "ret_114260", "ret_153130"])
    out = out.dropna(subset=["return_month"])
    out = out.drop_duplicates("return_month").sort_values("return_month").reset_index(drop=True)

    return out


def apply_lambda_weights(target: pd.DataFrame, lam: float) -> pd.DataFrame:
    df = target.copy().sort_values("signal_month").reset_index(drop=True)

    target_cols = ["target_w_069500", "target_w_114260", "target_w_153130"]
    actual_rows = []

    for i, row in df.iterrows():
        target_w = row[target_cols].astype(float).to_numpy()
        if i == 0:
            current_w = target_w
        else:
            prev_w = actual_rows[-1]
            current_w = prev_w + lam * (target_w - prev_w)
        current_w = np.clip(current_w, 0.0, 1.0)
        current_w = current_w / current_w.sum()
        actual_rows.append(current_w)

    arr = np.vstack(actual_rows)
    df["weight_069500"] = arr[:, 0]
    df["weight_114260"] = arr[:, 1]
    df["weight_153130"] = arr[:, 2]

    return df


def baseline_weights(target: pd.DataFrame) -> pd.DataFrame:
    df = target.copy()
    df = df.rename(
        columns={
            "target_w_069500": "weight_069500",
            "target_w_114260": "weight_114260",
            "target_w_153130": "weight_153130",
        }
    )
    return df


def ew_weights(target: pd.DataFrame) -> pd.DataFrame:
    df = target[["signal_month", "return_month", "hsi_state"]].copy()
    df["weight_069500"] = 1.0 / 3.0
    df["weight_114260"] = 1.0 / 3.0
    df["weight_153130"] = 1.0 / 3.0
    return df


def fixed_70_20_10_weights(target: pd.DataFrame) -> pd.DataFrame:
    """
    메인 BM: 동일 ETF 유니버스를 전략적 기준비중 70/20/10으로 고정 보유한다.

    역할
    ----
    ETF 선택 자체에서 발생하는 성과와 HSI·Lambda 기반 동적 비중조절에서
    발생하는 성과를 구분하기 위한 전략적 자산배분 기준선이다.
    """
    df = target[["signal_month", "return_month", "hsi_state"]].copy()
    df["weight_069500"] = 0.70
    df["weight_114260"] = 0.20
    df["weight_153130"] = 0.10
    return df


def calculate_turnover(df: pd.DataFrame) -> pd.Series:
    weight_cols = ["weight_069500", "weight_114260", "weight_153130"]
    diff = df[weight_cols].diff().abs()
    turnover = 0.5 * diff.sum(axis=1)
    turnover.iloc[0] = 0.0
    return turnover.fillna(0.0)


def attach_returns(weights: pd.DataFrame, returns: pd.DataFrame, strategy_name: str) -> pd.DataFrame:
    df = weights.merge(returns, on="return_month", how="inner").sort_values("return_month")
    if df.empty:
        raise ValueError(f"{strategy_name}: weights와 returns의 return_month가 겹치지 않습니다.")

    df["strategy_return"] = (
        df["weight_069500"] * df["ret_069500"]
        + df["weight_114260"] * df["ret_114260"]
        + df["weight_153130"] * df["ret_153130"]
    )
    df["turnover"] = calculate_turnover(df)
    df["strategy_name"] = strategy_name
    df["cum_return"] = (1.0 + df["strategy_return"]).cumprod()
    df["drawdown"] = df["cum_return"] / df["cum_return"].cummax() - 1.0

    return df


def build_strategy_timeseries() -> pd.DataFrame:
    target = load_target_weights()
    returns = load_monthly_returns()

    strategies = []
    strategies.append(attach_returns(fixed_70_20_10_weights(target), returns, "Fixed 70/20/10 BM"))
    strategies.append(attach_returns(ew_weights(target), returns, "EW Benchmark"))
    strategies.append(attach_returns(baseline_weights(target), returns, "HSI baseline"))

    for lam in CFG.lambdas:
        strategies.append(
            attach_returns(
                apply_lambda_weights(target, lam),
                returns,
                f"Lambda {lam:.1f}",
            )
        )

    return pd.concat(strategies, ignore_index=True)


# ============================================================
# 3. 성과 지표
# ============================================================

def annualized_cagr(cum_end: float, dates: pd.Series) -> float:
    if len(dates) <= 1:
        return np.nan
    start = pd.to_datetime(dates.iloc[0])
    end = pd.to_datetime(dates.iloc[-1])
    years = (end - start).days / 365.25
    if years <= 0:
        years = len(dates) / CFG.periods_per_year
    return cum_end ** (1.0 / years) - 1.0


def performance_metrics(sub: pd.DataFrame, annualize: bool = True) -> dict:
    sub = sub.sort_values("return_month").copy()
    r = pd.to_numeric(sub["strategy_return"], errors="coerce").fillna(0.0)
    turnover = pd.to_numeric(sub["turnover"], errors="coerce").fillna(0.0)

    cum = (1.0 + r).cumprod()
    dd = cum / cum.cummax() - 1.0

    if annualize:
        cagr = annualized_cagr(float(cum.iloc[-1]), sub["return_month"])
        ann_vol = r.std(ddof=1) * np.sqrt(CFG.periods_per_year)
        sharpe = safe_div(r.mean() * CFG.periods_per_year, ann_vol)
    else:
        # 상태별 분석처럼 비연속 월을 모을 때는 CAGR보다 평균 월수익률 중심으로 해석한다.
        cagr = np.nan
        ann_vol = r.std(ddof=1) * np.sqrt(CFG.periods_per_year)
        sharpe = safe_div(r.mean() * CFG.periods_per_year, ann_vol)

    mdd = float(dd.min()) if len(dd) else np.nan
    calmar = safe_div(cagr, abs(mdd)) if annualize else np.nan

    return {
        "months": int(len(sub)),
        "start_month": pd.to_datetime(sub["return_month"].iloc[0]).strftime("%Y-%m") if len(sub) else None,
        "end_month": pd.to_datetime(sub["return_month"].iloc[-1]).strftime("%Y-%m") if len(sub) else None,
        "final_cumulative_return": float(cum.iloc[-1]) if len(cum) else np.nan,
        "CAGR_pct": cagr * 100 if pd.notna(cagr) else np.nan,
        "annual_volatility_pct": ann_vol * 100 if pd.notna(ann_vol) else np.nan,
        "MDD_pct": mdd * 100 if pd.notna(mdd) else np.nan,
        "abs_MDD_pct": abs(mdd) * 100 if pd.notna(mdd) else np.nan,
        "Sharpe": sharpe,
        "Calmar": calmar,
        "WinRate_pct": float((r > 0).mean() * 100) if len(r) else np.nan,
        "avg_monthly_return_pct": float(r.mean() * 100) if len(r) else np.nan,
        "median_monthly_return_pct": float(r.median() * 100) if len(r) else np.nan,
        "best_month_pct": float(r.max() * 100) if len(r) else np.nan,
        "worst_month_pct": float(r.min() * 100) if len(r) else np.nan,
        "avg_turnover_pct": float(turnover.mean() * 100) if len(turnover) else np.nan,
        "max_turnover_pct": float(turnover.max() * 100) if len(turnover) else np.nan,
    }


def build_overall_summary(ts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy, sub in ts.groupby("strategy_name"):
        row = {"strategy_name": strategy}
        row.update(performance_metrics(sub, annualize=True))
        rows.append(row)

    summary = pd.DataFrame(rows)

    # 비교군 역할 구분
    summary["role"] = np.select(
        [
            summary["strategy_name"].isin(["Fixed 70/20/10 BM", "EW Benchmark"]),
            summary["strategy_name"].eq("HSI baseline"),
            summary["strategy_name"].str.startswith("Lambda"),
        ],
        ["benchmark", "baseline", "candidate"],
        default="other",
    )
    summary["strategy_name"] = pd.Categorical(summary["strategy_name"], categories=STRATEGY_ORDER, ordered=True)
    summary = summary.sort_values("strategy_name").reset_index(drop=True)
    summary["strategy_name"] = summary["strategy_name"].astype(str)
    return summary


def assign_period(month: pd.Timestamp) -> str | None:
    for label, start, end in CFG.period_bins:
        if pd.Timestamp(start) <= month <= pd.Timestamp(end):
            return label
    return None


def build_by_period(ts: pd.DataFrame) -> pd.DataFrame:
    df = ts.copy()
    df["period"] = df["return_month"].apply(assign_period)
    df = df[df["period"].notna()].copy()

    rows = []
    for (period, strategy), sub in df.groupby(["period", "strategy_name"]):
        row = {"period": period, "strategy_name": strategy}
        row.update(performance_metrics(sub, annualize=True))
        rows.append(row)

    out = pd.DataFrame(rows)
    order = [x[0] for x in CFG.period_bins]
    out["period"] = pd.Categorical(out["period"], categories=order, ordered=True)
    out["strategy_name"] = pd.Categorical(out["strategy_name"], categories=STRATEGY_ORDER, ordered=True)
    out = out.sort_values(["period", "strategy_name"]).reset_index(drop=True)
    out["strategy_name"] = out["strategy_name"].astype(str)
    return out


def build_by_state(ts: pd.DataFrame) -> pd.DataFrame:
    df = ts.copy()
    df["hsi_state"] = df["hsi_state"].fillna("unknown")

    rows = []
    for (state, strategy), sub in df.groupby(["hsi_state", "strategy_name"]):
        row = {"hsi_state": state, "strategy_name": strategy}
        row.update(performance_metrics(sub, annualize=False))
        rows.append(row)

    out = pd.DataFrame(rows)
    state_order = [
        "risk_relief",
        "neutral_watch",
        "conflict",
        "risk_warning",
        "accident_zone",
        "insufficient_data",
        "unknown",
    ]
    out["hsi_state"] = pd.Categorical(out["hsi_state"], categories=state_order, ordered=True)
    return out.sort_values(["hsi_state", "strategy_name"]).reset_index(drop=True)


def build_tail_tables(ts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = ts[ts["strategy_name"].eq("EW Benchmark")][
        ["return_month", "ret_069500", "hsi_state"]
    ].drop_duplicates("return_month")

    cutoff = base["ret_069500"].quantile(CFG.tail_quantile)
    tail_months = base[base["ret_069500"] <= cutoff].copy()
    tail_months["tail_event_type"] = f"069500_bottom_{int(CFG.tail_quantile * 100)}pct"

    merged = ts.merge(
        tail_months[["return_month", "tail_event_type"]],
        on="return_month",
        how="inner",
    )

    # 월별 상세표: 각 꼬리월에 전략별 수익률을 펼쳐서 저장
    detail = merged[
        [
            "return_month",
            "tail_event_type",
            "hsi_state",
            "strategy_name",
            "ret_069500",
            "strategy_return",
            "turnover",
            "weight_069500",
            "weight_114260",
            "weight_153130",
        ]
    ].copy()
    detail["return_month"] = detail["return_month"].dt.strftime("%Y-%m")
    detail["ret_069500_pct"] = detail["ret_069500"] * 100
    detail["strategy_return_pct"] = detail["strategy_return"] * 100
    detail["turnover_pct"] = detail["turnover"] * 100

    summary_rows = []
    for strategy, sub in merged.groupby("strategy_name"):
        r = pd.to_numeric(sub["strategy_return"], errors="coerce")
        summary_rows.append(
            {
                "tail_event_type": f"069500_bottom_{int(CFG.tail_quantile * 100)}pct",
                "strategy_name": strategy,
                "tail_months": int(len(sub)),
                "avg_tail_month_return_pct": float(r.mean() * 100),
                "median_tail_month_return_pct": float(r.median() * 100),
                "worst_tail_month_return_pct": float(r.min() * 100),
                "best_tail_month_return_pct": float(r.max() * 100),
                "win_rate_in_tail_pct": float((r > 0).mean() * 100),
                "avg_weight_069500_pct": float(sub["weight_069500"].mean() * 100),
                "avg_turnover_pct": float(sub["turnover"].mean() * 100),
            }
        )

    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        summary["strategy_name"] = pd.Categorical(summary["strategy_name"], categories=STRATEGY_ORDER, ordered=True)
        summary = summary.sort_values("strategy_name").reset_index(drop=True)
        summary["strategy_name"] = summary["strategy_name"].astype(str)
    return summary, detail


# ============================================================
# 4. 판단 보조표 및 그림
# ============================================================

def build_decision_note(summary: pd.DataFrame, by_period: pd.DataFrame, by_state: pd.DataFrame, tail_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []

    lambda_rows = summary[summary["strategy_name"].str.startswith("Lambda")].copy()
    if not lambda_rows.empty:
        best_calmar = lambda_rows.sort_values("Calmar", ascending=False).iloc[0]
        best_turnover = lambda_rows.sort_values("avg_turnover_pct", ascending=True).iloc[0]
        best_cagr = lambda_rows.sort_values("CAGR_pct", ascending=False).iloc[0]

        rows.extend(
            [
                {
                    "topic": "overall_calmar",
                    "finding": f"전체 기간 Calmar 기준 우위 Lambda 후보는 {best_calmar['strategy_name']}입니다.",
                    "value": float(best_calmar["Calmar"]),
                },
                {
                    "topic": "overall_turnover",
                    "finding": f"전체 기간 평균 Turnover가 낮은 Lambda 후보는 {best_turnover['strategy_name']}입니다.",
                    "value": float(best_turnover["avg_turnover_pct"]),
                },
                {
                    "topic": "overall_cagr",
                    "finding": f"전체 기간 CAGR이 높은 Lambda 후보는 {best_cagr['strategy_name']}입니다.",
                    "value": float(best_cagr["CAGR_pct"]),
                },
            ]
        )

    fixed = summary[summary["strategy_name"].eq("Fixed 70/20/10 BM")].copy()
    if not fixed.empty and not lambda_rows.empty:
        fixed_row = fixed.iloc[0]
        for _, row in lambda_rows.iterrows():
            rows.append(
                {
                    "topic": f"vs_fixed_bm_{row['strategy_name']}",
                    "finding": (
                        f"{row['strategy_name']}는 Fixed 70/20/10 BM 대비 "
                        f"CAGR {row['CAGR_pct'] - fixed_row['CAGR_pct']:.3f}%p, "
                        f"MDD {row['MDD_pct'] - fixed_row['MDD_pct']:.3f}%p, "
                        f"Calmar {row['Calmar'] - fixed_row['Calmar']:.3f} 차이를 보입니다."
                    ),
                    "value": float(row["CAGR_pct"] - fixed_row["CAGR_pct"]),
                }
            )

    # 기간별 MDD가 가장 낮은 전략 카운트
    period_counts = []
    for period, sub in by_period.groupby("period"):
        valid = sub[sub["strategy_name"].str.startswith("Lambda")].copy()
        if valid.empty:
            continue
        winner = valid.sort_values("abs_MDD_pct", ascending=True).iloc[0]["strategy_name"]
        period_counts.append(winner)

    if period_counts:
        counts = pd.Series(period_counts).value_counts()
        rows.append(
            {
                "topic": "period_mdd_count",
                "finding": "기간별 abs MDD 기준 Lambda 우위 횟수: " + ", ".join([f"{k}={v}" for k, v in counts.items()]),
                "value": np.nan,
            }
        )

    # Tail event 방어력
    tail_lambda = tail_summary[tail_summary["strategy_name"].str.startswith("Lambda")].copy()
    if not tail_lambda.empty:
        best_tail = tail_lambda.sort_values("avg_tail_month_return_pct", ascending=False).iloc[0]
        rows.append(
            {
                "topic": "tail_event_avg_return",
                "finding": f"069500 하위 10% 손실월 평균 수익률이 가장 나은 Lambda 후보는 {best_tail['strategy_name']}입니다.",
                "value": float(best_tail["avg_tail_month_return_pct"]),
            }
        )

    return pd.DataFrame(rows)


def plot_period_metric(by_period: pd.DataFrame, metric: str, output_path: Path, title: str, ylabel: str) -> None:
    pivot = by_period.pivot(index="period", columns="strategy_name", values=metric)
    pivot = pivot[[c for c in STRATEGY_ORDER if c in pivot.columns]]

    ax = pivot.plot(kind="bar", figsize=(11, 5))
    ax.set_title(title)
    ax.set_xlabel("Period")
    ax.set_ylabel(ylabel)
    ax.legend(loc="best")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def plot_state_heatmap(by_state: pd.DataFrame) -> None:
    pivot = by_state.pivot(index="hsi_state", columns="strategy_name", values="avg_monthly_return_pct")
    cols = [c for c in STRATEGY_ORDER if c in pivot.columns]
    pivot = pivot[cols]
    pivot = pivot.dropna(how="all")

    fig, ax = plt.subplots(figsize=(10, 5))
    im = ax.imshow(pivot.values, aspect="auto")
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=30, ha="right")
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels([str(x) for x in pivot.index])
    ax.set_title("Average monthly return by HSI state")

    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.iloc[i, j]
            if pd.notna(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8)

    fig.colorbar(im, ax=ax, label="Avg monthly return (%)")
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG_STATE_HEATMAP, dpi=180)
    plt.close()



def dataframe_to_markdown_simple(df: pd.DataFrame) -> str:
    """
    pandas.DataFrame.to_markdown()은 선택 패키지 tabulate가 필요하다.
    수업/프로젝트 실행환경에서 추가 설치 없이 Markdown 표를 만들기 위해
    간단한 자체 변환 함수를 사용한다.
    """
    if df.empty:
        return "_표시할 데이터가 없습니다._"

    safe = df.copy()

    for col in safe.columns:
        if pd.api.types.is_float_dtype(safe[col]):
            safe[col] = safe[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
        else:
            safe[col] = safe[col].map(lambda x: "" if pd.isna(x) else str(x))

    headers = [str(c) for c in safe.columns]
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for _, row in safe.iterrows():
        values = [str(row[c]).replace("\n", " ") for c in safe.columns]
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)

def write_note(summary: pd.DataFrame, by_period: pd.DataFrame, by_state: pd.DataFrame, tail_summary: pd.DataFrame, decision: pd.DataFrame) -> None:
    summary_show = summary[
        ["strategy_name", "CAGR_pct", "MDD_pct", "Sharpe", "Calmar", "avg_turnover_pct"]
    ].copy()

    top_calmar = summary[summary["strategy_name"].str.startswith("Lambda")].sort_values("Calmar", ascending=False).iloc[0]
    low_turnover = summary[summary["strategy_name"].str.startswith("Lambda")].sort_values("avg_turnover_pct", ascending=True).iloc[0]

    text = f"""# 16번 Benchmark Alignment Check Note

## 1. 실험 목적

17번은 강사님 RA 개발 기준에 맞춰 메인 BM인 Fixed 70/20/10 BM을 비교표에 추가하고, EW Benchmark·HSI baseline·Lambda 후보와 같은 기준으로 정렬하는 검증 실험이다.

```text
질문: Fixed 70/20/10 BM과 EW Benchmark를 함께 놓았을 때, Lambda 후보의 개선이 ETF 선택 효과인지 동적 비중조절 효과인지 구분되는가?
```

## 2. 비교 대상

```text
Fixed 70/20/10 BM
EW Benchmark
HSI baseline
Lambda 0.1
Lambda 0.3
```

## 3. 전체 기간 요약

{dataframe_to_markdown_simple(summary_show)}

전체 기간 Calmar 기준 Lambda 후보 중 우위는 **{top_calmar['strategy_name']}**이다.  
전체 기간 평균 Turnover 기준으로 더 보수적인 후보는 **{low_turnover['strategy_name']}**이다.

## 4. 해석 원칙

상태별 분석은 실제 연속 운용 경로가 아니라, 해당 HSI 상태가 관측된 월만 모아 본 조건부 진단표이다. 따라서 상태별 표에서는 CAGR보다 평균 월수익률, 최악 월수익률, 승률, 평균 Turnover를 중심으로 해석한다.

## 5. 보고서 문장 초안

BM 정렬 검토에서는 메인 BM인 Fixed 70/20/10 BM, 보조 BM인 EW Benchmark, 내부 기준선인 HSI baseline, 최종 후보인 Lambda 0.1과 Lambda 0.3을 같은 표에서 비교하였다. 이는 전략 성과가 ETF 유니버스 선택 자체에서 나온 것인지, HSI와 Lambda를 이용한 동적 비중조절에서 나온 것인지 구분하기 위한 절차이다. 분석 결과가 모든 지표에서 한 후보의 절대적 우월성을 보장하지 않더라도, Lambda 부분조정이 HSI baseline의 급격한 비중 전환과 Turnover 부담을 완화하는 구조적 역할을 하는지 확인하는 데 의미가 있다.

## 6. 산출물

```text
output/tables/main_final_benchmark_alignment_summary.csv
output/tables/main_final_benchmark_alignment_by_period.csv
output/tables/main_final_benchmark_alignment_by_hsi_state.csv
output/tables/main_final_benchmark_alignment_tail_event_summary.csv
output/tables/main_final_benchmark_alignment_tail_months.csv
output/tables/main_final_benchmark_alignment_decision_note.csv
```
"""
    OUTPUT_NOTE.write_text(text, encoding="utf-8-sig")


# ============================================================
# 5. main
# ============================================================

def main() -> None:
    ensure_dirs()

    print("=" * 80)
    print("17_benchmark_alignment_check.py 실행 시작")
    print("=" * 80)

    print("[1] 전략별 월별 수익률 생성")
    ts = build_strategy_timeseries()
    print(f"    strategy timeseries shape = {ts.shape}")
    print(f"    strategies = {[s for s in STRATEGY_ORDER if s in ts['strategy_name'].unique().tolist()]}")

    print("[2] 전체 기간 성과표 계산")
    summary = build_overall_summary(ts)

    print("[3] 기간별 robustness 계산")
    by_period = build_by_period(ts)

    print("[4] HSI 상태별 조건부 진단 계산")
    by_state = build_by_state(ts)

    print("[5] 큰 손실월 진단 계산")
    tail_summary, tail_months = build_tail_tables(ts)

    print("[6] 판단 보조표 계산")
    decision = build_decision_note(summary, by_period, by_state, tail_summary)

    print("[7] 저장")
    ts.to_csv(OUTPUT_STRATEGY_TS, index=False, encoding="utf-8-sig")
    summary.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8-sig")
    by_period.to_csv(OUTPUT_BY_PERIOD, index=False, encoding="utf-8-sig")
    by_state.to_csv(OUTPUT_BY_STATE, index=False, encoding="utf-8-sig")
    tail_summary.to_csv(OUTPUT_TAIL_SUMMARY, index=False, encoding="utf-8-sig")
    tail_months.to_csv(OUTPUT_TAIL_MONTHS, index=False, encoding="utf-8-sig")
    decision.to_csv(OUTPUT_DECISION, index=False, encoding="utf-8-sig")

    print("[8] 그림 저장")
    plot_period_metric(
        by_period,
        metric="CAGR_pct",
        output_path=OUTPUT_FIG_PERIOD_CAGR,
        title="Benchmark alignment by period: CAGR",
        ylabel="CAGR (%)",
    )
    plot_period_metric(
        by_period,
        metric="MDD_pct",
        output_path=OUTPUT_FIG_PERIOD_MDD,
        title="Benchmark alignment by period: MDD",
        ylabel="MDD (%)",
    )
    plot_state_heatmap(by_state)

    print("[9] Markdown 노트 저장")
    write_note(summary, by_period, by_state, tail_summary, decision)

    print("\n[전체 기간 성과 요약]")
    print(
        summary[
            [
                "strategy_name", "CAGR_pct", "MDD_pct", "Sharpe", "Calmar",
                "avg_turnover_pct", "role",
            ]
        ].to_string(index=False)
    )

    print("\n[판단 보조 메모]")
    print(decision.to_string(index=False))

    print("\n[저장 파일]")
    for p in [
        OUTPUT_SUMMARY, OUTPUT_BY_PERIOD, OUTPUT_BY_STATE, OUTPUT_TAIL_SUMMARY,
        OUTPUT_TAIL_MONTHS, OUTPUT_DECISION, OUTPUT_NOTE,
    ]:
        print(f"    저장: {p}")

    print("=" * 80)
    print("17_benchmark_alignment_check.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
