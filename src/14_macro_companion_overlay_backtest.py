from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
14_macro_companion_overlay_backtest.py

목적
----
05번 baseline HSI 비중표 위에 12~13번 macro companion 보조값을
아주 작은 방어 보정값으로 연결한다.

핵심 원칙
---------
1. HSI 상태 자체는 바꾸지 않는다.
2. macro companion은 HSI baseline 비중 위에 얹는 soft overlay로만 사용한다.
3. 매크로 자료가 없는 월은 baseline 비중을 그대로 사용한다.
4. 위험자산 069500에서 줄인 비중은 114260 30%, 153130 70%로 이동한다.
5. 월말 신호 t와 조정 비중은 다음 달 월간 수익률 t+1에 적용한다.

입력
----
data/processed/main_final_baseline_rebalance_weights.csv
data/processed/main_final_hsi_macro_companion_joined_monthly.csv
data/processed/main_final_monthly_return_decimal.csv

출력
----
data/processed/main_final_macro_overlay_weights.csv
data/processed/main_final_macro_overlay_backtest_timeseries.csv

output/tables/main_final_macro_overlay_performance_summary.csv
output/tables/main_final_macro_overlay_weight_adjustment_summary.csv
output/tables/main_final_macro_overlay_recent_weights.csv

docs/main_final_macro_overlay_backtest_note.md
"""


# ============================================================
# 0. 경로 및 공통 설정
# ============================================================

INPUT_BASELINE_WEIGHTS = cfg.PROCESSED_DIR / "main_final_baseline_rebalance_weights.csv"
INPUT_MACRO_JOINED = cfg.PROCESSED_DIR / "main_final_hsi_macro_companion_joined_monthly.csv"
INPUT_MONTHLY_RETURNS = cfg.PROCESSED_DIR / "main_final_monthly_return_decimal.csv"

OUTPUT_WEIGHTS = cfg.PROCESSED_DIR / "main_final_macro_overlay_weights.csv"
OUTPUT_BACKTEST_TS = cfg.PROCESSED_DIR / "main_final_macro_overlay_backtest_timeseries.csv"

OUTPUT_PERFORMANCE = cfg.TABLE_DIR / "main_final_macro_overlay_performance_summary.csv"
OUTPUT_ADJUSTMENT_SUMMARY = cfg.TABLE_DIR / "main_final_macro_overlay_weight_adjustment_summary.csv"
OUTPUT_RECENT_WEIGHTS = cfg.TABLE_DIR / "main_final_macro_overlay_recent_weights.csv"

OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_macro_overlay_backtest_note.md"

YEAR_MONTH_COL = "year_month"
RETURN_YEAR_MONTH_COL = "return_year_month"

TICKERS = list(getattr(cfg, "TICKERS", ["069500", "114260", "153130"]))

RISK_ASSET = "069500"
DEFENSIVE_BOND = "114260"
DEFENSIVE_CASHLIKE = "153130"

DEFENSIVE_TRANSFER_RATIO = {
    DEFENSIVE_BOND: 0.30,
    DEFENSIVE_CASHLIKE: 0.70,
}

MAX_MACRO_DELTA = 0.03

STRATEGY_BASELINE = "HSI_final_baseline_overlay"
STRATEGY_MACRO = "HSI_macro_companion_soft_overlay"

HSI_RISK_STATES = {"risk_warning", "accident_zone"}


# ============================================================
# 1. 입출력 보조 함수
# ============================================================

def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")


def read_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{label} 파일이 없습니다: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def normalize_year_month(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if YEAR_MONTH_COL not in out.columns:
        first_col = out.columns[0]

        if str(first_col).lower() in ["date", "datetime", "month"]:
            out[YEAR_MONTH_COL] = (
                pd.to_datetime(out[first_col], errors="coerce")
                .dt.to_period("M")
                .astype(str)
            )
        else:
            out = out.rename(columns={first_col: YEAR_MONTH_COL})

    out[YEAR_MONTH_COL] = out[YEAR_MONTH_COL].astype(str)
    out = out.dropna(subset=[YEAR_MONTH_COL])
    out = out.sort_values(YEAR_MONTH_COL).reset_index(drop=True)

    return out


def normalize_returns(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_year_month(df)

    for ticker in TICKERS:
        if ticker in out.columns:
            out[ticker] = pd.to_numeric(out[ticker], errors="coerce")
        else:
            raise ValueError(
                f"월간 수익률 파일에 {ticker} 컬럼이 없습니다. "
                f"현재 컬럼: {list(out.columns)}"
            )

    return out


def require_columns(df: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(
            f"{label}에 필요한 컬럼이 없습니다: {missing}\n"
            f"현재 컬럼: {list(df.columns)}"
        )


def first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


# ============================================================
# 2. macro companion 컬럼 표준화
# ============================================================

def normalize_macro_joined(macro_joined: pd.DataFrame) -> pd.DataFrame:
    out = normalize_year_month(macro_joined)

    addon_col = first_existing_column(
        out,
        [
            "macro_defense_addon",
            "macro_defensive_addon",
            "defense_addon",
            "macro_overlay_addon",
        ],
    )

    if addon_col is None:
        raise ValueError(
            "macro companion joined table에서 macro_defense_addon 컬럼을 찾지 못했습니다.\n"
            f"현재 컬럼: {list(out.columns)}"
        )

    out["macro_defense_addon"] = pd.to_numeric(
        out[addon_col],
        errors="coerce",
    ).fillna(0.0)

    available_col = first_existing_column(
        out,
        [
            "macro_data_available",
            "macro_available",
            "rate_fx_data_available",
        ],
    )

    if available_col is None:
        out["macro_data_available"] = np.where(
            out["macro_defense_addon"].notna(),
            1,
            0,
        )
    else:
        out["macro_data_available"] = pd.to_numeric(
            out[available_col],
            errors="coerce",
        ).fillna(0).astype(int)

    risk_flag_col = first_existing_column(
        out,
        [
            "macro_risk_flag",
            "macro_risk",
            "is_macro_risk",
        ],
    )

    if risk_flag_col is None:
        out["macro_risk_flag"] = np.where(
            (out["macro_data_available"] == 1)
            & (out["macro_defense_addon"] > 0),
            1,
            0,
        )
    else:
        out["macro_risk_flag"] = pd.to_numeric(
            out[risk_flag_col],
            errors="coerce",
        ).fillna(0).astype(int)

    regime_col = first_existing_column(
        out,
        [
            "macro_companion_regime_filled",
            "macro_companion_regime",
            "macro_regime",
        ],
    )

    if regime_col is None:
        out["macro_companion_regime"] = ""
    else:
        out["macro_companion_regime"] = out[regime_col].astype(str)

    keep_cols = [
        YEAR_MONTH_COL,
        "macro_data_available",
        "macro_risk_flag",
        "macro_defense_addon",
        "macro_companion_regime",
    ]

    optional_cols = [
        "gdp_data_available",
        "rate_fx_departure_range",
        "rate_up_flag",
        "fx_up_flag",
        "gdp_growth_yoy",
    ]

    for col in optional_cols:
        if col in out.columns:
            keep_cols.append(col)

    return out[keep_cols].copy()


# ============================================================
# 3. overlay 강도와 조정 비중 생성
# ============================================================

def classify_overlap(row: pd.Series) -> str:
    if int(row.get("macro_data_available", 0)) == 0:
        return "macro_data_unavailable"

    hsi_state = str(row.get("hsi_state", ""))
    hsi_risk = hsi_state in HSI_RISK_STATES
    macro_risk = int(row.get("macro_risk_flag", 0)) == 1

    if hsi_risk and macro_risk:
        return "both_hsi_and_macro_risk"

    if hsi_risk and not macro_risk:
        return "hsi_risk_only"

    if (not hsi_risk) and macro_risk:
        return "macro_risk_only"

    return "both_relief_or_neutral"


def decide_overlay_strength(row: pd.Series) -> float:
    if int(row.get("macro_data_available", 0)) == 0:
        return 0.0

    overlap_type = row.get("macro_hsi_overlap_type", "")
    hsi_state = str(row.get("hsi_state", ""))

    if overlap_type == "both_hsi_and_macro_risk":
        return 1.00

    if overlap_type == "macro_risk_only":
        if hsi_state in ["conflict", "neutral_watch"]:
            return 0.50

        if hsi_state == "risk_relief":
            return 0.25

        return 0.25

    return 0.0


def prepare_baseline_weights(baseline_weights: pd.DataFrame) -> pd.DataFrame:
    out = normalize_year_month(baseline_weights)

    if RETURN_YEAR_MONTH_COL not in out.columns:
        out[RETURN_YEAR_MONTH_COL] = (
            out[YEAR_MONTH_COL]
            .apply(lambda x: str(pd.Period(x, freq="M") + 1))
        )

    required = [
        YEAR_MONTH_COL,
        RETURN_YEAR_MONTH_COL,
        "hsi_state",
    ] + [f"weight_{ticker}" for ticker in TICKERS]

    require_columns(out, required, "baseline weights")

    for ticker in TICKERS:
        out[f"weight_{ticker}"] = pd.to_numeric(
            out[f"weight_{ticker}"],
            errors="coerce",
        )

    if "turnover" not in out.columns:
        weight_cols = [f"weight_{ticker}" for ticker in TICKERS]
        out["turnover"] = out[weight_cols].diff().abs().sum(axis=1) * 0.5
        out.loc[out.index[0], "turnover"] = 0.0

    if "state_kr" not in out.columns:
        out["state_kr"] = ""

    if "allocation_rule_name" not in out.columns:
        out["allocation_rule_name"] = "final_baseline_allocation_rule"

    return out


def build_macro_overlay_weights(
    baseline_weights: pd.DataFrame,
    macro_joined: pd.DataFrame,
) -> pd.DataFrame:
    baseline = prepare_baseline_weights(baseline_weights)
    macro = normalize_macro_joined(macro_joined)

    merged = baseline.merge(
        macro,
        on=YEAR_MONTH_COL,
        how="left",
    )

    merged["macro_data_available"] = (
        pd.to_numeric(
            merged["macro_data_available"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    merged["macro_risk_flag"] = (
        pd.to_numeric(
            merged["macro_risk_flag"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    merged["macro_defense_addon"] = (
        pd.to_numeric(
            merged["macro_defense_addon"],
            errors="coerce",
        )
        .fillna(0.0)
        .clip(lower=0.0, upper=MAX_MACRO_DELTA)
    )

    for ticker in TICKERS:
        merged[f"base_weight_{ticker}"] = merged[f"weight_{ticker}"]

    merged["macro_hsi_overlap_type"] = merged.apply(
        classify_overlap,
        axis=1,
    )

    merged["overlay_strength"] = merged.apply(
        decide_overlay_strength,
        axis=1,
    )

    merged["macro_overlay_delta"] = (
        merged["macro_defense_addon"]
        * merged["overlay_strength"]
    ).clip(lower=0.0, upper=MAX_MACRO_DELTA)

    # 069500 비중이 0인 accident_zone에서는 더 줄일 수 없으므로 delta를 실제 가능 범위 안으로 제한한다.
    merged["macro_overlay_delta"] = np.minimum(
        merged["macro_overlay_delta"],
        merged[f"base_weight_{RISK_ASSET}"],
    )

    merged[f"weight_{RISK_ASSET}"] = (
        merged[f"base_weight_{RISK_ASSET}"]
        - merged["macro_overlay_delta"]
    )

    merged[f"weight_{DEFENSIVE_BOND}"] = (
        merged[f"base_weight_{DEFENSIVE_BOND}"]
        + merged["macro_overlay_delta"] * DEFENSIVE_TRANSFER_RATIO[DEFENSIVE_BOND]
    )

    merged[f"weight_{DEFENSIVE_CASHLIKE}"] = (
        merged[f"base_weight_{DEFENSIVE_CASHLIKE}"]
        + merged["macro_overlay_delta"] * DEFENSIVE_TRANSFER_RATIO[DEFENSIVE_CASHLIKE]
    )

    # 혹시 티커가 3개 이상으로 확장되어도, 위 세 티커 외 자산은 baseline 비중을 그대로 둔다.
    for ticker in TICKERS:
        if ticker not in [RISK_ASSET, DEFENSIVE_BOND, DEFENSIVE_CASHLIKE]:
            merged[f"weight_{ticker}"] = merged[f"base_weight_{ticker}"]

    weight_cols = [f"weight_{ticker}" for ticker in TICKERS]
    weight_sum = merged[weight_cols].sum(axis=1)

    # 부동소수점 오차만 보정한다.
    for ticker in TICKERS:
        merged[f"weight_{ticker}"] = np.where(
            weight_sum > 0,
            merged[f"weight_{ticker}"] / weight_sum,
            merged[f"weight_{ticker}"],
        )

    merged["turnover"] = (
        merged[weight_cols]
        .diff()
        .abs()
        .sum(axis=1)
        * 0.5
    )
    merged.loc[merged.index[0], "turnover"] = 0.0

    merged["allocation_rule_name"] = "hsi_baseline_plus_macro_soft_overlay"

    return merged.sort_values(YEAR_MONTH_COL).reset_index(drop=True)


# ============================================================
# 4. 백테스트 계산
# ============================================================

def calculate_strategy_return(
    weights: pd.DataFrame,
    returns: pd.DataFrame,
    strategy_name: str,
) -> pd.DataFrame:
    ret = normalize_returns(returns)
    ret = ret.rename(columns={YEAR_MONTH_COL: RETURN_YEAR_MONTH_COL})

    merged = weights.merge(
        ret,
        on=RETURN_YEAR_MONTH_COL,
        how="left",
    )

    for ticker in TICKERS:
        merged[f"return_{ticker}"] = pd.to_numeric(
            merged[ticker],
            errors="coerce",
        )
        merged[f"contribution_{ticker}"] = (
            merged[f"weight_{ticker}"]
            * merged[f"return_{ticker}"]
        )

    contribution_cols = [f"contribution_{ticker}" for ticker in TICKERS]
    merged["strategy_return"] = merged[contribution_cols].sum(axis=1)
    merged["strategy_name"] = strategy_name

    keep_cols = [
        "strategy_name",
        YEAR_MONTH_COL,
        RETURN_YEAR_MONTH_COL,
        "hsi_state",
        "state_kr",
        "allocation_rule_name",
        "macro_data_available",
        "macro_risk_flag",
        "macro_defense_addon",
        "macro_hsi_overlap_type",
        "overlay_strength",
        "macro_overlay_delta",
        "strategy_return",
        "turnover",
    ]

    if "macro_companion_regime" in merged.columns:
        keep_cols.append("macro_companion_regime")

    for ticker in TICKERS:
        keep_cols += [
            f"weight_{ticker}",
            f"return_{ticker}",
            f"contribution_{ticker}",
        ]

    available_keep_cols = [col for col in keep_cols if col in merged.columns]

    out = merged[available_keep_cols].copy()
    out = out.dropna(subset=["strategy_return"]).reset_index(drop=True)

    return out


def add_cumulative_and_drawdown(backtest_ts: pd.DataFrame) -> pd.DataFrame:
    frames = []

    for strategy, group in backtest_ts.groupby("strategy_name"):
        g = group.sort_values(RETURN_YEAR_MONTH_COL).copy()
        g["cumulative_return"] = (1.0 + g["strategy_return"]).cumprod()
        g["running_max"] = g["cumulative_return"].cummax()
        g["drawdown"] = g["cumulative_return"] / g["running_max"] - 1.0
        frames.append(g)

    return pd.concat(frames, ignore_index=True)


def calc_performance(group: pd.DataFrame) -> dict:
    g = group.sort_values(RETURN_YEAR_MONTH_COL).copy()
    r = g["strategy_return"].dropna()

    months = len(r)

    if months == 0:
        return {}

    final_cum = float((1 + r).prod())
    cagr = final_cum ** (12 / months) - 1 if months > 0 else np.nan
    ann_vol = r.std(ddof=1) * np.sqrt(12) if months > 1 else np.nan

    ann_return_mean = r.mean() * 12
    sharpe = ann_return_mean / ann_vol if pd.notna(ann_vol) and ann_vol != 0 else np.nan

    downside = r[r < 0]
    downside_vol = downside.std(ddof=1) * np.sqrt(12) if len(downside) > 1 else np.nan
    sortino = (
        ann_return_mean / downside_vol
        if pd.notna(downside_vol) and downside_vol != 0
        else np.nan
    )

    mdd = g["drawdown"].min()
    calmar = cagr / abs(mdd) if pd.notna(mdd) and mdd < 0 else np.nan
    win_rate = (r > 0).mean()

    return {
        "strategy_name": g["strategy_name"].iloc[0],
        "months": months,
        "final_cumulative_return": final_cum,
        "CAGR_pct": cagr * 100,
        "annual_volatility_pct": ann_vol * 100 if pd.notna(ann_vol) else np.nan,
        "MDD_pct": mdd * 100 if pd.notna(mdd) else np.nan,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Calmar": calmar,
        "WinRate_pct": win_rate * 100,
        "avg_monthly_return_pct": r.mean() * 100,
        "best_month_pct": r.max() * 100,
        "worst_month_pct": r.min() * 100,
    }


def build_performance_summary(backtest_ts: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, group in backtest_ts.groupby("strategy_name"):
        rows.append(calc_performance(group))

    performance = pd.DataFrame(rows)

    if not performance.empty and STRATEGY_BASELINE in set(performance["strategy_name"]):
        baseline = performance.loc[
            performance["strategy_name"] == STRATEGY_BASELINE
        ].iloc[0]

        for col in ["CAGR_pct", "MDD_pct", "Sharpe", "Calmar", "WinRate_pct"]:
            performance[f"{col}_diff_vs_baseline"] = (
                performance[col]
                - baseline[col]
            )

    return performance


# ============================================================
# 5. 조정 요약표와 노트
# ============================================================

def summarize_group(
    weights: pd.DataFrame,
    group_cols: list[str],
    summary_name: str,
) -> pd.DataFrame:
    out = (
        weights
        .groupby(group_cols, dropna=False)
        .agg(
            months=(YEAR_MONTH_COL, "count"),
            macro_data_available_months=("macro_data_available", "sum"),
            macro_risk_months=("macro_risk_flag", "sum"),
            adjusted_months=("macro_overlay_delta", lambda x: int((x > 0).sum())),
            avg_delta_pctp=("macro_overlay_delta", lambda x: x.mean() * 100),
            max_delta_pctp=("macro_overlay_delta", lambda x: x.max() * 100),
            total_delta_pctp=("macro_overlay_delta", lambda x: x.sum() * 100),
            avg_strength=("overlay_strength", "mean"),
            max_strength=("overlay_strength", "max"),
        )
        .reset_index()
    )

    out.insert(0, "summary_type", summary_name)

    return out


def build_adjustment_summary(weights: pd.DataFrame) -> pd.DataFrame:
    overall = pd.DataFrame(
        [
            {
                "summary_type": "overall",
                "segment": "all",
                "months": len(weights),
                "macro_data_available_months": int(weights["macro_data_available"].sum()),
                "macro_risk_months": int(weights["macro_risk_flag"].sum()),
                "adjusted_months": int((weights["macro_overlay_delta"] > 0).sum()),
                "avg_delta_pctp": weights["macro_overlay_delta"].mean() * 100,
                "max_delta_pctp": weights["macro_overlay_delta"].max() * 100,
                "total_delta_pctp": weights["macro_overlay_delta"].sum() * 100,
                "avg_strength": weights["overlay_strength"].mean(),
                "max_strength": weights["overlay_strength"].max(),
            }
        ]
    )

    by_overlap = summarize_group(
        weights,
        ["macro_hsi_overlap_type"],
        "by_macro_hsi_overlap_type",
    ).rename(columns={"macro_hsi_overlap_type": "segment"})

    by_state = summarize_group(
        weights,
        ["hsi_state"],
        "by_hsi_state",
    ).rename(columns={"hsi_state": "segment"})

    common_cols = [
        "summary_type",
        "segment",
        "months",
        "macro_data_available_months",
        "macro_risk_months",
        "adjusted_months",
        "avg_delta_pctp",
        "max_delta_pctp",
        "total_delta_pctp",
        "avg_strength",
        "max_strength",
    ]

    return pd.concat(
        [
            overall[common_cols],
            by_overlap[common_cols],
            by_state[common_cols],
        ],
        ignore_index=True,
    )


def build_recent_weights(weights: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    cols = [
        YEAR_MONTH_COL,
        RETURN_YEAR_MONTH_COL,
        "hsi_state",
        "state_kr",
        "macro_data_available",
        "macro_risk_flag",
        "macro_defense_addon",
        "macro_hsi_overlap_type",
        "overlay_strength",
        "macro_overlay_delta",
    ]

    if "macro_companion_regime" in weights.columns:
        cols.append("macro_companion_regime")

    for ticker in TICKERS:
        cols += [
            f"base_weight_{ticker}",
            f"weight_{ticker}",
        ]

    return weights[cols].tail(n).copy()


def build_note(
    performance: pd.DataFrame,
    adjustment_summary: pd.DataFrame,
) -> str:
    lines = []

    lines.append("# main_final macro companion soft overlay 백테스트 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 단계는 05번 baseline HSI 비중 위에 macro companion 보조값을 "
        "소폭 반영하여, baseline과 macro overlay의 성과 및 비중 조정 정도를 비교한다."
    )
    lines.append("")
    lines.append("## 2. 핵심 원칙")
    lines.append("")
    lines.append("- HSI 상태분류는 바꾸지 않는다.")
    lines.append("- macro companion은 HSI baseline 비중 위의 작은 방어 보정값으로만 사용한다.")
    lines.append("- `macro_data_available = 0`인 월은 baseline 비중을 그대로 사용한다.")
    lines.append(
        f"- 위험자산 `{RISK_ASSET}`에서 줄인 비중은 "
        f"`{DEFENSIVE_BOND}` 30%, `{DEFENSIVE_CASHLIKE}` 70%로 이동한다."
    )
    lines.append(f"- macro overlay delta는 최대 {MAX_MACRO_DELTA * 100:.1f}%p로 제한한다.")
    lines.append("")
    lines.append("## 3. 적용 강도 규칙")
    lines.append("")
    lines.append("| 구분 | 적용 강도 | 해석 |")
    lines.append("|---|---:|---|")
    lines.append("| both_hsi_and_macro_risk | 1.00 | HSI와 macro가 동시에 위험을 말할 때만 온전히 반영 |")
    lines.append("| macro_risk_only + conflict/neutral_watch | 0.50 | HSI가 확실한 위험은 아니므로 절반만 반영 |")
    lines.append("| macro_risk_only + risk_relief | 0.25 | HSI가 완화 쪽이면 과잉방어 방지를 위해 작게 반영 |")
    lines.append("| hsi_risk_only 또는 both_relief_or_neutral | 0.00 | baseline 유지 |")
    lines.append("")
    lines.append("## 4. 성과 요약")
    lines.append("")
    lines.append("| strategy | months | CAGR_pct | MDD_pct | Sharpe | Calmar | WinRate_pct |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")

    for _, row in performance.iterrows():
        lines.append(
            f"| {row['strategy_name']} | {int(row['months'])} | "
            f"{row['CAGR_pct']:.4f} | {row['MDD_pct']:.4f} | "
            f"{row['Sharpe']:.4f} | {row['Calmar']:.4f} | {row['WinRate_pct']:.4f} |"
        )

    lines.append("")
    lines.append("## 5. 비중 조정 요약")
    lines.append("")
    lines.append("| summary_type | segment | months | adjusted_months | avg_delta_pctp | max_delta_pctp |")
    lines.append("|---|---|---:|---:|---:|---:|")

    for _, row in adjustment_summary.iterrows():
        lines.append(
            f"| {row['summary_type']} | {row['segment']} | {int(row['months'])} | "
            f"{int(row['adjusted_months'])} | {row['avg_delta_pctp']:.4f} | "
            f"{row['max_delta_pctp']:.4f} |"
        )

    lines.append("")
    lines.append("## 6. 보고서용 해석 문장")
    lines.append("")
    lines.append(
        "본 프로젝트에서는 macro companion layer를 HSI 상태분류의 대체 신호로 사용하지 않고, "
        "HSI baseline 비중 위에 소폭의 방어 보정값을 더하는 soft overlay 방식으로만 사용하였다. "
        "매크로 위험 신호가 HSI 위험상태와 동시에 나타날 때는 보정값을 온전히 반영하고, "
        "매크로 위험 신호만 단독으로 나타나는 경우에는 과잉방어를 피하기 위해 보정 강도를 낮추었다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 6. main
# ============================================================

def main() -> None:
    print("=" * 80)
    print("14_macro_companion_overlay_backtest.py 실행 시작")
    print("=" * 80)

    cfg.ensure_final_directories()

    print("[1] 입력 파일 로드")
    baseline_weights = read_csv(INPUT_BASELINE_WEIGHTS, "05번 baseline 비중표")
    macro_joined = read_csv(INPUT_MACRO_JOINED, "13번 HSI-macro joined table")
    monthly_returns = read_csv(INPUT_MONTHLY_RETURNS, "월간 수익률 decimal")

    print(f"    baseline_weights shape = {baseline_weights.shape}")
    print(f"    macro_joined shape      = {macro_joined.shape}")
    print(f"    monthly_returns shape   = {monthly_returns.shape}")

    print("[2] macro-adjusted weights 생성")
    macro_weights = build_macro_overlay_weights(
        baseline_weights,
        macro_joined,
    )
    save_csv(macro_weights, OUTPUT_WEIGHTS)
    print(f"    저장: {OUTPUT_WEIGHTS}")

    print("[3] baseline vs macro overlay 백테스트 계산")
    baseline_clean = prepare_baseline_weights(baseline_weights)
    baseline_clean["macro_data_available"] = 0
    baseline_clean["macro_risk_flag"] = 0
    baseline_clean["macro_defense_addon"] = 0.0
    baseline_clean["macro_hsi_overlap_type"] = "baseline_no_macro_overlay"
    baseline_clean["overlay_strength"] = 0.0
    baseline_clean["macro_overlay_delta"] = 0.0
    baseline_clean["allocation_rule_name"] = "hsi_final_baseline_overlay"

    baseline_bt = calculate_strategy_return(
        baseline_clean,
        monthly_returns,
        STRATEGY_BASELINE,
    )

    macro_bt = calculate_strategy_return(
        macro_weights,
        monthly_returns,
        STRATEGY_MACRO,
    )

    backtest_ts = pd.concat(
        [baseline_bt, macro_bt],
        ignore_index=True,
    )

    backtest_ts = add_cumulative_and_drawdown(backtest_ts)
    save_csv(backtest_ts, OUTPUT_BACKTEST_TS)
    print(f"    저장: {OUTPUT_BACKTEST_TS}")

    print("[4] 성과표 계산")
    performance = build_performance_summary(backtest_ts)
    save_csv(performance, OUTPUT_PERFORMANCE)
    print(f"    저장: {OUTPUT_PERFORMANCE}")

    print("[5] 비중 조정 요약표 계산")
    adjustment_summary = build_adjustment_summary(macro_weights)
    save_csv(adjustment_summary, OUTPUT_ADJUSTMENT_SUMMARY)
    print(f"    저장: {OUTPUT_ADJUSTMENT_SUMMARY}")

    print("[6] 최근 비중표 저장")
    recent_weights = build_recent_weights(macro_weights, n=12)
    save_csv(recent_weights, OUTPUT_RECENT_WEIGHTS)
    print(f"    저장: {OUTPUT_RECENT_WEIGHTS}")

    print("[7] Markdown 노트 저장")
    note = build_note(performance, adjustment_summary)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[성과 요약]")
    print(performance.to_string(index=False))

    print("\n[비중 조정 요약]")
    print(adjustment_summary.to_string(index=False))

    print("\n[최근 12개월 macro overlay weights]")
    preview_cols = [
        YEAR_MONTH_COL,
        RETURN_YEAR_MONTH_COL,
        "hsi_state",
        "macro_data_available",
        "macro_risk_flag",
        "macro_defense_addon",
        "macro_hsi_overlap_type",
        "overlay_strength",
        "macro_overlay_delta",
        f"base_weight_{RISK_ASSET}",
        f"weight_{RISK_ASSET}",
        f"weight_{DEFENSIVE_BOND}",
        f"weight_{DEFENSIVE_CASHLIKE}",
    ]
    print(macro_weights[preview_cols].tail(12).to_string(index=False))

    print("=" * 80)
    print("14_macro_companion_overlay_backtest.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
