"""
20_select_final_candidates_with_cost_and_turnover.py

목적
----
00~11번 실험에서 생성된 백테스트 시계열을 한곳에 모아
Turnover 필터, 거래비용 민감도, MDD/Calmar/Sharpe 기준을 적용하고
최종 후보군을 선별한다.

핵심 원칙
---------
1. 최고 CAGR 하나만으로 후보를 고르지 않는다.
2. Turnover가 과도한 후보는 먼저 제외하거나 보류한다.
3. 거래비용은 월별 Turnover × 거래비용률로 단순 차감한다.
4. 비용 반영 후 CAGR, MDD, Sharpe, Calmar를 다시 계산한다.
5. 최종 후보는 성과, 위험관리, 비용 민감도, 안정성 조건을 함께 본다.

입력
----
data/processed/main_final_*backtest_timeseries.csv

예시 입력 파일
-------------
main_final_baseline_backtest_timeseries.csv
main_final_signal_combo_backtest_timeseries.csv
main_final_event_balance_filter_backtest_timeseries.csv
main_final_lambda_backtest_timeseries.csv
main_final_theta_backtest_timeseries.csv

출력
----
output/tables/main_final_candidate_source_inventory.csv
output/tables/main_final_candidate_all_cost_sensitivity.csv
output/tables/main_final_candidate_turnover_filtered.csv
output/tables/main_final_candidate_final_judgement.csv
output/tables/main_final_candidate_selection_summary.csv

docs/main_final_candidate_selection_note.md
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

import final_project_config as cfg


# ============================================================
# 1. 경로와 설정
# ============================================================

BACKTEST_GLOB = "main_final_*backtest_timeseries.csv"

OUTPUT_SOURCE_INVENTORY = cfg.TABLE_DIR / "main_final_candidate_source_inventory.csv"
OUTPUT_ALL_COST = cfg.TABLE_DIR / "main_final_candidate_all_cost_sensitivity.csv"
OUTPUT_TURNOVER_FILTERED = cfg.TABLE_DIR / "main_final_candidate_turnover_filtered.csv"
OUTPUT_FINAL_JUDGEMENT = cfg.TABLE_DIR / "main_final_candidate_final_judgement.csv"
OUTPUT_SELECTION_SUMMARY = cfg.TABLE_DIR / "main_final_candidate_selection_summary.csv"
OUTPUT_NOTE = cfg.DOCS_DIR / "experiment_notes" / "main_final_candidate_selection_note.md"

YEAR_MONTH_COL = "year_month"
RETURN_YEAR_MONTH_COL = "return_year_month"

# 거래비용률 후보
# 0.0005 = 0.05%, 0.0010 = 0.10%, 0.0020 = 0.20%
COST_RATE_GRID = {
    "cost_0bp": 0.0000,
    "cost_5bp": 0.0005,
    "cost_10bp": 0.0010,
    "cost_20bp": 0.0020,
}

# 최종 판단에 사용할 대표 비용률
FINAL_COST_LABEL = "cost_10bp"
FINAL_COST_RATE = COST_RATE_GRID[FINAL_COST_LABEL]

# Turnover 후보 압축 기준
STRICT_AVG_TURNOVER_PCT = 10.0
STRICT_MAX_TURNOVER_PCT = 40.0
FLEX_AVG_TURNOVER_PCT = 15.0
FLEX_MAX_TURNOVER_PCT = 50.0

# 방어형 overlay 후보 판단 기준
MIN_MONTHS_RATIO = 0.90
MDD_WORSE_THAN_EW_ALLOWANCE_PCT = 3.0
MIN_SHARPE = 0.70
MIN_CALMAR = 0.45
MIN_CAGR_GAP_VS_EW_PCT = 0.0
MAX_COST_DRAG_20BP_PCT = 1.0

# 보고서에서 읽기 쉬운 컬럼 순서
KEY_PARAM_COLS = [
    "source_type",
    "source_file",
    "strategy_name",
    "combo_id",
    "combo_name",
    "theta_id",
    "theta_common",
    "lambda_value",
    "allocation_rule_name",
]


# ============================================================
# 2. 공통 유틸
# ============================================================

def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def infer_source_type(path: Path) -> str:
    stem = path.stem.lower()

    if "signal_combo" in stem:
        return "signal_combo"
    if "event_balance_filter" in stem:
        return "event_balance_filter"
    if "lambda" in stem:
        return "lambda"
    if "theta" in stem:
        return "theta"
    if "baseline" in stem:
        return "baseline"
    if "grid" in stem:
        return "grid"

    return "other"


def discover_backtest_files() -> list[Path]:
    files = sorted(cfg.PROCESSED_DIR.glob(BACKTEST_GLOB))

    # 이 파일이 반복 실행될 때 자신이 만든 산출물을 잘못 읽지 않도록 방지한다.
    excluded_keywords = [
        "candidate",
        "selection",
        "cost_sensitivity",
    ]

    filtered = []
    for path in files:
        lower = path.name.lower()
        if any(key in lower for key in excluded_keywords):
            continue
        filtered.append(path)

    return filtered


def ensure_required_columns(df: pd.DataFrame, path: Path) -> bool:
    required = {"strategy_name", "strategy_return", "turnover"}
    missing = required - set(df.columns)
    if missing:
        print(f"    SKIP: {path.name} 필수 컬럼 누락 {sorted(missing)}")
        return False
    return True


def normalize_timeseries(df: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    out = df.copy()
    out["source_file"] = source_path.name
    out["source_type"] = infer_source_type(source_path)
    out["source_stem"] = source_path.stem

    if YEAR_MONTH_COL not in out.columns:
        out[YEAR_MONTH_COL] = pd.NA

    if RETURN_YEAR_MONTH_COL not in out.columns:
        if YEAR_MONTH_COL in out.columns:
            out[RETURN_YEAR_MONTH_COL] = out[YEAR_MONTH_COL]
        else:
            out[RETURN_YEAR_MONTH_COL] = pd.NA

    out[YEAR_MONTH_COL] = out[YEAR_MONTH_COL].astype(str)
    out[RETURN_YEAR_MONTH_COL] = out[RETURN_YEAR_MONTH_COL].astype(str)

    out["strategy_name"] = out["strategy_name"].astype(str)
    out["strategy_return"] = pd.to_numeric(out["strategy_return"], errors="coerce")
    out["turnover"] = pd.to_numeric(out["turnover"], errors="coerce").fillna(0.0)

    # 후보 식별자가 중복되지 않도록 source_file을 포함한다.
    out["candidate_key"] = out["source_stem"] + "|" + out["strategy_name"]

    # 주요 파라미터 컬럼이 없으면 빈 컬럼으로 맞춘다.
    for col in KEY_PARAM_COLS:
        if col not in out.columns:
            out[col] = np.nan

    return out


# ============================================================
# 3. 성과지표 계산
# ============================================================

def calc_drawdown(returns: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    cumulative = (1.0 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = cumulative / running_max - 1.0
    return cumulative, running_max, drawdown


def calc_performance_from_returns(
    returns: pd.Series,
    turnover: pd.Series,
    *,
    cost_label: str,
    cost_rate: float,
) -> dict:
    r = pd.to_numeric(returns, errors="coerce")
    t = pd.to_numeric(turnover, errors="coerce").fillna(0.0)

    valid = r.notna()
    r = r[valid]
    t = t[valid]

    months = len(r)
    if months == 0:
        return {
            "cost_label": cost_label,
            "cost_rate": cost_rate,
            "months": 0,
        }

    trading_cost = t * cost_rate
    r_after_cost = r - trading_cost

    cumulative, _, drawdown = calc_drawdown(r_after_cost)

    final_cum = float(cumulative.iloc[-1])
    cagr = final_cum ** (12 / months) - 1 if months > 0 else np.nan
    ann_vol = r_after_cost.std(ddof=1) * np.sqrt(12) if months > 1 else np.nan
    ann_mean = r_after_cost.mean() * 12
    sharpe = ann_mean / ann_vol if pd.notna(ann_vol) and ann_vol != 0 else np.nan

    downside = r_after_cost[r_after_cost < 0]
    downside_vol = downside.std(ddof=1) * np.sqrt(12) if len(downside) > 1 else np.nan
    sortino = ann_mean / downside_vol if pd.notna(downside_vol) and downside_vol != 0 else np.nan

    mdd = drawdown.min()
    calmar = cagr / abs(mdd) if pd.notna(mdd) and mdd < 0 else np.nan

    return {
        "cost_label": cost_label,
        "cost_rate": cost_rate,
        "months": months,
        "final_cumulative_return": final_cum,
        "CAGR_pct": cagr * 100,
        "annual_volatility_pct": ann_vol * 100 if pd.notna(ann_vol) else np.nan,
        "MDD_pct": mdd * 100 if pd.notna(mdd) else np.nan,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Calmar": calmar,
        "WinRate_pct": (r_after_cost > 0).mean() * 100,
        "avg_monthly_return_pct": r_after_cost.mean() * 100,
        "best_month_pct": r_after_cost.max() * 100,
        "worst_month_pct": r_after_cost.min() * 100,
        "avg_turnover_pct": t.mean() * 100,
        "max_turnover_pct": t.max() * 100,
        "total_turnover_pct": t.sum() * 100,
        "total_trading_cost_pct": trading_cost.sum() * 100,
        "avg_monthly_trading_cost_pct": trading_cost.mean() * 100,
    }


def first_non_null(group: pd.DataFrame, col: str):
    if col not in group.columns:
        return np.nan
    s = group[col].dropna()
    if s.empty:
        return np.nan
    return s.iloc[0]


def build_cost_sensitivity_table(backtest_all: pd.DataFrame) -> pd.DataFrame:
    rows = []

    group_cols = ["candidate_key"]

    for candidate_key, group in backtest_all.groupby(group_cols[0]):
        g = group.sort_values([RETURN_YEAR_MONTH_COL, YEAR_MONTH_COL]).copy()

        base_info = {
            "candidate_key": candidate_key,
        }

        for col in KEY_PARAM_COLS:
            base_info[col] = first_non_null(g, col)

        # source_type/source_file은 항상 채운다.
        base_info["source_type"] = g["source_type"].iloc[0]
        base_info["source_file"] = g["source_file"].iloc[0]
        base_info["strategy_name"] = g["strategy_name"].iloc[0]

        for cost_label, cost_rate in COST_RATE_GRID.items():
            metrics = calc_performance_from_returns(
                g["strategy_return"],
                g["turnover"],
                cost_label=cost_label,
                cost_rate=cost_rate,
            )
            rows.append({**base_info, **metrics})

    result = pd.DataFrame(rows)
    return result


# ============================================================
# 4. 벤치마크와 비용 민감도 보조 컬럼
# ============================================================

def choose_ew_benchmark(cost_table: pd.DataFrame, cost_label: str) -> pd.Series | None:
    ew = cost_table[
        (cost_table["strategy_name"] == "EW")
        & (cost_table["cost_label"] == cost_label)
    ].copy()

    if ew.empty:
        return None

    # baseline 파일의 EW가 있으면 우선 사용한다.
    baseline_ew = ew[ew["source_type"] == "baseline"]
    if not baseline_ew.empty:
        return baseline_ew.iloc[0]

    return ew.iloc[0]


def add_cost_drag_columns(cost_table: pd.DataFrame) -> pd.DataFrame:
    base = cost_table.copy()

    zero = base[base["cost_label"] == "cost_0bp"][[
        "candidate_key",
        "CAGR_pct",
        "final_cumulative_return",
    ]].rename(columns={
        "CAGR_pct": "CAGR_0bp_pct",
        "final_cumulative_return": "final_cumulative_return_0bp",
    })

    out = base.merge(zero, on="candidate_key", how="left")
    out["CAGR_cost_drag_pct"] = out["CAGR_0bp_pct"] - out["CAGR_pct"]
    out["final_cum_cost_drag"] = out["final_cumulative_return_0bp"] - out["final_cumulative_return"]

    return out


# ============================================================
# 5. 후보 판단
# ============================================================

def percentile_score(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.notna().sum() <= 1:
        return pd.Series(0.5, index=series.index)

    if higher_is_better:
        return s.rank(pct=True)
    return (-s).rank(pct=True)


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
        [
            final["strict_turnover_pass"],
            final["flex_turnover_pass"],
        ],
        [
            "strict_pass",
            "flex_pass",
        ],
        default="fail",
    )

    return final


def build_final_judgement(cost_table: pd.DataFrame) -> pd.DataFrame:
    final = build_turnover_filtered_table(cost_table)

    ew = choose_ew_benchmark(cost_table, FINAL_COST_LABEL)

    if ew is None:
        ew_cagr = np.nan
        ew_mdd = np.nan
        ew_sharpe = np.nan
        ew_calmar = np.nan
    else:
        ew_cagr = ew["CAGR_pct"]
        ew_mdd = ew["MDD_pct"]
        ew_sharpe = ew["Sharpe"]
        ew_calmar = ew["Calmar"]

    cost_20 = cost_table[cost_table["cost_label"] == "cost_20bp"][[
        "candidate_key",
        "CAGR_pct",
        "CAGR_cost_drag_pct",
    ]].rename(columns={
        "CAGR_pct": "CAGR_20bp_pct",
        "CAGR_cost_drag_pct": "CAGR_cost_drag_20bp_pct",
    })

    out = final.merge(cost_20, on="candidate_key", how="left")

    out["CAGR_gap_vs_EW_pct"] = out["CAGR_pct"] - ew_cagr
    out["MDD_gap_vs_EW_pct"] = out["MDD_pct"] - ew_mdd
    out["Sharpe_gap_vs_EW"] = out["Sharpe"] - ew_sharpe
    out["Calmar_gap_vs_EW"] = out["Calmar"] - ew_calmar

    out["performance_pass"] = out["CAGR_gap_vs_EW_pct"] >= MIN_CAGR_GAP_VS_EW_PCT
    out["mdd_pass"] = out["MDD_pct"] >= (ew_mdd - MDD_WORSE_THAN_EW_ALLOWANCE_PCT)
    out["sharpe_pass"] = out["Sharpe"] >= MIN_SHARPE
    out["calmar_pass"] = out["Calmar"] >= MIN_CALMAR
    out["risk_metric_pass"] = out["mdd_pass"] & out["sharpe_pass"] & out["calmar_pass"]

    out["cost_sensitivity_pass"] = (
        (out["CAGR_20bp_pct"] >= ew_cagr)
        & (out["CAGR_cost_drag_20bp_pct"] <= MAX_COST_DRAG_20BP_PCT)
    )

    # 간단한 robustness proxy:
    # 같은 source_type 안에서 strict 또는 flex 조건과 성과·위험·비용 조건을 통과한 후보가 2개 이상이면
    # 해당 실험군은 단일 파라미터에만 의존하지 않는 것으로 본다.
    out["core_pass_for_robustness"] = (
        out["months_pass"]
        & out["flex_turnover_pass"]
        & out["performance_pass"]
        & out["risk_metric_pass"]
        & out["cost_sensitivity_pass"]
        & (out["strategy_name"] != "EW")
    )

    robust_counts = (
        out.groupby("source_type")["core_pass_for_robustness"]
        .sum()
        .reset_index(name="source_type_pass_count")
    )

    out = out.merge(robust_counts, on="source_type", how="left")
    out["robustness_proxy_pass"] = out["source_type_pass_count"] >= 2

    out["selection_score"] = (
        0.22 * percentile_score(out["CAGR_pct"], higher_is_better=True)
        + 0.26 * percentile_score(out["MDD_pct"], higher_is_better=True)
        + 0.20 * percentile_score(out["Calmar"], higher_is_better=True)
        + 0.16 * percentile_score(out["Sharpe"], higher_is_better=True)
        + 0.16 * percentile_score(out["avg_turnover_pct"], higher_is_better=False)
    )

    decisions = []
    reasons = []

    for _, row in out.iterrows():
        if row["strategy_name"] == "EW":
            decisions.append("benchmark")
            reasons.append("동일가중 비교 기준")
            continue

        if not row["months_pass"]:
            decisions.append("exclude_short_sample")
            reasons.append("비교 가능한 백테스트 월 수가 부족함")
            continue

        if not row["flex_turnover_pass"]:
            decisions.append("exclude_turnover")
            reasons.append("평균 또는 최대 Turnover가 후보 기준을 초과함")
            continue

        if not row["performance_pass"]:
            decisions.append("exclude_return")
            reasons.append("비용 반영 후 CAGR이 EW 기준을 넘지 못함")
            continue

        if not row["risk_metric_pass"]:
            decisions.append("exclude_risk_metric")
            reasons.append("MDD, Sharpe, Calmar 중 하나 이상이 방어형 기준을 통과하지 못함")
            continue

        if not row["cost_sensitivity_pass"]:
            decisions.append("review_cost_sensitive")
            reasons.append("0.20% 보수적 비용 가정에서 성과 훼손 여부를 추가 검토해야 함")
            continue

        if row["strict_turnover_pass"] and row["robustness_proxy_pass"]:
            decisions.append("final_candidate")
            reasons.append("Turnover, 비용, MDD, Sharpe, Calmar, robustness proxy를 통과함")
        elif row["flex_turnover_pass"] and row["robustness_proxy_pass"]:
            decisions.append("reserve_candidate")
            reasons.append("핵심 조건은 통과했으나 Turnover 기준이 유연 기준에 해당함")
        else:
            decisions.append("review_robustness")
            reasons.append("핵심 조건은 양호하나 동일 실험군 내 주변 후보 안정성 확인이 더 필요함")

    out["final_decision"] = decisions
    out["decision_reason"] = reasons

    sort_order = {
        "final_candidate": 1,
        "reserve_candidate": 2,
        "review_robustness": 3,
        "review_cost_sensitive": 4,
        "exclude_risk_metric": 5,
        "exclude_turnover": 6,
        "exclude_return": 7,
        "exclude_short_sample": 8,
        "benchmark": 9,
    }
    out["decision_order"] = out["final_decision"].map(sort_order).fillna(99)

    out = out.sort_values(
        ["decision_order", "selection_score", "CAGR_pct"],
        ascending=[True, False, False],
    ).reset_index(drop=True)

    return out


# ============================================================
# 6. 요약표와 노트
# ============================================================

def build_source_inventory(backtest_files: list[Path], loaded_frames: list[pd.DataFrame]) -> pd.DataFrame:
    rows = []

    loaded_map = {df["source_file"].iloc[0]: df for df in loaded_frames if not df.empty}

    for path in backtest_files:
        df = loaded_map.get(path.name)
        if df is None:
            rows.append({
                "source_file": path.name,
                "source_type": infer_source_type(path),
                "rows": 0,
                "strategies": "",
                "status": "SKIPPED_OR_EMPTY",
                "note": "필수 컬럼 누락 또는 빈 파일",
            })
        else:
            rows.append({
                "source_file": path.name,
                "source_type": infer_source_type(path),
                "rows": len(df),
                "strategies": ", ".join(sorted(df["strategy_name"].dropna().astype(str).unique())),
                "status": "OK",
                "note": "최종 후보 선정 입력으로 사용",
            })

    return pd.DataFrame(rows)


def build_selection_summary(final_judgement: pd.DataFrame, cost_table: pd.DataFrame) -> pd.DataFrame:
    decision_counts = (
        final_judgement["final_decision"]
        .value_counts(dropna=False)
        .rename_axis("final_decision")
        .reset_index(name="candidate_count")
    )

    rows = []
    rows.append({
        "item": "total_candidate_rows_at_final_cost",
        "value": len(final_judgement),
        "note": f"대표 비용률 {FINAL_COST_LABEL} 기준 후보 행 수",
    })
    rows.append({
        "item": "final_candidate_count",
        "value": int((final_judgement["final_decision"] == "final_candidate").sum()),
        "note": "최종 후보 수",
    })
    rows.append({
        "item": "reserve_candidate_count",
        "value": int((final_judgement["final_decision"] == "reserve_candidate").sum()),
        "note": "보류 후보 수",
    })
    rows.append({
        "item": "cost_rate_grid",
        "value": str(COST_RATE_GRID),
        "note": "거래비용률 민감도 후보",
    })
    rows.append({
        "item": "turnover_filter_strict",
        "value": f"avg <= {STRICT_AVG_TURNOVER_PCT}%, max <= {STRICT_MAX_TURNOVER_PCT}%",
        "note": "엄격 Turnover 후보 기준",
    })
    rows.append({
        "item": "turnover_filter_flex",
        "value": f"avg <= {FLEX_AVG_TURNOVER_PCT}%, max <= {FLEX_MAX_TURNOVER_PCT}%",
        "note": "유연 Turnover 후보 기준",
    })

    summary = pd.DataFrame(rows)

    # decision count를 뒤에 붙인다.
    decision_rows = []
    for _, row in decision_counts.iterrows():
        decision_rows.append({
            "item": f"decision_count_{row['final_decision']}",
            "value": row["candidate_count"],
            "note": "최종 판단 분포",
        })

    return pd.concat([summary, pd.DataFrame(decision_rows)], ignore_index=True)


def build_note(
    source_inventory: pd.DataFrame,
    final_judgement: pd.DataFrame,
    selection_summary: pd.DataFrame,
) -> str:
    lines = []

    lines.append("# main_final 최종 후보 선정 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 단계는 00~11번 실험에서 생성된 백테스트 시계열을 모아 Turnover 필터, "
        "거래비용 민감도, MDD, Sharpe, Calmar 기준을 적용해 최종 후보군을 선별한다. "
        "최고 CAGR 하나를 고르는 것이 아니라 방어형 overlay로 해석 가능한 후보를 압축하는 절차이다."
    )
    lines.append("")
    lines.append("## 2. 거래비용 계산")
    lines.append("")
    lines.append("```text")
    lines.append("월별 거래비용 = 월별 Turnover × 거래비용률")
    lines.append("비용 차감 후 월수익률 = 기존 월수익률 - 월별 거래비용")
    lines.append("```")
    lines.append("")
    lines.append("거래비용률 후보는 다음과 같다.")
    lines.append("")
    lines.append("| label | cost_rate | 해석 |")
    lines.append("|---|---:|---|")
    label_map = {
        "cost_0bp": "비용 미반영 기준",
        "cost_5bp": "낮은 비용 가정",
        "cost_10bp": "보통 비용 가정",
        "cost_20bp": "보수적 비용 가정",
    }
    for label, rate in COST_RATE_GRID.items():
        lines.append(f"| {label} | {rate:.4f} | {label_map.get(label, '')} |")
    lines.append("")
    lines.append("## 3. 입력 파일")
    lines.append("")
    lines.append("| source_file | source_type | rows | status | strategies |")
    lines.append("|---|---|---:|---|---|")
    for _, row in source_inventory.iterrows():
        lines.append(
            f"| {row['source_file']} | {row['source_type']} | {row['rows']} | "
            f"{row['status']} | {row['strategies']} |"
        )
    lines.append("")
    lines.append("## 4. 최종 후보 판단 기준")
    lines.append("")
    lines.append(f"- 대표 비용률: `{FINAL_COST_LABEL}` = {FINAL_COST_RATE:.4f}")
    lines.append(f"- 엄격 Turnover 기준: 평균 {STRICT_AVG_TURNOVER_PCT}% 이하, 최대 {STRICT_MAX_TURNOVER_PCT}% 이하")
    lines.append(f"- 유연 Turnover 기준: 평균 {FLEX_AVG_TURNOVER_PCT}% 이하, 최대 {FLEX_MAX_TURNOVER_PCT}% 이하")
    lines.append(f"- MDD 기준: EW 대비 {MDD_WORSE_THAN_EW_ALLOWANCE_PCT}%p 이상 악화되지 않을 것")
    lines.append(f"- Sharpe 기준: {MIN_SHARPE} 이상")
    lines.append(f"- Calmar 기준: {MIN_CALMAR} 이상")
    lines.append(f"- 보수적 비용 기준: 20bp 비용 적용 후 CAGR 손상폭 {MAX_COST_DRAG_20BP_PCT}%p 이하")
    lines.append("")
    lines.append("## 5. 최종 후보 상위표")
    lines.append("")
    display = final_judgement[
        final_judgement["final_decision"].isin(["final_candidate", "reserve_candidate", "review_robustness"])
    ].head(20)

    if display.empty:
        lines.append("현재 기준을 통과한 최종 후보는 없다. 기준을 완화하거나 후보군을 추가 검토해야 한다.")
    else:
        lines.append("| decision | source_type | strategy | CAGR | MDD | Sharpe | Calmar | avg_turnover | max_turnover | reason |")
        lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---|")
        for _, row in display.iterrows():
            lines.append(
                f"| {row['final_decision']} | {row['source_type']} | {row['strategy_name']} | "
                f"{row['CAGR_pct']:.4f} | {row['MDD_pct']:.4f} | {row['Sharpe']:.4f} | "
                f"{row['Calmar']:.4f} | {row['avg_turnover_pct']:.4f} | "
                f"{row['max_turnover_pct']:.4f} | {row['decision_reason']} |"
            )
    lines.append("")
    lines.append("## 6. 요약")
    lines.append("")
    lines.append("| item | value | note |")
    lines.append("|---|---:|---|")
    for _, row in selection_summary.iterrows():
        lines.append(f"| {row['item']} | {row['value']} | {row['note']} |")
    lines.append("")
    lines.append("## 7. 해석상 주의")
    lines.append("")
    lines.append(
        "이 표는 자동으로 최종 정답을 확정하기 위한 것이 아니라, 후보를 압축하기 위한 기준표이다. "
        "최종 보고서에서는 선택 후보뿐 아니라 제외·보류 사유를 함께 기록해야 한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 7. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("12_select_final_candidates_with_cost_and_turnover.py 실행 시작")
    print("=" * 80)

    print("[1] 최종 폴더 확인")
    cfg.ensure_final_directories()
    print("    OK")

    print("[2] 백테스트 시계열 파일 탐색")
    backtest_files = discover_backtest_files()
    if not backtest_files:
        raise FileNotFoundError(
            f"{cfg.PROCESSED_DIR}에서 {BACKTEST_GLOB} 파일을 찾지 못했습니다. "
            "05~11번 백테스트 파일을 먼저 실행하세요."
        )

    for path in backtest_files:
        print(f"    발견: {path.name}")

    print("[3] 백테스트 시계열 로드")
    frames = []
    for path in backtest_files:
        df = read_csv(path)
        if not ensure_required_columns(df, path):
            continue
        norm = normalize_timeseries(df, path)
        frames.append(norm)
        print(f"    사용: {path.name} shape={norm.shape}")

    if not frames:
        raise RuntimeError("최종 후보 선정에 사용할 수 있는 백테스트 시계열이 없습니다.")

    source_inventory = build_source_inventory(backtest_files, frames)
    save_csv(source_inventory, OUTPUT_SOURCE_INVENTORY)
    print(f"    저장: {OUTPUT_SOURCE_INVENTORY}")

    backtest_all = pd.concat(frames, ignore_index=True)

    print("[4] 거래비용 민감도 성과표 계산")
    cost_table = build_cost_sensitivity_table(backtest_all)
    cost_table = add_cost_drag_columns(cost_table)
    save_csv(cost_table, OUTPUT_ALL_COST)
    print(f"    저장: {OUTPUT_ALL_COST}")

    print("[5] Turnover 필터 후보표 생성")
    turnover_filtered = build_turnover_filtered_table(cost_table)
    save_csv(turnover_filtered, OUTPUT_TURNOVER_FILTERED)
    print(f"    저장: {OUTPUT_TURNOVER_FILTERED}")

    print("[6] 최종 후보 판단표 생성")
    final_judgement = build_final_judgement(cost_table)
    save_csv(final_judgement, OUTPUT_FINAL_JUDGEMENT)
    print(f"    저장: {OUTPUT_FINAL_JUDGEMENT}")

    print("[7] 요약표와 노트 생성")
    selection_summary = build_selection_summary(final_judgement, cost_table)
    save_csv(selection_summary, OUTPUT_SELECTION_SUMMARY)
    print(f"    저장: {OUTPUT_SELECTION_SUMMARY}")

    note = build_note(source_inventory, final_judgement, selection_summary)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[최종 후보 판단 상위 20개]")
    display_cols = [
        "final_decision",
        "source_type",
        "strategy_name",
        "combo_id",
        "theta_common",
        "lambda_value",
        "CAGR_pct",
        "MDD_pct",
        "Sharpe",
        "Calmar",
        "avg_turnover_pct",
        "max_turnover_pct",
        "CAGR_cost_drag_20bp_pct",
        "selection_score",
        "decision_reason",
    ]
    display_cols = [c for c in display_cols if c in final_judgement.columns]
    print(final_judgement[display_cols].head(20).to_string(index=False))

    print("\n[판단 분포]")
    print(
        final_judgement["final_decision"]
        .value_counts(dropna=False)
        .rename_axis("final_decision")
        .reset_index(name="count")
        .to_string(index=False)
    )

    print("=" * 80)
    print("12_select_final_candidates_with_cost_and_turnover.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
