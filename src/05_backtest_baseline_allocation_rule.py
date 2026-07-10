from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
05_backtest_baseline_allocation_rule.py

목적
----
04번에서 만든 HSI 5상태표를 최종 baseline 리밸런싱 규칙과 연결해
EW 전략과 HSI overlay 전략을 비교한다.

핵심 구조
---------
월말 HSI 상태 t
→ 다음 달 목표 ETF 비중 적용
→ 다음 달 월간 수익률 계산
→ 누적수익률, Drawdown, Turnover, 성과지표 계산

입력
----
data/processed/main_final_hsi_state5_table.csv
data/processed/main_final_monthly_return_decimal.csv
output/tables/main_final_allocation_rule_table.csv

출력
----
data/processed/main_final_baseline_rebalance_weights.csv
data/processed/main_final_baseline_backtest_timeseries.csv

output/tables/main_final_baseline_alignment_check.csv
output/tables/main_final_baseline_performance_summary.csv
output/tables/main_final_baseline_turnover_summary.csv

docs/main_final_baseline_backtest_note.md
"""


INPUT_STATE_TABLE = cfg.PROCESSED_DIR / "main_final_hsi_state5_table.csv"
INPUT_MONTHLY_RETURNS = cfg.PROCESSED_DIR / "main_final_monthly_return_decimal.csv"
INPUT_ALLOCATION_RULE = cfg.TABLE_DIR / "main_final_allocation_rule_table.csv"

OUTPUT_WEIGHTS = cfg.PROCESSED_DIR / "main_final_baseline_rebalance_weights.csv"
OUTPUT_BACKTEST_TS = cfg.PROCESSED_DIR / "main_final_baseline_backtest_timeseries.csv"

OUTPUT_ALIGNMENT_CHECK = cfg.TABLE_DIR / "main_final_baseline_alignment_check.csv"
OUTPUT_PERFORMANCE = cfg.TABLE_DIR / "main_final_baseline_performance_summary.csv"
OUTPUT_TURNOVER = cfg.TABLE_DIR / "main_final_baseline_turnover_summary.csv"
OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_baseline_backtest_note.md"


YEAR_MONTH_COL = "year_month"
RETURN_YEAR_MONTH_COL = "return_year_month"

STRATEGY_EW = "EW"
STRATEGY_HSI = "HSI_final_baseline_overlay"


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
        first_col = out.columns[0]
        out = out.rename(columns={first_col: YEAR_MONTH_COL})

    out[YEAR_MONTH_COL] = out[YEAR_MONTH_COL].astype(str)

    for ticker in cfg.TICKERS:
        if ticker in out.columns:
            out[ticker] = pd.to_numeric(out[ticker], errors="coerce")

    return out


def build_allocation_map() -> dict:
    rule_map = {}

    for state, rule in cfg.FINAL_BASELINE_ALLOCATION_RULES.items():
        rule_map[state] = {
            ticker: float(rule[ticker])
            for ticker in cfg.TICKERS
        }

    return rule_map


def get_target_weight(hsi_state: str, allocation_map: dict) -> dict:
    if hsi_state in allocation_map:
        return allocation_map[hsi_state]

    return allocation_map["neutral_watch"]


def build_rebalance_weights(state_table: pd.DataFrame) -> pd.DataFrame:
    allocation_map = build_allocation_map()

    rows = []

    for _, row in state_table.iterrows():
        state = row["hsi_state"]
        weight = get_target_weight(state, allocation_map)

        item = {
            YEAR_MONTH_COL: row[YEAR_MONTH_COL],
            RETURN_YEAR_MONTH_COL: str(pd.Period(row[YEAR_MONTH_COL], freq="M") + 1),
            "hsi_state": state,
            "state_kr": row.get("state_kr", ""),
            "allocation_rule_name": cfg.FINAL_ALLOCATION_RULE_NAME,
        }

        for ticker in cfg.TICKERS:
            item[f"weight_{ticker}"] = weight[ticker]

        rows.append(item)

    weights = pd.DataFrame(rows)

    weight_cols = [f"weight_{ticker}" for ticker in cfg.TICKERS]
    weights = weights.sort_values(YEAR_MONTH_COL).reset_index(drop=True)

    turnover = weights[weight_cols].diff().abs().sum(axis=1) * 0.5
    turnover.iloc[0] = 0.0

    weights["turnover"] = turnover

    return weights


def build_ew_weights(weights: pd.DataFrame) -> pd.DataFrame:
    ew = weights[[YEAR_MONTH_COL, RETURN_YEAR_MONTH_COL, "hsi_state", "state_kr"]].copy()
    ew["allocation_rule_name"] = "equal_weight"

    for ticker in cfg.TICKERS:
        ew[f"weight_{ticker}"] = 1.0 / len(cfg.TICKERS)

    ew["turnover"] = 0.0

    return ew


def calculate_strategy_return(weights: pd.DataFrame, returns: pd.DataFrame, strategy_name: str) -> pd.DataFrame:
    ret = returns.copy()

    ret = ret.rename(columns={YEAR_MONTH_COL: RETURN_YEAR_MONTH_COL})

    merged = weights.merge(ret, on=RETURN_YEAR_MONTH_COL, how="left")

    for ticker in cfg.TICKERS:
        merged[f"return_{ticker}"] = pd.to_numeric(merged[ticker], errors="coerce")
        merged[f"contribution_{ticker}"] = merged[f"weight_{ticker}"] * merged[f"return_{ticker}"]

    contribution_cols = [f"contribution_{ticker}" for ticker in cfg.TICKERS]

    merged["strategy_return"] = merged[contribution_cols].sum(axis=1)
    merged["strategy_name"] = strategy_name

    keep_cols = [
        "strategy_name",
        YEAR_MONTH_COL,
        RETURN_YEAR_MONTH_COL,
        "hsi_state",
        "state_kr",
        "allocation_rule_name",
        "strategy_return",
        "turnover",
    ]

    for ticker in cfg.TICKERS:
        keep_cols += [f"weight_{ticker}", f"return_{ticker}", f"contribution_{ticker}"]

    out = merged[keep_cols].copy()

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
    sharpe = ann_return_mean / ann_vol if ann_vol and ann_vol != 0 else np.nan

    downside = r[r < 0]
    downside_vol = downside.std(ddof=1) * np.sqrt(12) if len(downside) > 1 else np.nan
    sortino = ann_return_mean / downside_vol if downside_vol and downside_vol != 0 else np.nan

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


def build_alignment_check(weights: pd.DataFrame, backtest_ts: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    return_cols = [t for t in cfg.TICKERS if t in returns.columns]

    rows = [
        {
            "item": "signal_months",
            "value": weights[YEAR_MONTH_COL].nunique(),
            "status": "OK",
            "note": "HSI 상태가 존재하는 월 수",
        },
        {
            "item": "return_months",
            "value": returns[YEAR_MONTH_COL].nunique(),
            "status": "OK",
            "note": "월간 수익률 decimal 월 수",
        },
        {
            "item": "backtest_months_hsi",
            "value": backtest_ts[backtest_ts["strategy_name"] == STRATEGY_HSI][RETURN_YEAR_MONTH_COL].nunique(),
            "status": "OK",
            "note": "HSI overlay 백테스트에 실제 사용된 월 수",
        },
        {
            "item": "alignment_rule",
            "value": cfg.ALIGNMENT_RULE,
            "status": "OK",
            "note": "월말 신호 t를 다음 달 수익률 t+1에 적용",
        },
        {
            "item": "return_columns_used",
            "value": ", ".join(return_cols),
            "status": "OK" if set(cfg.TICKERS).issubset(set(return_cols)) else "CHECK",
            "note": "백테스트 수익률 컬럼",
        },
    ]

    return pd.DataFrame(rows)


def build_note(performance: pd.DataFrame, turnover: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_final baseline HSI overlay 백테스트 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 단계는 HSI 5상태를 최종 baseline 리밸런싱 규칙과 연결하여 "
        "EW 전략 대비 성과, Drawdown, Turnover를 비교한다."
    )
    lines.append("")
    lines.append("## 2. 시점 정합성")
    lines.append("")
    lines.append(f"- `{cfg.ALIGNMENT_RULE}`")
    lines.append("- 월말 HSI 상태를 다음 달 ETF 월간 수익률에 적용한다.")
    lines.append("")
    lines.append("## 3. 성과 요약")
    lines.append("")
    lines.append("| strategy | months | CAGR_pct | MDD_pct | Sharpe | Calmar | WinRate_pct |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for _, row in performance.iterrows():
        lines.append(
            f"| {row['strategy_name']} | {row['months']} | "
            f"{row['CAGR_pct']:.4f} | {row['MDD_pct']:.4f} | "
            f"{row['Sharpe']:.4f} | {row['Calmar']:.4f} | {row['WinRate_pct']:.4f} |"
        )
    lines.append("")
    lines.append("## 4. Turnover 요약")
    lines.append("")
    lines.append("| strategy | avg_turnover_pct | max_turnover_pct | total_turnover_pct |")
    lines.append("|---|---:|---:|---:|")
    for _, row in turnover.iterrows():
        lines.append(
            f"| {row['strategy_name']} | "
            f"{row['avg_turnover_pct']:.4f} | {row['max_turnover_pct']:.4f} | "
            f"{row['total_turnover_pct']:.4f} |"
        )
    lines.append("")
    lines.append("## 5. 다음 단계")
    lines.append("")
    lines.append(
        "`06_build_relative_speed_diagnostics.py`에서는 HSI 입력 신호들이 "
        "위험 악화 또는 위험 완화 방향으로 얼마나 빠르게 움직이는지 진단한다."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("05_backtest_baseline_allocation_rule.py 실행 시작")
    print("=" * 80)

    cfg.ensure_final_directories()

    print("[1] 입력 파일 로드")
    state_table = read_csv(INPUT_STATE_TABLE, "HSI 5상태표")
    monthly_returns = normalize_returns(read_csv(INPUT_MONTHLY_RETURNS, "월간 수익률 decimal"))
    print(f"    state_table shape = {state_table.shape}")
    print(f"    monthly_returns shape = {monthly_returns.shape}")

    print("[2] HSI target weights 생성")
    hsi_weights = build_rebalance_weights(state_table)
    ew_weights = build_ew_weights(hsi_weights)
    save_csv(hsi_weights, OUTPUT_WEIGHTS)
    print(f"    저장: {OUTPUT_WEIGHTS}")

    print("[3] 전략별 월간 수익률 계산")
    hsi_bt = calculate_strategy_return(hsi_weights, monthly_returns, STRATEGY_HSI)
    ew_bt = calculate_strategy_return(ew_weights, monthly_returns, STRATEGY_EW)

    backtest_ts = pd.concat([ew_bt, hsi_bt], ignore_index=True)
    backtest_ts = add_cumulative_and_drawdown(backtest_ts)

    save_csv(backtest_ts, OUTPUT_BACKTEST_TS)
    print(f"    저장: {OUTPUT_BACKTEST_TS}")

    print("[4] 성과표 계산")
    performance = build_performance_summary(backtest_ts)
    save_csv(performance, OUTPUT_PERFORMANCE)
    print(f"    저장: {OUTPUT_PERFORMANCE}")

    print("[5] Turnover 요약 계산")
    turnover = build_turnover_summary(backtest_ts)
    save_csv(turnover, OUTPUT_TURNOVER)
    print(f"    저장: {OUTPUT_TURNOVER}")

    print("[6] Alignment check 저장")
    alignment = build_alignment_check(hsi_weights, backtest_ts, monthly_returns)
    save_csv(alignment, OUTPUT_ALIGNMENT_CHECK)
    print(f"    저장: {OUTPUT_ALIGNMENT_CHECK}")

    print("[7] Markdown 노트 저장")
    note = build_note(performance, turnover)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[성과 요약]")
    print(performance.to_string(index=False))

    print("\n[Turnover 요약]")
    print(turnover.to_string(index=False))

    print("\n[최근 10개월 백테스트]")
    preview_cols = [
        "strategy_name",
        YEAR_MONTH_COL,
        RETURN_YEAR_MONTH_COL,
        "hsi_state",
        "strategy_return",
        "cumulative_return",
        "drawdown",
        "turnover",
    ]
    print(backtest_ts[preview_cols].tail(20).to_string(index=False))

    print("=" * 80)
    print("05_backtest_baseline_allocation_rule.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()