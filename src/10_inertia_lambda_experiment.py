from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
10_inertia_lambda_experiment.py

목적
----
HSI 상태별 목표 비중으로 한 번에 이동할지,
일부만 이동할지 확인하는 포트폴리오 관성 λ 실험을 수행한다.

공식
----
actual_weight_t = previous_weight + λ × (target_weight_t - previous_weight)

해석
----
λ = 1.0 : 목표 비중으로 즉시 이동
λ = 0.7 : 목표 비중의 70% 반영
λ = 0.5 : 목표 비중의 절반 반영
λ = 0.3 : 천천히 이동
λ = 0.1 : 매우 천천히 이동

중요
----
이 실험은 최고 수익률을 찾는 실험이 아니다.
Turnover와 방어 성과 사이의 균형을 확인하는 실험이다.

입력
----
data/processed/main_final_hsi_state5_table.csv
data/processed/main_final_monthly_return_decimal.csv

출력
----
data/processed/main_final_lambda_weights.csv
data/processed/main_final_lambda_backtest_timeseries.csv

output/tables/main_final_lambda_experiment_design.csv
output/tables/main_final_lambda_performance_summary.csv
output/tables/main_final_lambda_turnover_summary.csv
output/tables/main_final_lambda_candidate_judgement.csv

docs/main_final_lambda_experiment_note.md
"""


INPUT_STATE_TABLE = cfg.PROCESSED_DIR / "main_final_hsi_state5_table.csv"
INPUT_MONTHLY_RETURNS = cfg.PROCESSED_DIR / "main_final_monthly_return_decimal.csv"

OUTPUT_LAMBDA_WEIGHTS = cfg.PROCESSED_DIR / "main_final_lambda_weights.csv"
OUTPUT_LAMBDA_BACKTEST_TS = cfg.PROCESSED_DIR / "main_final_lambda_backtest_timeseries.csv"

OUTPUT_EXPERIMENT_DESIGN = cfg.TABLE_DIR / "main_final_lambda_experiment_design.csv"
OUTPUT_PERFORMANCE = cfg.TABLE_DIR / "main_final_lambda_performance_summary.csv"
OUTPUT_TURNOVER = cfg.TABLE_DIR / "main_final_lambda_turnover_summary.csv"
OUTPUT_JUDGEMENT = cfg.TABLE_DIR / "main_final_lambda_candidate_judgement.csv"

OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_lambda_experiment_note.md"


YEAR_MONTH_COL = "year_month"
RETURN_YEAR_MONTH_COL = "return_year_month"

LAMBDA_CANDIDATES = [1.0, 0.7, 0.5, 0.3, 0.1]

EW_STRATEGY_NAME = "EW"


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


def get_target_weight(hsi_state: str) -> dict:
    if hsi_state in cfg.FINAL_BASELINE_ALLOCATION_RULES:
        rule = cfg.FINAL_BASELINE_ALLOCATION_RULES[hsi_state]
    else:
        rule = cfg.FINAL_BASELINE_ALLOCATION_RULES["neutral_watch"]

    return {ticker: float(rule[ticker]) for ticker in cfg.TICKERS}


def build_experiment_design() -> pd.DataFrame:
    rows = []

    for lam in LAMBDA_CANDIDATES:
        rows.append({
            "lambda_id": f"lambda_{lam:.1f}",
            "lambda_value": lam,
            "adjustment_formula": "actual_weight_t = previous_weight + lambda * (target_weight_t - previous_weight)",
            "allocation_rule_name": cfg.FINAL_ALLOCATION_RULE_NAME,
            "purpose": "Turnover와 방어 성과 사이의 균형 확인",
        })

    return pd.DataFrame(rows)


def build_lambda_weights(state_table: pd.DataFrame) -> pd.DataFrame:
    state = normalize_year_month(state_table).sort_values(YEAR_MONTH_COL).reset_index(drop=True)

    rows = []

    for lam in LAMBDA_CANDIDATES:
        previous_weight = {ticker: 1.0 / len(cfg.TICKERS) for ticker in cfg.TICKERS}

        for _, row in state.iterrows():
            target_weight = get_target_weight(row["hsi_state"])

            actual_weight = {}
            for ticker in cfg.TICKERS:
                actual_weight[ticker] = (
                    previous_weight[ticker]
                    + lam * (target_weight[ticker] - previous_weight[ticker])
                )

            total = sum(actual_weight.values())
            if total != 0:
                actual_weight = {k: v / total for k, v in actual_weight.items()}

            item = {
                "strategy_name": f"lambda_{lam:.1f}",
                "lambda_value": lam,
                YEAR_MONTH_COL: row[YEAR_MONTH_COL],
                RETURN_YEAR_MONTH_COL: str(pd.Period(row[YEAR_MONTH_COL], freq="M") + 1),
                "hsi_state": row["hsi_state"],
                "state_kr": row.get("state_kr", ""),
                "allocation_rule_name": cfg.FINAL_ALLOCATION_RULE_NAME,
            }

            for ticker in cfg.TICKERS:
                item[f"target_weight_{ticker}"] = target_weight[ticker]
                item[f"weight_{ticker}"] = actual_weight[ticker]

            rows.append(item)
            previous_weight = actual_weight

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
            "lambda_value": np.nan,
            YEAR_MONTH_COL: ym,
            RETURN_YEAR_MONTH_COL: str(pd.Period(ym, freq="M") + 1),
            "hsi_state": "EW",
            "state_kr": "동일가중",
            "allocation_rule_name": "equal_weight",
            "turnover": 0.0,
        }

        for ticker in cfg.TICKERS:
            item[f"target_weight_{ticker}"] = 1.0 / len(cfg.TICKERS)
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
        "lambda_value",
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
        "lambda_value": g["lambda_value"].iloc[0],
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
            "lambda_value": group["lambda_value"].iloc[0],
            "months": len(group),
            "avg_turnover_pct": t.mean() * 100,
            "max_turnover_pct": t.max() * 100,
            "total_turnover_pct": t.sum() * 100,
            "nonzero_turnover_months": int((t > 0).sum()),
        })

    return pd.DataFrame(rows)


def build_candidate_judgement(performance: pd.DataFrame, turnover: pd.DataFrame) -> pd.DataFrame:
    merged = performance.merge(
        turnover[["strategy_name", "avg_turnover_pct", "max_turnover_pct", "total_turnover_pct"]],
        on="strategy_name",
        how="left",
    )

    lambda_1 = merged[merged["strategy_name"] == "lambda_1.0"].iloc[0]

    rows = []

    for _, row in merged.iterrows():
        if row["strategy_name"] == EW_STRATEGY_NAME:
            rows.append({
                "strategy_name": row["strategy_name"],
                "lambda_value": row["lambda_value"],
                "CAGR_change_vs_lambda1_pct": np.nan,
                "MDD_change_vs_lambda1_pct": np.nan,
                "avg_turnover_change_vs_lambda1_pct": np.nan,
                "decision": "benchmark",
                "reason": "동일가중 비교 기준",
            })
            continue

        cagr_change = row["CAGR_pct"] - lambda_1["CAGR_pct"]
        mdd_change = row["MDD_pct"] - lambda_1["MDD_pct"]
        turnover_change = row["avg_turnover_pct"] - lambda_1["avg_turnover_pct"]

        if row["lambda_value"] == 1.0:
            decision = "baseline_lambda"
            reason = "목표 비중 즉시 이동 기준"
        elif turnover_change < 0 and mdd_change >= -2.0:
            decision = "candidate"
            reason = "Turnover가 감소하고 MDD 악화가 제한적"
        elif turnover_change < 0:
            decision = "review"
            reason = "Turnover는 감소하나 위험 대응 지연 여부 확인 필요"
        else:
            decision = "revise_or_exclude"
            reason = "λ를 낮추었지만 Turnover 개선이 뚜렷하지 않음"

        rows.append({
            "strategy_name": row["strategy_name"],
            "lambda_value": row["lambda_value"],
            "CAGR_change_vs_lambda1_pct": cagr_change,
            "MDD_change_vs_lambda1_pct": mdd_change,
            "avg_turnover_change_vs_lambda1_pct": turnover_change,
            "decision": decision,
            "reason": reason,
        })

    return pd.DataFrame(rows)


def build_note(performance: pd.DataFrame, turnover: pd.DataFrame, judgement: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_final λ 기반 포트폴리오 관성 실험 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "λ 실험은 HSI 상태가 바뀔 때 목표 비중으로 한 번에 이동하는 것이 좋은지, "
        "또는 일부만 이동하는 것이 더 안정적인지 확인하는 실험이다."
    )
    lines.append("")
    lines.append("## 2. 공식")
    lines.append("")
    lines.append("```text")
    lines.append("actual_weight_t = previous_weight + λ × (target_weight_t - previous_weight)")
    lines.append("```")
    lines.append("")
    lines.append("## 3. 성과 요약")
    lines.append("")
    lines.append("| strategy | lambda | CAGR_pct | MDD_pct | Sharpe | Calmar |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for _, row in performance.iterrows():
        lam = "" if pd.isna(row["lambda_value"]) else f"{row['lambda_value']:.1f}"
        lines.append(
            f"| {row['strategy_name']} | {lam} | {row['CAGR_pct']:.4f} | "
            f"{row['MDD_pct']:.4f} | {row['Sharpe']:.4f} | {row['Calmar']:.4f} |"
        )
    lines.append("")
    lines.append("## 4. Turnover 요약")
    lines.append("")
    lines.append("| strategy | avg_turnover_pct | max_turnover_pct | total_turnover_pct |")
    lines.append("|---|---:|---:|---:|")
    for _, row in turnover.iterrows():
        lines.append(
            f"| {row['strategy_name']} | {row['avg_turnover_pct']:.4f} | "
            f"{row['max_turnover_pct']:.4f} | {row['total_turnover_pct']:.4f} |"
        )
    lines.append("")
    lines.append("## 5. 후보 판단")
    lines.append("")
    for _, row in judgement.iterrows():
        lines.append(f"- {row['strategy_name']}: {row['decision']} — {row['reason']}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("10_inertia_lambda_experiment.py 실행 시작")
    print("=" * 80)

    cfg.ensure_final_directories()

    print("[1] 입력 파일 로드")
    state_table = read_csv(INPUT_STATE_TABLE, "HSI 5상태표")
    monthly_returns = normalize_returns(read_csv(INPUT_MONTHLY_RETURNS, "월간 수익률 decimal"))
    print(f"    state_table shape = {state_table.shape}")
    print(f"    monthly_returns shape = {monthly_returns.shape}")

    print("[2] λ 실험 설계표 저장")
    design = build_experiment_design()
    save_csv(design, OUTPUT_EXPERIMENT_DESIGN)
    print(f"    저장: {OUTPUT_EXPERIMENT_DESIGN}")

    print("[3] λ별 비중표 생성")
    lambda_weights = build_lambda_weights(state_table)
    ew_weights = build_ew_weights(sorted(state_table[YEAR_MONTH_COL].astype(str).unique().tolist()))
    all_weights = pd.concat([ew_weights, lambda_weights], ignore_index=True)

    save_csv(all_weights, OUTPUT_LAMBDA_WEIGHTS)
    print(f"    저장: {OUTPUT_LAMBDA_WEIGHTS}")

    print("[4] 백테스트 실행")
    backtest_ts = calculate_strategy_return(all_weights, monthly_returns)
    backtest_ts = add_cumulative_and_drawdown(backtest_ts)

    save_csv(backtest_ts, OUTPUT_LAMBDA_BACKTEST_TS)
    print(f"    저장: {OUTPUT_LAMBDA_BACKTEST_TS}")

    print("[5] 요약표 생성")
    performance = build_performance_summary(backtest_ts)
    turnover = build_turnover_summary(backtest_ts)
    judgement = build_candidate_judgement(performance, turnover)

    save_csv(performance, OUTPUT_PERFORMANCE)
    save_csv(turnover, OUTPUT_TURNOVER)
    save_csv(judgement, OUTPUT_JUDGEMENT)

    print(f"    저장: {OUTPUT_PERFORMANCE}")
    print(f"    저장: {OUTPUT_TURNOVER}")
    print(f"    저장: {OUTPUT_JUDGEMENT}")

    print("[6] Markdown 노트 저장")
    note = build_note(performance, turnover, judgement)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[성과 요약]")
    print(performance.to_string(index=False))

    print("\n[Turnover 요약]")
    print(turnover.to_string(index=False))

    print("\n[후보 판단]")
    print(judgement.to_string(index=False))

    print("=" * 80)
    print("10_inertia_lambda_experiment.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()