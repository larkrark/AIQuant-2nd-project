from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
09_event_balance_filter_backtest.py

목적
----
사건균형지표를 HSI 상태를 대체하는 신호가 아니라
상태별 목표 비중에 ±5~10%p 보조 조정하는 필터로 제한하여 실험한다.

핵심 원칙
---------
1. HSI 5상태가 기본 비중을 결정한다.
2. 사건균형지표는 기본 비중을 뒤집지 않는다.
3. 위험 누적이 강하면 위험자산에서 현금성 자산으로 일부 이동한다.
4. 완화 누적이 강하면 현금성 자산에서 위험자산으로 일부 이동한다.
5. 조정폭은 5~10%p로 제한한다.

입력
----
data/processed/main_final_hsi_state5_table.csv
data/processed/main_final_hsi_event_balance_monthly.csv
data/processed/main_final_monthly_return_decimal.csv

출력
----
data/processed/main_final_event_balance_filter_weights.csv
data/processed/main_final_event_balance_filter_backtest_timeseries.csv

output/tables/main_final_event_balance_filter_adjustment_detail.csv
output/tables/main_final_event_balance_filter_performance_summary.csv
output/tables/main_final_event_balance_filter_turnover_summary.csv
output/tables/main_final_event_balance_filter_judgement.csv

docs/main_final_event_balance_filter_backtest_note.md
"""


INPUT_STATE_TABLE = cfg.PROCESSED_DIR / "main_final_hsi_state5_table.csv"
INPUT_EVENT_BALANCE = cfg.PROCESSED_DIR / "main_final_hsi_event_balance_monthly.csv"
INPUT_MONTHLY_RETURNS = cfg.PROCESSED_DIR / "main_final_monthly_return_decimal.csv"

OUTPUT_WEIGHTS = cfg.PROCESSED_DIR / "main_final_event_balance_filter_weights.csv"
OUTPUT_BACKTEST_TS = cfg.PROCESSED_DIR / "main_final_event_balance_filter_backtest_timeseries.csv"

OUTPUT_ADJUSTMENT_DETAIL = cfg.TABLE_DIR / "main_final_event_balance_filter_adjustment_detail.csv"
OUTPUT_PERFORMANCE = cfg.TABLE_DIR / "main_final_event_balance_filter_performance_summary.csv"
OUTPUT_TURNOVER = cfg.TABLE_DIR / "main_final_event_balance_filter_turnover_summary.csv"
OUTPUT_JUDGEMENT = cfg.TABLE_DIR / "main_final_event_balance_filter_judgement.csv"

OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_event_balance_filter_backtest_note.md"


YEAR_MONTH_COL = "year_month"
RETURN_YEAR_MONTH_COL = "return_year_month"

STRATEGY_EW = "EW"
STRATEGY_BASELINE = "HSI_final_baseline_overlay"
STRATEGY_EVENT_FILTER = "HSI_event_balance_filter_overlay"

RISK_BALANCE_STRONG = 0.20
RISK_BALANCE_WEAK = 0.10
RELIEF_BALANCE_STRONG = -0.20
RELIEF_BALANCE_WEAK = -0.10
INTENSITY_MIN = 0.20

ADJUST_SMALL = 0.05
ADJUST_LARGE = 0.10


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
        out = out.rename(columns={out.columns[0]: YEAR_MONTH_COL})
    out[YEAR_MONTH_COL] = out[YEAR_MONTH_COL].astype(str)
    return out


def normalize_returns(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_year_month(df)

    for ticker in cfg.TICKERS:
        if ticker in out.columns:
            out[ticker] = pd.to_numeric(out[ticker], errors="coerce")

    return out


def get_base_weight(hsi_state: str) -> dict:
    if hsi_state in cfg.FINAL_BASELINE_ALLOCATION_RULES:
        rule = cfg.FINAL_BASELINE_ALLOCATION_RULES[hsi_state]
    else:
        rule = cfg.FINAL_BASELINE_ALLOCATION_RULES["neutral_watch"]

    return {ticker: float(rule[ticker]) for ticker in cfg.TICKERS}


def decide_event_adjustment(event_balance: float, event_intensity: float) -> tuple[float, str]:
    """
    반환값
    ------
    adjustment:
        양수면 위험자산 → 현금성자산 이동
        음수면 현금성자산 → 위험자산 이동

    label:
        조정 사유
    """
    if pd.isna(event_balance) or pd.isna(event_intensity):
        return 0.0, "no_adjustment_missing_event_balance"

    if event_intensity < INTENSITY_MIN:
        return 0.0, "no_adjustment_low_intensity"

    if event_balance >= RISK_BALANCE_STRONG:
        return ADJUST_LARGE, "large_risk_to_cash_adjustment"

    if event_balance >= RISK_BALANCE_WEAK:
        return ADJUST_SMALL, "small_risk_to_cash_adjustment"

    if event_balance <= RELIEF_BALANCE_STRONG:
        return -ADJUST_LARGE, "large_cash_to_risk_adjustment"

    if event_balance <= RELIEF_BALANCE_WEAK:
        return -ADJUST_SMALL, "small_cash_to_risk_adjustment"

    return 0.0, "no_adjustment_mixed_or_neutral"


def apply_adjustment(base_weight: dict, adjustment: float) -> dict:
    w = base_weight.copy()

    if adjustment > 0:
        move = min(adjustment, w[cfg.RISK_TICKER])
        w[cfg.RISK_TICKER] -= move
        w[cfg.CASH_TICKER] += move

    elif adjustment < 0:
        move = min(abs(adjustment), w[cfg.CASH_TICKER])
        w[cfg.CASH_TICKER] -= move
        w[cfg.RISK_TICKER] += move

    total = sum(w.values())

    if total != 0:
        w = {k: v / total for k, v in w.items()}

    return w


def build_weight_tables(state_table: pd.DataFrame, event_balance: pd.DataFrame) -> pd.DataFrame:
    state = normalize_year_month(state_table)
    event = normalize_year_month(event_balance)

    event_like_cols = [
        col for col in state.columns
        if col.startswith("event_balance_")
        or col.startswith("event_intensity_")
    ]

    state = state.drop(columns=event_like_cols, errors="ignore")

    keep_event_cols = [
        YEAR_MONTH_COL,
        "event_balance_13612w",
        "event_intensity_13612w",
        "event_balance_13612w_label",
        "event_intensity_13612w_label",
    ]

    keep_event_cols = [c for c in keep_event_cols if c in event.columns]

    merged = state.merge(
        event[keep_event_cols],
        on=YEAR_MONTH_COL,
        how="left",
    )

    rows = []

    for _, row in merged.iterrows():
        base_w = get_base_weight(row["hsi_state"])

        adjustment, adjustment_label = decide_event_adjustment(
            row.get("event_balance_13612w", np.nan),
            row.get("event_intensity_13612w", np.nan),
        )

        adjusted_w = apply_adjustment(base_w, adjustment)

        for strategy_name, weight, strategy_note in [
            (STRATEGY_BASELINE, base_w, "HSI 상태별 목표 비중만 적용"),
            (STRATEGY_EVENT_FILTER, adjusted_w, "HSI 상태별 목표 비중에 사건균형 보조 필터 적용"),
        ]:
            item = {
                "strategy_name": strategy_name,
                YEAR_MONTH_COL: row[YEAR_MONTH_COL],
                RETURN_YEAR_MONTH_COL: str(pd.Period(row[YEAR_MONTH_COL], freq="M") + 1),
                "hsi_state": row["hsi_state"],
                "state_kr": row.get("state_kr", ""),
                "event_balance_13612w": row.get("event_balance_13612w", np.nan),
                "event_intensity_13612w": row.get("event_intensity_13612w", np.nan),
                "event_balance_13612w_label": row.get("event_balance_13612w_label", ""),
                "event_intensity_13612w_label": row.get("event_intensity_13612w_label", ""),
                "event_adjustment": adjustment if strategy_name == STRATEGY_EVENT_FILTER else 0.0,
                "adjustment_label": adjustment_label if strategy_name == STRATEGY_EVENT_FILTER else "baseline_no_event_filter",
                "strategy_note": strategy_note,
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
            "strategy_name": STRATEGY_EW,
            YEAR_MONTH_COL: ym,
            RETURN_YEAR_MONTH_COL: str(pd.Period(ym, freq="M") + 1),
            "hsi_state": "EW",
            "state_kr": "동일가중",
            "event_balance_13612w": np.nan,
            "event_intensity_13612w": np.nan,
            "event_balance_13612w_label": "",
            "event_intensity_13612w_label": "",
            "event_adjustment": 0.0,
            "adjustment_label": "equal_weight",
            "strategy_note": "동일가중 비교 기준",
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
        YEAR_MONTH_COL,
        RETURN_YEAR_MONTH_COL,
        "hsi_state",
        "state_kr",
        "event_balance_13612w",
        "event_intensity_13612w",
        "event_adjustment",
        "adjustment_label",
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
        g["cumulative_return"] = (1 + g["strategy_return"]).cumprod()
        g["running_max"] = g["cumulative_return"].cummax()
        g["drawdown"] = g["cumulative_return"] / g["running_max"] - 1
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
            "months": len(group),
            "avg_turnover_pct": t.mean() * 100,
            "max_turnover_pct": t.max() * 100,
            "total_turnover_pct": t.sum() * 100,
            "nonzero_turnover_months": int((t > 0).sum()),
        })

    return pd.DataFrame(rows)


def build_adjustment_detail(weights: pd.DataFrame) -> pd.DataFrame:
    event_filter = weights[weights["strategy_name"] == STRATEGY_EVENT_FILTER].copy()

    detail = (
        event_filter
        .groupby("adjustment_label")
        .agg(
            months=(YEAR_MONTH_COL, "count"),
            avg_adjustment=("event_adjustment", "mean"),
            min_adjustment=("event_adjustment", "min"),
            max_adjustment=("event_adjustment", "max"),
            avg_event_balance=("event_balance_13612w", "mean"),
            avg_event_intensity=("event_intensity_13612w", "mean"),
        )
        .reset_index()
    )

    return detail


def build_judgement(performance: pd.DataFrame, turnover: pd.DataFrame) -> pd.DataFrame:
    merged = performance.merge(turnover, on="strategy_name", how="left")

    base = merged[merged["strategy_name"] == STRATEGY_BASELINE].iloc[0]
    event = merged[merged["strategy_name"] == STRATEGY_EVENT_FILTER].iloc[0]

    mdd_change = event["MDD_pct"] - base["MDD_pct"]
    cagr_change = event["CAGR_pct"] - base["CAGR_pct"]
    turnover_change = event["avg_turnover_pct"] - base["avg_turnover_pct"]

    if mdd_change > 0 and turnover_change <= 0:
        decision = "candidate"
        reason = "baseline 대비 MDD가 개선되고 평균 Turnover가 증가하지 않음"
    elif mdd_change > 0:
        decision = "review"
        reason = "MDD는 개선되었으나 Turnover 증가 여부를 검토해야 함"
    else:
        decision = "hold_as_diagnostic"
        reason = "전략 필터보다는 사건균형 진단지표로 유지하는 것이 안전"

    rows = [
        {
            "comparison": f"{STRATEGY_EVENT_FILTER} vs {STRATEGY_BASELINE}",
            "CAGR_change_pct": cagr_change,
            "MDD_change_pct": mdd_change,
            "avg_turnover_change_pct": turnover_change,
            "decision": decision,
            "reason": reason,
        }
    ]

    return pd.DataFrame(rows)


def build_note(performance: pd.DataFrame, judgement: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_final 사건균형 보조 필터 백테스트 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 단계는 사건균형지표를 HSI 상태를 대체하는 신호가 아니라, "
        "상태별 목표 비중을 ±5~10%p 범위에서 보정하는 보조 필터로 제한해 실험한다."
    )
    lines.append("")
    lines.append("## 2. 보조 필터 원칙")
    lines.append("")
    lines.append("- 위험 누적이 강하면 069500에서 153130으로 일부 이동한다.")
    lines.append("- 완화 누적이 강하면 153130에서 069500으로 일부 이동한다.")
    lines.append("- 사건균형지표는 기본 HSI 상태를 뒤집지 않는다.")
    lines.append("")
    lines.append("## 3. 성과 요약")
    lines.append("")
    lines.append("| strategy | CAGR_pct | MDD_pct | Sharpe | Calmar |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, row in performance.iterrows():
        lines.append(
            f"| {row['strategy_name']} | {row['CAGR_pct']:.4f} | "
            f"{row['MDD_pct']:.4f} | {row['Sharpe']:.4f} | {row['Calmar']:.4f} |"
        )
    lines.append("")
    lines.append("## 4. 판단")
    lines.append("")
    for _, row in judgement.iterrows():
        lines.append(f"- {row['comparison']}: {row['decision']} — {row['reason']}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("09_event_balance_filter_backtest.py 실행 시작")
    print("=" * 80)

    cfg.ensure_final_directories()

    print("[1] 입력 파일 로드")
    state_table = read_csv(INPUT_STATE_TABLE, "HSI 5상태표")
    event_balance = read_csv(INPUT_EVENT_BALANCE, "월말 사건균형지표")
    monthly_returns = normalize_returns(read_csv(INPUT_MONTHLY_RETURNS, "월간 수익률 decimal"))

    print(f"    state_table shape = {state_table.shape}")
    print(f"    event_balance shape = {event_balance.shape}")
    print(f"    monthly_returns shape = {monthly_returns.shape}")

    print("[2] baseline / event filter 비중표 생성")
    weights = build_weight_tables(state_table, event_balance)

    ew_weights = build_ew_weights(sorted(state_table[YEAR_MONTH_COL].astype(str).unique().tolist()))
    all_weights = pd.concat([ew_weights, weights], ignore_index=True)

    save_csv(all_weights, OUTPUT_WEIGHTS)
    print(f"    저장: {OUTPUT_WEIGHTS}")

    print("[3] 백테스트 실행")
    backtest_ts = calculate_strategy_return(all_weights, monthly_returns)
    backtest_ts = add_cumulative_and_drawdown(backtest_ts)

    save_csv(backtest_ts, OUTPUT_BACKTEST_TS)
    print(f"    저장: {OUTPUT_BACKTEST_TS}")

    print("[4] 요약표 생성")
    adjustment_detail = build_adjustment_detail(all_weights)
    performance = build_performance_summary(backtest_ts)
    turnover = build_turnover_summary(backtest_ts)
    judgement = build_judgement(performance, turnover)

    save_csv(adjustment_detail, OUTPUT_ADJUSTMENT_DETAIL)
    save_csv(performance, OUTPUT_PERFORMANCE)
    save_csv(turnover, OUTPUT_TURNOVER)
    save_csv(judgement, OUTPUT_JUDGEMENT)

    print(f"    저장: {OUTPUT_ADJUSTMENT_DETAIL}")
    print(f"    저장: {OUTPUT_PERFORMANCE}")
    print(f"    저장: {OUTPUT_TURNOVER}")
    print(f"    저장: {OUTPUT_JUDGEMENT}")

    print("[5] Markdown 노트 저장")
    note = build_note(performance, judgement)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[성과 요약]")
    print(performance.to_string(index=False))

    print("\n[Turnover 요약]")
    print(turnover.to_string(index=False))

    print("\n[조정 상세]")
    print(adjustment_detail.to_string(index=False))

    print("\n[판단]")
    print(judgement.to_string(index=False))

    print("=" * 80)
    print("09_event_balance_filter_backtest.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()