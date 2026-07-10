from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
07_run_signal_combo_backtests.py

목적
----
HSI 5상태 baseline 이후, 여러 신호 조합을 비교한다.

이 파일의 실험은 최고 수익률 조합을 찾는 것이 아니라,
신호 조합이 달라졌을 때 HSI 상태분포, 성과, MDD, Turnover가
얼마나 안정적인지 확인하는 비교 실험이다.

실험 조합
---------
combo_00_core5
    score_return, score_ma_pos, score_momentum, score_vol, score_rs

combo_01_core4_no_rs
    score_return, score_ma_pos, score_momentum, score_vol

combo_02_trend_only
    score_return, score_ma_pos, score_momentum

combo_03_risk_damage_focus
    score_return, score_ma_pos, score_vol

combo_04_core5_plus_relative_speed
    core5 + score_relative_speed

중요
----
상대속도는 선행/후행 예측값이 아니다.
전체 HSI 중심 흐름보다 특정 신호가 위험 악화 또는 위험 완화 방향으로
더 빠르게 움직이는지를 보는 내부 진단 신호이다.

입력
----
data/processed/main_final_monthly_signal_inputs_long.csv
data/processed/main_final_relative_speed_long.csv
data/processed/main_final_monthly_return_decimal.csv

출력
----
data/processed/main_final_signal_combo_hsi_state_table.csv
data/processed/main_final_signal_combo_rebalance_weights.csv
data/processed/main_final_signal_combo_backtest_timeseries.csv

output/tables/main_final_signal_combo_experiment_design.csv
output/tables/main_final_signal_combo_state_distribution.csv
output/tables/main_final_signal_combo_performance_summary.csv
output/tables/main_final_signal_combo_turnover_summary.csv
output/tables/main_final_signal_combo_candidate_judgement.csv

docs/main_final_signal_combo_backtest_note.md
"""


INPUT_MONTHLY_SIGNAL_LONG = cfg.PROCESSED_DIR / "main_final_monthly_signal_inputs_long.csv"
INPUT_RELATIVE_SPEED_LONG = cfg.PROCESSED_DIR / "main_final_relative_speed_long.csv"
INPUT_MONTHLY_RETURNS = cfg.PROCESSED_DIR / "main_final_monthly_return_decimal.csv"

OUTPUT_STATE_TABLE = cfg.PROCESSED_DIR / "main_final_signal_combo_hsi_state_table.csv"
OUTPUT_WEIGHTS = cfg.PROCESSED_DIR / "main_final_signal_combo_rebalance_weights.csv"
OUTPUT_BACKTEST_TS = cfg.PROCESSED_DIR / "main_final_signal_combo_backtest_timeseries.csv"

OUTPUT_EXPERIMENT_DESIGN = cfg.TABLE_DIR / "main_final_signal_combo_experiment_design.csv"
OUTPUT_STATE_DISTRIBUTION = cfg.TABLE_DIR / "main_final_signal_combo_state_distribution.csv"
OUTPUT_PERFORMANCE = cfg.TABLE_DIR / "main_final_signal_combo_performance_summary.csv"
OUTPUT_TURNOVER = cfg.TABLE_DIR / "main_final_signal_combo_turnover_summary.csv"
OUTPUT_JUDGEMENT = cfg.TABLE_DIR / "main_final_signal_combo_candidate_judgement.csv"

OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_signal_combo_backtest_note.md"


YEAR_MONTH_COL = "year_month"
RETURN_YEAR_MONTH_COL = "return_year_month"
TICKER_COL = "ticker"

MARKET_STATE_TICKER = cfg.RISK_TICKER

CORE_SCORE_COLS = [
    "score_return",
    "score_ma_pos",
    "score_momentum",
    "score_vol",
    "score_rs",
]

COMBO_DESIGN = [
    {
        "combo_id": "combo_00_core5",
        "combo_name": "기본 5개 HSI 점수",
        "score_cols": CORE_SCORE_COLS,
        "note": "기본 HSI 점수 5개를 모두 사용한다.",
    },
    {
        "combo_id": "combo_01_core4_no_rs",
        "combo_name": "기본 4개 HSI 점수",
        "score_cols": ["score_return", "score_ma_pos", "score_momentum", "score_vol"],
        "note": "벤치마크 자기비교 성격이 있는 score_rs를 제외한다.",
    },
    {
        "combo_id": "combo_02_trend_only",
        "combo_name": "추세 중심 신호",
        "score_cols": ["score_return", "score_ma_pos", "score_momentum"],
        "note": "수익률·이동평균 위치·모멘텀 중심으로 상태를 분류한다.",
    },
    {
        "combo_id": "combo_03_risk_damage_focus",
        "combo_name": "추세+위험훼손 신호",
        "score_cols": ["score_return", "score_ma_pos", "score_vol"],
        "note": "수익률·이동평균 위치·변동성으로 위험 훼손을 본다.",
    },
    {
        "combo_id": "combo_04_core5_plus_relative_speed",
        "combo_name": "기본 5개 + 상대속도",
        "score_cols": CORE_SCORE_COLS + ["score_relative_speed"],
        "note": "기본 HSI 점수에 상대속도 진단 점수를 보조 신호로 추가한다.",
    },
]

SCORE_SCALE = 10.0
THETA_COMMON = 0.15
ACCIDENT_EXTRA = 0.20
DIRECTION_MARGIN = 0.05
CONFLICT_DIRECTION_BAND = 0.20


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


def build_relative_speed_score(relative_speed: pd.DataFrame) -> pd.DataFrame:
    df = relative_speed.copy()
    df[TICKER_COL] = df[TICKER_COL].astype(str).str.zfill(6)

    risk_df = df[df[TICKER_COL] == cfg.RISK_TICKER].copy()

    if risk_df.empty:
        return pd.DataFrame(columns=[YEAR_MONTH_COL, "score_relative_speed"])

    summary = (
        risk_df
        .dropna(subset=["relative_velocity"])
        .groupby(YEAR_MONTH_COL)
        .agg(
            score_relative_speed=("relative_velocity", "mean"),
            relative_speed_abs_mean=("relative_speed_abs", "mean"),
            risk_accelerating_ratio=("direction_label", lambda s: (s == "risk_accelerating").mean()),
            relief_accelerating_ratio=("direction_label", lambda s: (s == "risk_relief_accelerating").mean()),
        )
        .reset_index()
    )

    summary["score_relative_speed"] = summary["score_relative_speed"].clip(-10, 10)

    return summary


def attach_relative_speed_score(monthly_long: pd.DataFrame, relative_speed_score: pd.DataFrame) -> pd.DataFrame:
    out = monthly_long.copy()

    if relative_speed_score.empty:
        out["score_relative_speed"] = np.nan
        out["relative_speed_abs_mean"] = np.nan
        out["risk_accelerating_ratio"] = np.nan
        out["relief_accelerating_ratio"] = np.nan
        return out

    out = out.merge(relative_speed_score, on=YEAR_MONTH_COL, how="left")
    return out


def classify_state(row: pd.Series, score_cols: list[str]) -> pd.Series:
    scores = pd.to_numeric(row[score_cols], errors="coerce").dropna()
    valid_score_count = len(scores)
    min_valid = min(3, len(score_cols))

    if valid_score_count < min_valid:
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

    if risk_component >= THETA_COMMON + ACCIDENT_EXTRA and state_direction > 0:
        hsi_state = "accident_zone"
        reason = "risk_component_above_accident_threshold"
    elif (
        risk_component >= THETA_COMMON
        and relief_component >= THETA_COMMON
        and abs(state_direction) <= CONFLICT_DIRECTION_BAND
    ):
        hsi_state = "conflict"
        reason = "risk_and_relief_components_both_active"
    elif risk_component >= THETA_COMMON and state_direction > DIRECTION_MARGIN:
        hsi_state = "risk_warning"
        reason = "risk_component_dominant"
    elif relief_component >= THETA_COMMON and state_direction < -DIRECTION_MARGIN:
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


def build_combo_state_table(monthly_long: pd.DataFrame) -> pd.DataFrame:
    df = monthly_long.copy()
    df[TICKER_COL] = df[TICKER_COL].astype(str).str.zfill(6)

    market_df = df[df[TICKER_COL] == MARKET_STATE_TICKER].copy()

    if market_df.empty:
        raise ValueError(f"{MARKET_STATE_TICKER} 기준 월말 신호가 없습니다.")

    all_rows = []

    for combo in COMBO_DESIGN:
        combo_id = combo["combo_id"]
        score_cols = combo["score_cols"]

        for col in score_cols:
            if col not in market_df.columns:
                market_df[col] = np.nan

        state_features = market_df.apply(lambda row: classify_state(row, score_cols), axis=1)

        keep_cols = [
            YEAR_MONTH_COL,
            TICKER_COL,
            "ticker_name",
            "ticker_role",
            "score_date",
            "hsi_direction",
            "raw3_signal",
        ] + [c for c in score_cols if c in market_df.columns]

        keep_cols = [c for c in keep_cols if c in market_df.columns]

        out = pd.concat(
            [
                market_df[keep_cols].reset_index(drop=True),
                state_features.reset_index(drop=True),
            ],
            axis=1,
        )

        out["combo_id"] = combo_id
        out["combo_name"] = combo["combo_name"]
        out["score_cols_used"] = ", ".join(score_cols)
        out["state_kr"] = out["hsi_state"].map(cfg.HSI_STATE_KR)
        out["state_rule_version"] = "combo_state5_v1"

        all_rows.append(out)

    return pd.concat(all_rows, ignore_index=True)


def build_experiment_design() -> pd.DataFrame:
    rows = []

    for combo in COMBO_DESIGN:
        rows.append({
            "combo_id": combo["combo_id"],
            "combo_name": combo["combo_name"],
            "score_cols": ", ".join(combo["score_cols"]),
            "theta_common": THETA_COMMON,
            "accident_extra": ACCIDENT_EXTRA,
            "conflict_direction_band": CONFLICT_DIRECTION_BAND,
            "allocation_rule_name": cfg.FINAL_ALLOCATION_RULE_NAME,
            "note": combo["note"],
        })

    return pd.DataFrame(rows)


def get_target_weight(hsi_state: str) -> dict:
    if hsi_state in cfg.FINAL_BASELINE_ALLOCATION_RULES:
        rule = cfg.FINAL_BASELINE_ALLOCATION_RULES[hsi_state]
    else:
        rule = cfg.FINAL_BASELINE_ALLOCATION_RULES["neutral_watch"]

    return {ticker: float(rule[ticker]) for ticker in cfg.TICKERS}


def build_rebalance_weights(combo_state: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in combo_state.iterrows():
        weight = get_target_weight(row["hsi_state"])

        item = {
            "combo_id": row["combo_id"],
            "combo_name": row["combo_name"],
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
    weights = weights.sort_values(["combo_id", YEAR_MONTH_COL]).reset_index(drop=True)

    weight_cols = [f"weight_{ticker}" for ticker in cfg.TICKERS]
    weights["turnover"] = (
        weights
        .groupby("combo_id")[weight_cols]
        .diff()
        .abs()
        .sum(axis=1)
        * 0.5
    )
    weights["turnover"] = weights["turnover"].fillna(0.0)

    return weights


def build_ew_backtest_base(monthly_returns: pd.DataFrame, signal_months: list[str]) -> pd.DataFrame:
    rows = []

    for ym in signal_months:
        item = {
            "combo_id": "EW",
            "combo_name": "Equal Weight",
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
    merged["strategy_name"] = np.where(
        merged["combo_id"] == "EW",
        "EW",
        merged["combo_id"],
    )

    keep_cols = [
        "strategy_name",
        "combo_id",
        "combo_name",
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
        "combo_id": g["combo_id"].iloc[0],
        "combo_name": g["combo_name"].iloc[0],
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
            "combo_id": group["combo_id"].iloc[0],
            "combo_name": group["combo_name"].iloc[0],
            "months": len(group),
            "avg_turnover_pct": t.mean() * 100,
            "max_turnover_pct": t.max() * 100,
            "total_turnover_pct": t.sum() * 100,
            "nonzero_turnover_months": int((t > 0).sum()),
        })

    return pd.DataFrame(rows)


def build_state_distribution(combo_state: pd.DataFrame) -> pd.DataFrame:
    dist = (
        combo_state
        .groupby(["combo_id", "combo_name", "hsi_state", "state_kr"])
        .size()
        .reset_index(name="months")
    )

    total = (
        combo_state
        .groupby("combo_id")
        .size()
        .reset_index(name="total_months")
    )

    dist = dist.merge(total, on="combo_id", how="left")
    dist["ratio"] = dist["months"] / dist["total_months"]

    return dist.sort_values(["combo_id", "hsi_state"]).reset_index(drop=True)


def build_candidate_judgement(performance: pd.DataFrame, turnover: pd.DataFrame) -> pd.DataFrame:
    perf = performance.merge(
        turnover[["strategy_name", "avg_turnover_pct", "max_turnover_pct", "total_turnover_pct"]],
        on="strategy_name",
        how="left",
    )

    ew = perf[perf["strategy_name"] == "EW"].iloc[0]

    rows = []

    for _, row in perf.iterrows():
        if row["strategy_name"] == "EW":
            decision = "benchmark"
            reason = "동일가중 비교 기준"
        else:
            mdd_change = row["MDD_pct"] - ew["MDD_pct"]
            cagr_gap = row["CAGR_pct"] - ew["CAGR_pct"]

            pass_turnover = row["avg_turnover_pct"] <= 5.0 and row["max_turnover_pct"] <= 25.0
            pass_mdd = mdd_change >= 0

            if pass_turnover and pass_mdd:
                decision = "candidate"
                reason = "EW 대비 MDD가 개선되고 Turnover 기준을 통과"
            elif pass_turnover:
                decision = "review"
                reason = "Turnover 기준은 통과했으나 EW 대비 MDD 개선은 불충분"
            else:
                decision = "revise_or_exclude"
                reason = "Turnover 기준 또는 위험관리 기준 재검토 필요"

            rows.append({
                "strategy_name": row["strategy_name"],
                "combo_id": row["combo_id"],
                "combo_name": row["combo_name"],
                "CAGR_gap_vs_EW_pct": cagr_gap,
                "MDD_change_vs_EW_pct": mdd_change,
                "avg_turnover_pct": row["avg_turnover_pct"],
                "max_turnover_pct": row["max_turnover_pct"],
                "decision": decision,
                "reason": reason,
            })
            continue

        rows.append({
            "strategy_name": row["strategy_name"],
            "combo_id": row["combo_id"],
            "combo_name": row["combo_name"],
            "CAGR_gap_vs_EW_pct": 0.0,
            "MDD_change_vs_EW_pct": 0.0,
            "avg_turnover_pct": row["avg_turnover_pct"],
            "max_turnover_pct": row["max_turnover_pct"],
            "decision": decision,
            "reason": reason,
        })

    return pd.DataFrame(rows)


def build_note(performance: pd.DataFrame, judgement: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_final 신호 조합 백테스트 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 단계는 HSI 상태분류에 사용하는 신호 조합을 바꾸었을 때 "
        "성과, MDD, Turnover, 상태분포가 어떻게 달라지는지 비교한다."
    )
    lines.append("")
    lines.append("## 2. 주의")
    lines.append("")
    lines.append(
        "상대속도는 미래 수익률을 예측하기 위한 선행지표가 아니라, "
        "HSI 내부 신호가 전체 중심 흐름보다 위험 악화 또는 완화 방향으로 빠르게 움직이는지 보는 진단 신호이다."
    )
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
    lines.append("## 4. 후보 판단")
    lines.append("")
    lines.append("| strategy | decision | reason |")
    lines.append("|---|---|---|")
    for _, row in judgement.iterrows():
        lines.append(f"| {row['strategy_name']} | {row['decision']} | {row['reason']} |")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("07_run_signal_combo_backtests.py 실행 시작")
    print("=" * 80)

    cfg.ensure_final_directories()

    print("[1] 입력 파일 로드")
    monthly_long = read_csv(INPUT_MONTHLY_SIGNAL_LONG, "월말 HSI signal long")
    relative_speed = read_csv(INPUT_RELATIVE_SPEED_LONG, "상대속도 long")
    monthly_returns = normalize_returns(read_csv(INPUT_MONTHLY_RETURNS, "월간 수익률 decimal"))
    print(f"    monthly_long shape = {monthly_long.shape}")
    print(f"    relative_speed shape = {relative_speed.shape}")
    print(f"    monthly_returns shape = {monthly_returns.shape}")

    print("[2] 상대속도 점수 생성 및 병합")
    rv_score = build_relative_speed_score(relative_speed)
    monthly_long = attach_relative_speed_score(monthly_long, rv_score)
    print(f"    relative_speed_score shape = {rv_score.shape}")

    print("[3] 실험 설계표 저장")
    design = build_experiment_design()
    save_csv(design, OUTPUT_EXPERIMENT_DESIGN)
    print(f"    저장: {OUTPUT_EXPERIMENT_DESIGN}")

    print("[4] 조합별 HSI 상태표 생성")
    combo_state = build_combo_state_table(monthly_long)
    save_csv(combo_state, OUTPUT_STATE_TABLE)
    print(f"    저장: {OUTPUT_STATE_TABLE}")

    print("[5] 조합별 비중표 생성")
    combo_weights = build_rebalance_weights(combo_state)

    ew_weights = build_ew_backtest_base(
        monthly_returns,
        sorted(combo_state[YEAR_MONTH_COL].unique().tolist()),
    )

    all_weights = pd.concat([ew_weights, combo_weights], ignore_index=True)
    save_csv(all_weights, OUTPUT_WEIGHTS)
    print(f"    저장: {OUTPUT_WEIGHTS}")

    print("[6] 백테스트 실행")
    backtest_ts = calculate_strategy_return(all_weights, monthly_returns)
    backtest_ts = add_cumulative_and_drawdown(backtest_ts)
    save_csv(backtest_ts, OUTPUT_BACKTEST_TS)
    print(f"    저장: {OUTPUT_BACKTEST_TS}")

    print("[7] 요약표 생성")
    state_dist = build_state_distribution(combo_state)
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

    print("[8] Markdown 노트 저장")
    note = build_note(performance, judgement)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[성과 요약]")
    print(performance.to_string(index=False))

    print("\n[후보 판단]")
    print(judgement.to_string(index=False))

    print("=" * 80)
    print("07_run_signal_combo_backtests.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()