from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
11_theta_sensitivity_experiment.py

목적
----
HSI 5상태 분류 민감도 기준인 θ를 바꾸었을 때
상태분포, 성과, MDD, Turnover가 안정적으로 유지되는지 확인한다.

중요
----
θ 실험은 최고 CAGR을 찾기 위한 최적화가 아니다.
HSI 상태분류 기준이 조금 바뀌어도 결과가 크게 무너지지 않는지 확인하는
민감도 검증 절차이다.

입력
----
data/processed/main_final_monthly_signal_inputs_long.csv
data/processed/main_final_monthly_return_decimal.csv

출력
----
data/processed/main_final_theta_hsi_state_table.csv
data/processed/main_final_theta_weights.csv
data/processed/main_final_theta_backtest_timeseries.csv

output/tables/main_final_theta_experiment_grid.csv
output/tables/main_final_theta_state_distribution.csv
output/tables/main_final_theta_performance_summary.csv
output/tables/main_final_theta_turnover_summary.csv
output/tables/main_final_theta_candidate_judgement.csv

docs/main_final_theta_sensitivity_note.md
"""


INPUT_MONTHLY_SIGNAL_LONG = cfg.PROCESSED_DIR / "main_final_monthly_signal_inputs_long.csv"
INPUT_MONTHLY_RETURNS = cfg.PROCESSED_DIR / "main_final_monthly_return_decimal.csv"

OUTPUT_THETA_STATE = cfg.PROCESSED_DIR / "main_final_theta_hsi_state_table.csv"
OUTPUT_THETA_WEIGHTS = cfg.PROCESSED_DIR / "main_final_theta_weights.csv"
OUTPUT_THETA_BACKTEST_TS = cfg.PROCESSED_DIR / "main_final_theta_backtest_timeseries.csv"

OUTPUT_THETA_GRID = cfg.TABLE_DIR / "main_final_theta_experiment_grid.csv"
OUTPUT_STATE_DISTRIBUTION = cfg.TABLE_DIR / "main_final_theta_state_distribution.csv"
OUTPUT_PERFORMANCE = cfg.TABLE_DIR / "main_final_theta_performance_summary.csv"
OUTPUT_TURNOVER = cfg.TABLE_DIR / "main_final_theta_turnover_summary.csv"
OUTPUT_JUDGEMENT = cfg.TABLE_DIR / "main_final_theta_candidate_judgement.csv"

OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_theta_sensitivity_note.md"


YEAR_MONTH_COL = "year_month"
RETURN_YEAR_MONTH_COL = "return_year_month"
TICKER_COL = "ticker"

MARKET_STATE_TICKER = cfg.RISK_TICKER

SCORE_COLS = [
    "score_return",
    "score_ma_pos",
    "score_momentum",
    "score_vol",
    "score_rs",
]

THETA_CANDIDATES = [0.10, 0.15, 0.20, 0.25, 0.30]

SCORE_SCALE = 10.0
ACCIDENT_EXTRA = 0.20
DIRECTION_MARGIN = 0.05
CONFLICT_DIRECTION_BAND = 0.20
MIN_VALID_SCORE_COUNT = 3

EW_STRATEGY_NAME = "EW"


def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")


def read_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{label} 파일이 없습니다: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def normalize_returns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if YEAR_MONTH_COL not in out.columns:
        out = out.rename(columns={out.columns[0]: YEAR_MONTH_COL})

    out[YEAR_MONTH_COL] = out[YEAR_MONTH_COL].astype(str)

    for ticker in cfg.TICKERS:
        if ticker in out.columns:
            out[ticker] = pd.to_numeric(out[ticker], errors="coerce")

    return out


def build_theta_grid() -> pd.DataFrame:
    rows = []

    for theta in THETA_CANDIDATES:
        rows.append({
            "theta_id": f"theta_{theta:.2f}",
            "theta_common": theta,
            "accident_extra": ACCIDENT_EXTRA,
            "conflict_direction_band": CONFLICT_DIRECTION_BAND,
            "score_cols": ", ".join(SCORE_COLS),
            "allocation_rule_name": cfg.FINAL_ALLOCATION_RULE_NAME,
            "purpose": "HSI 상태분류 민감도 검증",
        })

    return pd.DataFrame(rows)


def classify_state(row: pd.Series, theta: float) -> pd.Series:
    scores = pd.to_numeric(row[SCORE_COLS], errors="coerce").dropna()
    valid_score_count = len(scores)

    if valid_score_count < MIN_VALID_SCORE_COUNT:
        return pd.Series({
            "risk_component": np.nan,
            "relief_component": np.nan,
            "state_direction": np.nan,
            "state_intensity": np.nan,
            "valid_score_count": valid_score_count,
            "hsi_state": "insufficient_data",
            "state_reason": "valid_score_count_below_minimum",
        })

    risk_component = scores.clip(lower=0).sum() / (valid_score_count * SCORE_SCALE)
    relief_component = (-scores.clip(upper=0)).sum() / (valid_score_count * SCORE_SCALE)

    state_direction = risk_component - relief_component
    state_intensity = risk_component + relief_component

    if risk_component >= theta + ACCIDENT_EXTRA and state_direction > 0:
        hsi_state = "accident_zone"
        reason = "risk_component_above_accident_threshold"
    elif (
        risk_component >= theta
        and relief_component >= theta
        and abs(state_direction) <= CONFLICT_DIRECTION_BAND
    ):
        hsi_state = "conflict"
        reason = "risk_and_relief_components_both_active"
    elif risk_component >= theta and state_direction > DIRECTION_MARGIN:
        hsi_state = "risk_warning"
        reason = "risk_component_dominant"
    elif relief_component >= theta and state_direction < -DIRECTION_MARGIN:
        hsi_state = "risk_relief"
        reason = "relief_component_dominant"
    else:
        hsi_state = "neutral_watch"
        reason = "weak_or_balanced_signal"

    return pd.Series({
        "risk_component": risk_component,
        "relief_component": relief_component,
        "state_direction": state_direction,
        "state_intensity": state_intensity,
        "valid_score_count": valid_score_count,
        "hsi_state": hsi_state,
        "state_reason": reason,
    })


def build_theta_state_table(monthly_long: pd.DataFrame) -> pd.DataFrame:
    df = monthly_long.copy()
    df[TICKER_COL] = df[TICKER_COL].astype(str).str.zfill(6)

    market_df = df[df[TICKER_COL] == MARKET_STATE_TICKER].copy()

    if market_df.empty:
        raise ValueError(f"{MARKET_STATE_TICKER} 기준 월말 신호가 없습니다.")

    for col in SCORE_COLS:
        if col not in market_df.columns:
            market_df[col] = np.nan

    all_rows = []

    for theta in THETA_CANDIDATES:
        state_features = market_df.apply(lambda row: classify_state(row, theta), axis=1)

        keep_cols = [
            YEAR_MONTH_COL,
            TICKER_COL,
            "ticker_name",
            "ticker_role",
            "score_date",
            "hsi_direction",
            "raw3_signal",
        ] + SCORE_COLS

        keep_cols = [c for c in keep_cols if c in market_df.columns]

        out = pd.concat(
            [
                market_df[keep_cols].reset_index(drop=True),
                state_features.reset_index(drop=True),
            ],
            axis=1,
        )

        out["theta_id"] = f"theta_{theta:.2f}"
        out["theta_common"] = theta
        out["state_kr"] = out["hsi_state"].map(cfg.HSI_STATE_KR)
        out["state_rule_version"] = "theta_state5_sensitivity_v1"

        all_rows.append(out)

    return pd.concat(all_rows, ignore_index=True)


def get_target_weight(hsi_state: str) -> dict:
    if hsi_state in cfg.FINAL_BASELINE_ALLOCATION_RULES:
        rule = cfg.FINAL_BASELINE_ALLOCATION_RULES[hsi_state]
    else:
        rule = cfg.FINAL_BASELINE_ALLOCATION_RULES["neutral_watch"]

    return {ticker: float(rule[ticker]) for ticker in cfg.TICKERS}


def build_theta_weights(theta_state: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in theta_state.iterrows():
        weight = get_target_weight(row["hsi_state"])

        item = {
            "strategy_name": row["theta_id"],
            "theta_id": row["theta_id"],
            "theta_common": row["theta_common"],
            YEAR_MONTH_COL: row[YEAR_MONTH_COL],
            RETURN_YEAR_MONTH_COL: str(pd.Period(row[YEAR_MONTH_COL], freq="M") + 1),
            "hsi_state": row["hsi_state"],
            "state_kr": row["state_kr"],
            "allocation_rule_name": cfg.FINAL_ALLOCATION_RULE_NAME,
        }

        for ticker in cfg.TICKERS:
            item[f"weight_{ticker}"] = weight[ticker]

        rows.append(item)

    weights = pd.DataFrame(rows)
    weights = weights.sort_values(["strategy_name", YEAR_MONTH_COL]).reset_index(drop=True)

    weight_cols = [f"weight_{ticker}" for ticker in cfg.TICKERS]
    weights["turnover"] = (
        weights
        .groupby("strategy_name")[weight_cols]
        .diff()
        .abs()
        .sum(axis=1)
        * 0.5
    )
    weights["turnover"] = weights["turnover"].fillna(0.0)

    return weights


def build_ew_weights(signal_months: list[str]) -> pd.DataFrame:
    rows = []

    for ym in signal_months:
        item = {
            "strategy_name": EW_STRATEGY_NAME,
            "theta_id": "EW",
            "theta_common": np.nan,
            YEAR_MONTH_COL: ym,
            RETURN_YEAR_MONTH_COL: str(pd.Period(ym, freq="M") + 1),
            "hsi_state": "EW",
            "state_kr": "동일가중",
            "allocation_rule_name": "equal_weight",
            "turnover": 0.0,
        }

        for ticker in cfg.TICKERS:
            item[f"weight_{ticker}"] = 1.0 / len(cfg.TICKERS)

        rows.append(item)

    return pd.DataFrame(rows)


def calculate_strategy_return(weights: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    ret = returns.copy().rename(columns={YEAR_MONTH_COL: RETURN_YEAR_MONTH_COL})
    merged = weights.merge(ret, on=RETURN_YEAR_MONTH_COL, how="left")

    for ticker in cfg.TICKERS:
        merged[f"return_{ticker}"] = pd.to_numeric(merged[ticker], errors="coerce")
        merged[f"contribution_{ticker}"] = merged[f"weight_{ticker}"] * merged[f"return_{ticker}"]

    contribution_cols = [f"contribution_{ticker}" for ticker in cfg.TICKERS]
    merged["strategy_return"] = merged[contribution_cols].sum(axis=1)

    keep_cols = [
        "strategy_name",
        "theta_id",
        "theta_common",
        YEAR_MONTH_COL,
        RETURN_YEAR_MONTH_COL,
        "hsi_state",
        "state_kr",
        "strategy_return",
        "turnover",
    ]

    for ticker in cfg.TICKERS:
        keep_cols += [f"weight_{ticker}", f"return_{ticker}", f"contribution_{ticker}"]

    out = merged[keep_cols].dropna(subset=["strategy_return"]).reset_index(drop=True)
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
    cagr = final_cum ** (12 / months) - 1
    ann_vol = r.std(ddof=1) * np.sqrt(12) if months > 1 else np.nan
    ann_mean = r.mean() * 12
    sharpe = ann_mean / ann_vol if pd.notna(ann_vol) and ann_vol != 0 else np.nan

    downside = r[r < 0]
    downside_vol = downside.std(ddof=1) * np.sqrt(12) if len(downside) > 1 else np.nan
    sortino = ann_mean / downside_vol if pd.notna(downside_vol) and downside_vol != 0 else np.nan

    mdd = g["drawdown"].min()
    calmar = cagr / abs(mdd) if pd.notna(mdd) and mdd < 0 else np.nan

    return {
        "strategy_name": g["strategy_name"].iloc[0],
        "theta_id": g["theta_id"].iloc[0],
        "theta_common": g["theta_common"].iloc[0],
        "months": months,
        "final_cumulative_return": final_cum,
        "CAGR_pct": cagr * 100,
        "annual_volatility_pct": ann_vol * 100 if pd.notna(ann_vol) else np.nan,
        "MDD_pct": mdd * 100 if pd.notna(mdd) else np.nan,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Calmar": calmar,
        "WinRate_pct": (r > 0).mean() * 100,
    }


def build_performance_summary(backtest_ts: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, group in backtest_ts.groupby("strategy_name"):
        rows.append(calc_performance(group))

    return pd.DataFrame(rows)


def build_turnover_summary(backtest_ts: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for strategy, group in backtest_ts.groupby("strategy_name"):
        t = group["turnover"].fillna(0)

        rows.append({
            "strategy_name": strategy,
            "theta_id": group["theta_id"].iloc[0],
            "theta_common": group["theta_common"].iloc[0],
            "months": len(group),
            "avg_turnover_pct": t.mean() * 100,
            "max_turnover_pct": t.max() * 100,
            "total_turnover_pct": t.sum() * 100,
            "nonzero_turnover_months": int((t > 0).sum()),
        })

    return pd.DataFrame(rows)


def build_state_distribution(theta_state: pd.DataFrame) -> pd.DataFrame:
    dist = (
        theta_state
        .groupby(["theta_id", "theta_common", "hsi_state", "state_kr"])
        .size()
        .reset_index(name="months")
    )

    total = theta_state.groupby("theta_id").size().reset_index(name="total_months")
    dist = dist.merge(total, on="theta_id", how="left")
    dist["ratio"] = dist["months"] / dist["total_months"]

    return dist.sort_values(["theta_common", "hsi_state"]).reset_index(drop=True)


def build_candidate_judgement(performance: pd.DataFrame, turnover: pd.DataFrame) -> pd.DataFrame:
    merged = performance.merge(
        turnover[["strategy_name", "avg_turnover_pct", "max_turnover_pct"]],
        on="strategy_name",
        how="left",
    )

    baseline = merged[merged["strategy_name"] == "theta_0.15"].iloc[0]

    rows = []

    for _, row in merged.iterrows():
        if row["strategy_name"] == EW_STRATEGY_NAME:
            decision = "benchmark"
            reason = "동일가중 비교 기준"
            cagr_change = np.nan
            mdd_change = np.nan
            turnover_change = np.nan
        else:
            cagr_change = row["CAGR_pct"] - baseline["CAGR_pct"]
            mdd_change = row["MDD_pct"] - baseline["MDD_pct"]
            turnover_change = row["avg_turnover_pct"] - baseline["avg_turnover_pct"]

            if row["strategy_name"] == "theta_0.15":
                decision = "baseline_theta"
                reason = "기준 θ"
            elif abs(mdd_change) <= 2.0 and row["avg_turnover_pct"] <= 8.0:
                decision = "stable_candidate"
                reason = "기준 θ 주변에서 MDD와 Turnover가 크게 무너지지 않음"
            elif row["avg_turnover_pct"] > 8.0:
                decision = "review_turnover"
                reason = "상태 전환이 잦아 Turnover 확인 필요"
            else:
                decision = "review"
                reason = "기준 θ 대비 성과·위험 변화 검토 필요"

        rows.append({
            "strategy_name": row["strategy_name"],
            "theta_common": row["theta_common"],
            "CAGR_change_vs_theta015_pct": cagr_change,
            "MDD_change_vs_theta015_pct": mdd_change,
            "avg_turnover_change_vs_theta015_pct": turnover_change,
            "decision": decision,
            "reason": reason,
        })

    return pd.DataFrame(rows)


def build_note(performance: pd.DataFrame, turnover: pd.DataFrame, judgement: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_final θ 민감도 실험 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "θ 실험은 최고 CAGR을 찾는 최적화가 아니라, HSI 상태분류 기준이 조금 바뀌어도 "
        "상태분포, MDD, Turnover, Sharpe, Calmar가 크게 무너지지 않는지 확인하는 민감도 검증이다."
    )
    lines.append("")
    lines.append("## 2. θ 후보")
    lines.append("")
    lines.append(f"- 후보: {THETA_CANDIDATES}")
    lines.append("- 기준값: 0.15")
    lines.append("")
    lines.append("## 3. 성과 요약")
    lines.append("")
    lines.append("| strategy | theta | CAGR_pct | MDD_pct | Sharpe | Calmar |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for _, row in performance.iterrows():
        theta = "" if pd.isna(row["theta_common"]) else f"{row['theta_common']:.2f}"
        lines.append(
            f"| {row['strategy_name']} | {theta} | {row['CAGR_pct']:.4f} | "
            f"{row['MDD_pct']:.4f} | {row['Sharpe']:.4f} | {row['Calmar']:.4f} |"
        )
    lines.append("")
    lines.append("## 4. 후보 판단")
    lines.append("")
    for _, row in judgement.iterrows():
        lines.append(f"- {row['strategy_name']}: {row['decision']} — {row['reason']}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("11_theta_sensitivity_experiment.py 실행 시작")
    print("=" * 80)

    cfg.ensure_final_directories()

    print("[1] 입력 파일 로드")
    monthly_long = read_csv(INPUT_MONTHLY_SIGNAL_LONG, "월말 HSI signal long")
    monthly_returns = normalize_returns(read_csv(INPUT_MONTHLY_RETURNS, "월간 수익률 decimal"))
    print(f"    monthly_long shape = {monthly_long.shape}")
    print(f"    monthly_returns shape = {monthly_returns.shape}")

    print("[2] θ grid 저장")
    theta_grid = build_theta_grid()
    save_csv(theta_grid, OUTPUT_THETA_GRID)
    print(f"    저장: {OUTPUT_THETA_GRID}")

    print("[3] θ별 HSI 상태표 생성")
    theta_state = build_theta_state_table(monthly_long)
    save_csv(theta_state, OUTPUT_THETA_STATE)
    print(f"    저장: {OUTPUT_THETA_STATE}")

    print("[4] θ별 비중표 생성")
    theta_weights = build_theta_weights(theta_state)
    ew_weights = build_ew_weights(sorted(theta_state[YEAR_MONTH_COL].astype(str).unique().tolist()))
    all_weights = pd.concat([ew_weights, theta_weights], ignore_index=True)

    save_csv(all_weights, OUTPUT_THETA_WEIGHTS)
    print(f"    저장: {OUTPUT_THETA_WEIGHTS}")

    print("[5] 백테스트 실행")
    backtest_ts = calculate_strategy_return(all_weights, monthly_returns)
    backtest_ts = add_cumulative_and_drawdown(backtest_ts)

    save_csv(backtest_ts, OUTPUT_THETA_BACKTEST_TS)
    print(f"    저장: {OUTPUT_THETA_BACKTEST_TS}")

    print("[6] 요약표 생성")
    state_dist = build_state_distribution(theta_state)
    performance = build_performance_summary(backtest_ts)
    turnover = build_turnover_summary(backtest_ts)
    judgement = build_candidate_judgement(performance, turnover)

    save_csv(state_dist, OUTPUT_STATE_DISTRIBUTION)
    save_csv(performance, OUTPUT_PERFORMANCE)
    save_csv(turnover, OUTPUT_TURNOVER)
    save_csv(judgement, OUTPUT_JUDGEMENT)

    print(f"    저장: {OUTPUT_STATE_DISTRIBUTION}")
    print(f"    저장: {OUTPUT_PERFORMANCE}")
    print(f"    저장: {OUTPUT_TURNOVER}")
    print(f"    저장: {OUTPUT_JUDGEMENT}")

    print("[7] Markdown 노트 저장")
    note = build_note(performance, turnover, judgement)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[성과 요약]")
    print(performance.to_string(index=False))

    print("\n[후보 판단]")
    print(judgement.to_string(index=False))

    print("=" * 80)
    print("11_theta_sensitivity_experiment.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()