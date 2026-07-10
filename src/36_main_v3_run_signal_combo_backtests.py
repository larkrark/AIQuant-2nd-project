from pathlib import Path
from datetime import datetime
import math

import numpy as np
import pandas as pd


"""
36_main_v3_run_signal_combo_backtests.py

목적
----
35번에서 생성한 추가 지표 입력표를 사용하여
신호 조합별 HSI 5상태 분류와 main_v2b 기준 백테스트를 실행한다.

핵심 원칙
---------
1. ETF 3개는 고정한다.
2. main_v2b 비중 규칙은 고정한다.
3. 월말 신호를 다음 달 수익률에 적용한다.
4. 바꾸는 것은 오직 신호 조합이다.

비교 실험
---------
combo_00_baseline_core
combo_01_trend_speed
combo_02_risk_damage
combo_03_relative_strength
combo_04_speed_alignment_all

입력
----
data/processed/main_v3_extended_signal_inputs_long.csv
data/processed/monthly_returns.csv

출력
----
data/processed/main_v3_signal_combo_hsi_state_table.csv
data/processed/main_v3_signal_combo_rebalance_weights.csv
data/processed/main_v3_signal_combo_backtest_timeseries.csv

output/tables/main_v3_signal_combo_experiment_design.csv
output/tables/main_v3_signal_combo_state_distribution.csv
output/tables/main_v3_signal_combo_performance_summary.csv
output/tables/main_v3_signal_combo_turnover_summary.csv
output/tables/main_v3_signal_combo_candidate_judgement.csv
output/tables/main_v3_signal_combo_alignment_check.csv

docs/main_v3_signal_combo_backtest_note.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
DOCS_DIR = PROJECT_ROOT / "docs"

DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_EXTENDED_LONG = DATA_PROCESSED_DIR / "main_v3_extended_signal_inputs_long.csv"
INPUT_MONTHLY_RETURNS = DATA_PROCESSED_DIR / "monthly_returns.csv"

OUTPUT_STATE_TABLE = DATA_PROCESSED_DIR / "main_v3_signal_combo_hsi_state_table.csv"
OUTPUT_REBALANCE_WEIGHTS = DATA_PROCESSED_DIR / "main_v3_signal_combo_rebalance_weights.csv"
OUTPUT_BACKTEST_TS = DATA_PROCESSED_DIR / "main_v3_signal_combo_backtest_timeseries.csv"

OUTPUT_EXPERIMENT_DESIGN = TABLE_DIR / "main_v3_signal_combo_experiment_design.csv"
OUTPUT_STATE_DISTRIBUTION = TABLE_DIR / "main_v3_signal_combo_state_distribution.csv"
OUTPUT_PERFORMANCE = TABLE_DIR / "main_v3_signal_combo_performance_summary.csv"
OUTPUT_TURNOVER = TABLE_DIR / "main_v3_signal_combo_turnover_summary.csv"
OUTPUT_CANDIDATE_JUDGEMENT = TABLE_DIR / "main_v3_signal_combo_candidate_judgement.csv"
OUTPUT_ALIGNMENT_CHECK = TABLE_DIR / "main_v3_signal_combo_alignment_check.csv"

OUTPUT_NOTE = DOCS_DIR / "main_v3_signal_combo_backtest_note.md"


# ============================================================
# 1. 설정
# ============================================================

RISK_TICKER = "069500"
BOND_TICKER = "114260"
CASH_TICKER = "153130"

TICKERS = [RISK_TICKER, BOND_TICKER, CASH_TICKER]

SCORE_SCALE = 10.0
SCORE_NEUTRAL_BAND = 1.0

THETA_COMMON = 0.15
ACCIDENT_EXTRA = 0.20
CONFLICT_DIRECTION_BAND = 0.20

STRATEGY_EW_PREFIX = "EW_match"

# main_v2b 기준 비중 규칙
STATE_ALLOCATION_RULES = {
    "risk_relief": {
        RISK_TICKER: 1 / 3,
        BOND_TICKER: 1 / 3,
        CASH_TICKER: 1 / 3,
        "rule_note": "위험 완화 우세. baseline에서는 과도한 risk-on 없이 동일비중 유지.",
    },
    "neutral_watch": {
        RISK_TICKER: 1 / 3,
        BOND_TICKER: 1 / 3,
        CASH_TICKER: 1 / 3,
        "rule_note": "관찰·중립. 동일비중 유지.",
    },
    "conflict": {
        RISK_TICKER: 1 / 3,
        BOND_TICKER: 1 / 3,
        CASH_TICKER: 1 / 3,
        "rule_note": "신호 충돌. main_v2b에서는 즉시 방어하지 않고 동일비중 관찰.",
    },
    "risk_warning": {
        RISK_TICKER: 0.20,
        BOND_TICKER: 0.40,
        CASH_TICKER: 0.40,
        "rule_note": "위험 악화 우세. 위험자산 축소, 방어자산 확대.",
    },
    "accident_zone": {
        RISK_TICKER: 0.10,
        BOND_TICKER: 0.45,
        CASH_TICKER: 0.45,
        "rule_note": "강한 위험 악화. 위험자산 강한 축소.",
    },
}


# ============================================================
# 2. 실험 설계
# ============================================================

def make_experiment_design() -> pd.DataFrame:
    rows = [
        {
            "experiment_id": "combo_00_baseline_core",
            "experiment_name": "기본 HSI 핵심 신호",
            "signal_set_type": "baseline",
            "signal_columns": [
                "score_return",
                "score_ma_pos",
                "score_momentum",
                "score_vol",
            ],
            "main_question": "기본 HSI 신호만으로 EW 대비 방어 효과가 있는가?",
        },
        {
            "experiment_id": "combo_01_trend_speed",
            "experiment_name": "단기-중기 추세 보강",
            "signal_set_type": "trend_speed",
            "signal_columns": [
                "score_return",
                "score_ma_pos",
                "score_momentum",
                "score_vol",
                "score_ma20_gap",
                "score_ma60_gap",
            ],
            "main_question": "단기·중기 추세 보강이 상태분류와 성과를 개선하는가?",
        },
        {
            "experiment_id": "combo_02_risk_damage",
            "experiment_name": "위험강도·누적손상 보강",
            "signal_set_type": "risk_damage",
            "signal_columns": [
                "score_return",
                "score_ma_pos",
                "score_momentum",
                "score_vol",
                "score_vol20",
                "score_drawdown_60",
            ],
            "main_question": "변동성 확대와 누적 손상 신호가 방어 효과를 개선하는가?",
        },
        {
            "experiment_id": "combo_03_relative_strength",
            "experiment_name": "현금성 자산 대비 상대강도 보강",
            "signal_set_type": "relative_strength",
            "signal_columns": [
                "score_return",
                "score_ma_pos",
                "score_momentum",
                "score_vol",
                "score_risk_vs_cash_ret20",
            ],
            "main_question": "위험자산이 현금성 자산 대비 약해지는 구간을 더 잘 포착하는가?",
        },
        {
            "experiment_id": "combo_04_speed_alignment_all",
            "experiment_name": "단기-중기 신호 정렬 통합",
            "signal_set_type": "speed_alignment_all",
            "signal_columns": [
                "score_return",
                "score_ma_pos",
                "score_momentum",
                "score_vol",
                "score_ma20_gap",
                "score_ma60_gap",
                "score_vol20",
                "score_drawdown_60",
                "score_risk_vs_cash_ret20",
            ],
            "main_question": "추세·위험손상·상대강도 신호를 함께 쓰면 방어형 overlay 성과가 개선되는가?",
        },
    ]

    out_rows = []

    for row in rows:
        signal_columns = row["signal_columns"]
        out_rows.append({
            "experiment_id": row["experiment_id"],
            "experiment_name": row["experiment_name"],
            "signal_set_type": row["signal_set_type"],
            "signal_columns": "|".join(signal_columns),
            "signal_count": len(signal_columns),
            "min_valid_signals": max(3, math.ceil(len(signal_columns) * 0.60)),
            "theta_common": THETA_COMMON,
            "conflict_direction_band": CONFLICT_DIRECTION_BAND,
            "allocation_rule": "main_v2b_fixed",
            "main_question": row["main_question"],
        })

    return pd.DataFrame(out_rows)


# ============================================================
# 3. 입력 로드
# ============================================================

def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"필수 입력 파일을 찾을 수 없습니다: {path}")


def read_monthly_returns(path: Path) -> pd.DataFrame:
    """
    monthly_returns.csv를 읽는다.

    현재 프로젝트 기준:
    - data/processed/monthly_returns.csv는 백테스트용 decimal 단위
    - data/processed/monthly_returns_pct.csv는 사람이 보기 위한 percent 백업

    따라서 여기서는 /100 변환을 하지 않는다.
    """
    require_file(path)

    df = pd.read_csv(path, encoding="utf-8-sig")

    first_col = df.columns[0]
    if first_col.lower() in ["date", "year_month", "month"]:
        df = df.rename(columns={first_col: "year_month"})
        df = df.set_index("year_month")
    else:
        df = df.set_index(first_col)

    df.index = df.index.astype(str)
    df.columns = [str(c).zfill(6) for c in df.columns]

    monthly_returns_decimal = df[TICKERS].astype(float)

    # 방어 점검: decimal 파일인데 값이 너무 크면 경고
    max_abs = monthly_returns_decimal.stack().dropna().abs().max()
    if max_abs > 1.0:
        raise ValueError(
            "monthly_returns.csv가 decimal 단위가 아닌 것 같습니다. "
            f"최대 절대값={max_abs:.4f}. "
            "31b_fix_monthly_return_unit.py를 먼저 실행하거나 "
            "monthly_returns_pct.csv와 혼동했는지 확인하세요."
        )

    return monthly_returns_decimal


# ============================================================
# 4. HSI 상태분류
# ============================================================

def classify_state(
    hsi_direction: float,
    hsi_intensity: float,
    positive_count: int,
    negative_count: int,
    neutral_count: int,
    valid_signal_count: int,
    min_valid_signals: int,
) -> tuple[str, str]:
    if valid_signal_count < min_valid_signals:
        return (
            "insufficient_data",
            f"valid_signal_count={valid_signal_count} < min_valid_signals={min_valid_signals}",
        )

    conflict_ratio = (
        min(positive_count, negative_count) / valid_signal_count
        if valid_signal_count > 0
        else 0.0
    )

    if (
        positive_count >= 1
        and negative_count >= 1
        and conflict_ratio >= 0.25
        and abs(hsi_direction) < CONFLICT_DIRECTION_BAND
    ):
        return (
            "conflict",
            (
                f"positive={positive_count}, negative={negative_count}, "
                f"conflict_ratio={conflict_ratio:.2f}, direction={hsi_direction:.3f}"
            ),
        )

    accident_direction_threshold = THETA_COMMON + ACCIDENT_EXTRA
    accident_intensity_threshold = THETA_COMMON + ACCIDENT_EXTRA
    accident_positive_min = max(3, math.ceil(valid_signal_count * 0.45))

    if (
        hsi_direction >= accident_direction_threshold
        and hsi_intensity >= accident_intensity_threshold
        and positive_count >= accident_positive_min
    ):
        return (
            "accident_zone",
            (
                f"strong risk direction: direction={hsi_direction:.3f}, "
                f"intensity={hsi_intensity:.3f}, positive={positive_count}"
            ),
        )

    warning_positive_min = max(2, math.ceil(valid_signal_count * 0.35))

    if hsi_direction >= THETA_COMMON and positive_count >= warning_positive_min:
        return (
            "risk_warning",
            (
                f"risk warning: direction={hsi_direction:.3f}, "
                f"positive={positive_count}, negative={negative_count}"
            ),
        )

    relief_negative_min = max(2, math.ceil(valid_signal_count * 0.35))

    if hsi_direction <= -THETA_COMMON and negative_count >= relief_negative_min:
        return (
            "risk_relief",
            (
                f"risk relief: direction={hsi_direction:.3f}, "
                f"negative={negative_count}, positive={positive_count}"
            ),
        )

    return (
        "neutral_watch",
        (
            f"neutral/watch: direction={hsi_direction:.3f}, "
            f"positive={positive_count}, negative={negative_count}, neutral={neutral_count}"
        ),
    )


def build_state_table_for_experiment(
    monthly_signal_long: pd.DataFrame,
    experiment_row: pd.Series,
) -> pd.DataFrame:
    experiment_id = experiment_row["experiment_id"]
    experiment_name = experiment_row["experiment_name"]
    signal_columns = experiment_row["signal_columns"].split("|")
    min_valid_signals = int(experiment_row["min_valid_signals"])

    risk_df = monthly_signal_long[
        monthly_signal_long["ticker"].astype(str).str.zfill(6) == RISK_TICKER
    ].copy()

    risk_df = risk_df.sort_values("year_month")

    rows = []

    for _, row in risk_df.iterrows():
        year_month = str(row["year_month"])

        signal_values = {}

        for col in signal_columns:
            if col in row.index:
                signal_values[col] = row[col]
            else:
                signal_values[col] = np.nan

        score_series = pd.Series(signal_values, dtype="float64")
        valid_scores = score_series.dropna()
        valid_signal_count = len(valid_scores)

        if valid_signal_count == 0:
            hsi_direction = np.nan
            hsi_intensity = np.nan
            positive_count = 0
            negative_count = 0
            neutral_count = 0
        else:
            positive_count = int((valid_scores > SCORE_NEUTRAL_BAND).sum())
            negative_count = int((valid_scores < -SCORE_NEUTRAL_BAND).sum())
            neutral_count = int(valid_signal_count - positive_count - negative_count)

            hsi_direction = valid_scores.sum() / (valid_signal_count * SCORE_SCALE)
            hsi_intensity = valid_scores.abs().mean() / SCORE_SCALE

        hsi_state, state_reason = classify_state(
            hsi_direction=hsi_direction if not pd.isna(hsi_direction) else 0.0,
            hsi_intensity=hsi_intensity if not pd.isna(hsi_intensity) else 0.0,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            valid_signal_count=valid_signal_count,
            min_valid_signals=min_valid_signals,
        )

        state_valid = hsi_state != "insufficient_data"

        out = {
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "signal_set_type": experiment_row["signal_set_type"],
            "year_month": year_month,
            "risk_ticker": RISK_TICKER,
            "hsi_direction": round(hsi_direction, 6) if not pd.isna(hsi_direction) else np.nan,
            "hsi_intensity": round(hsi_intensity, 6) if not pd.isna(hsi_intensity) else np.nan,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "valid_signal_count": valid_signal_count,
            "min_valid_signals": min_valid_signals,
            "state_valid": state_valid,
            "hsi_state": hsi_state,
            "state_reason": state_reason,
            "active_signals": ", ".join(valid_scores.index.tolist()),
        }

        for col in signal_columns:
            out[col] = row[col] if col in row.index else np.nan

        rows.append(out)

    return pd.DataFrame(rows)


def build_all_state_tables(
    monthly_signal_long: pd.DataFrame,
    experiment_design: pd.DataFrame,
) -> pd.DataFrame:
    frames = []

    for _, exp_row in experiment_design.iterrows():
        state_table = build_state_table_for_experiment(
            monthly_signal_long=monthly_signal_long,
            experiment_row=exp_row,
        )
        frames.append(state_table)

    return pd.concat(frames, ignore_index=True)


def build_state_distribution(state_table: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for experiment_id, g in state_table.groupby("experiment_id"):
        total_months = len(g)
        valid_months = int(g["state_valid"].sum())

        dist = (
            g.groupby(["hsi_state", "state_valid"], dropna=False)
            .size()
            .reset_index(name="month_count")
        )

        for _, row in dist.iterrows():
            share_all = row["month_count"] / total_months if total_months > 0 else np.nan
            share_valid = (
                row["month_count"] / valid_months
                if row["state_valid"] and valid_months > 0
                else np.nan
            )

            rows.append({
                "experiment_id": experiment_id,
                "experiment_name": g["experiment_name"].iloc[0],
                "hsi_state": row["hsi_state"],
                "state_valid": row["state_valid"],
                "month_count": row["month_count"],
                "share_all_months": share_all,
                "share_valid_months": share_valid,
            })

    return pd.DataFrame(rows)


# ============================================================
# 5. 백테스트
# ============================================================

def get_weights_for_state(hsi_state: str) -> dict:
    if hsi_state not in STATE_ALLOCATION_RULES:
        raise ValueError(f"정의되지 않은 HSI 상태입니다: {hsi_state}")

    rule = STATE_ALLOCATION_RULES[hsi_state]

    return {
        RISK_TICKER: rule[RISK_TICKER],
        BOND_TICKER: rule[BOND_TICKER],
        CASH_TICKER: rule[CASH_TICKER],
    }


def build_rebalance_weights(
    state_table: pd.DataFrame,
    monthly_returns_decimal: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    available_return_months = set(monthly_returns_decimal.index.astype(str))

    valid_states = state_table[state_table["state_valid"] == True].copy()
    valid_states = valid_states.sort_values(["experiment_id", "year_month"])

    for _, row in valid_states.iterrows():
        signal_month = str(row["year_month"])
        return_month = str(pd.Period(signal_month, freq="M") + 1)

        if return_month not in available_return_months:
            continue

        hsi_state = row["hsi_state"]
        weights = get_weights_for_state(hsi_state)

        for ticker, weight in weights.items():
            rows.append({
                "experiment_id": row["experiment_id"],
                "strategy_name": row["experiment_id"],
                "signal_month": signal_month,
                "return_month": return_month,
                "ticker": ticker,
                "weight": weight,
                "hsi_state": hsi_state,
                "hsi_direction": row["hsi_direction"],
                "hsi_intensity": row["hsi_intensity"],
                "allocation_rule": "main_v2b_fixed",
            })

    return pd.DataFrame(rows)


def build_strategy_returns(
    rebalance_weights: pd.DataFrame,
    monthly_returns_decimal: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    group_cols = ["experiment_id", "signal_month", "return_month", "hsi_state"]

    for keys, g in rebalance_weights.groupby(group_cols):
        experiment_id, signal_month, return_month, hsi_state = keys

        portfolio_return = 0.0

        for _, row in g.iterrows():
            ticker = row["ticker"]
            weight = row["weight"]
            asset_return = monthly_returns_decimal.loc[return_month, ticker]
            portfolio_return += weight * asset_return

        rows.append({
            "experiment_id": experiment_id,
            "strategy_name": experiment_id,
            "signal_month": signal_month,
            "return_month": return_month,
            "hsi_state": hsi_state,
            "monthly_return": portfolio_return,
            "strategy_type": "HSI_combo",
        })

    return pd.DataFrame(rows).sort_values(["experiment_id", "return_month"])


def build_matched_ew_returns(
    hsi_returns: pd.DataFrame,
    monthly_returns_decimal: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for experiment_id, g in hsi_returns.groupby("experiment_id"):
        return_months = g["return_month"].drop_duplicates().tolist()

        for return_month in return_months:
            ew_return = monthly_returns_decimal.loc[return_month, TICKERS].mean()

            rows.append({
                "experiment_id": experiment_id,
                "strategy_name": f"{STRATEGY_EW_PREFIX}_{experiment_id}",
                "signal_month": "",
                "return_month": return_month,
                "hsi_state": "benchmark",
                "monthly_return": ew_return,
                "strategy_type": "EW_matched",
            })

    return pd.DataFrame(rows).sort_values(["experiment_id", "return_month"])


def add_cumulative_and_drawdown(strategy_returns: pd.DataFrame) -> pd.DataFrame:
    required_cols = ["strategy_name", "return_month", "monthly_return"]

    missing_cols = [c for c in required_cols if c not in strategy_returns.columns]
    if missing_cols:
        raise KeyError(
            f"strategy_returns에 필요한 컬럼이 없습니다: {missing_cols}\n"
            f"현재 컬럼: {list(strategy_returns.columns)}"
        )

    frames = []

    for strategy_name, g in strategy_returns.groupby("strategy_name"):
        g = g.sort_values("return_month").copy()

        growth = (1.0 + g["monthly_return"].astype(float)).cumprod()

        g["strategy_name"] = strategy_name
        g["growth_index"] = growth
        g["cumulative_return"] = growth - 1.0
        g["drawdown"] = growth / growth.cummax() - 1.0

        frames.append(g)

    out = pd.concat(frames, ignore_index=True)

    out["monthly_return_pct"] = out["monthly_return"] * 100.0
    out["cumulative_return_pct"] = out["cumulative_return"] * 100.0
    out["drawdown_pct"] = out["drawdown"] * 100.0

    return out.sort_values(["experiment_id", "strategy_name", "return_month"])


def calculate_performance_summary(backtest_ts: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for strategy_name, g in backtest_ts.groupby("strategy_name"):
        g = g.sort_values("return_month").copy()

        r = g["monthly_return"].astype(float)
        months = len(r)

        total_return = g["growth_index"].iloc[-1] - 1.0
        cagr = (1.0 + total_return) ** (12.0 / months) - 1.0 if months > 0 else np.nan

        annual_return_arithmetic = r.mean() * 12.0
        annual_volatility = r.std(ddof=1) * np.sqrt(12.0) if months > 1 else np.nan

        downside = r[r < 0]
        downside_volatility = downside.std(ddof=1) * np.sqrt(12.0) if len(downside) > 1 else np.nan

        sharpe = (
            annual_return_arithmetic / annual_volatility
            if annual_volatility is not None and annual_volatility > 0
            else np.nan
        )

        sortino = (
            annual_return_arithmetic / downside_volatility
            if downside_volatility is not None and downside_volatility > 0
            else np.nan
        )

        mdd = g["drawdown"].min()
        calmar = cagr / abs(mdd) if mdd < 0 else np.nan
        win_rate = (r > 0).mean()

        rows.append({
            "experiment_id": g["experiment_id"].iloc[0],
            "strategy_name": strategy_name,
            "strategy_type": g["strategy_type"].iloc[0],
            "months": months,
            "start_return_month": g["return_month"].iloc[0],
            "end_return_month": g["return_month"].iloc[-1],
            "total_return": total_return,
            "CAGR": cagr,
            "annual_volatility": annual_volatility,
            "MDD": mdd,
            "Sharpe": sharpe,
            "Sortino": sortino,
            "Calmar": calmar,
            "WinRate": win_rate,
            "avg_monthly_return": r.mean(),
            "best_month": r.max(),
            "worst_month": r.min(),
            "total_return_pct": total_return * 100.0,
            "CAGR_pct": cagr * 100.0,
            "annual_volatility_pct": annual_volatility * 100.0,
            "MDD_pct": mdd * 100.0,
            "WinRate_pct": win_rate * 100.0,
        })

    return pd.DataFrame(rows).sort_values(["experiment_id", "strategy_type"])


def calculate_turnover_summary(rebalance_weights: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for experiment_id, g in rebalance_weights.groupby("experiment_id"):
        wide = (
            g.pivot_table(
                index="return_month",
                columns="ticker",
                values="weight",
                aggfunc="first",
            )
            .sort_index()
        )

        turnover_values = []
        previous_weights = None

        for _, row in wide.iterrows():
            current_weights = row[TICKERS].astype(float)

            if previous_weights is None:
                turnover = 0.0
            else:
                turnover = 0.5 * (current_weights - previous_weights).abs().sum()

            turnover_values.append(turnover)
            previous_weights = current_weights

        turnover_series = pd.Series(turnover_values, dtype="float64")

        rows.append({
            "experiment_id": experiment_id,
            "strategy_name": experiment_id,
            "months": len(turnover_series),
            "avg_turnover": turnover_series.mean(),
            "max_turnover": turnover_series.max(),
            "total_turnover": turnover_series.sum(),
            "avg_turnover_pct": turnover_series.mean() * 100.0,
            "max_turnover_pct": turnover_series.max() * 100.0,
            "total_turnover_pct": turnover_series.sum() * 100.0,
        })

    return pd.DataFrame(rows).sort_values("experiment_id")


# ============================================================
# 6. 후보 판단
# ============================================================

def build_candidate_judgement(
    experiment_design: pd.DataFrame,
    performance_summary: pd.DataFrame,
    turnover_summary: pd.DataFrame,
    state_distribution: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    hsi_perf = performance_summary[performance_summary["strategy_type"] == "HSI_combo"].copy()
    ew_perf = performance_summary[performance_summary["strategy_type"] == "EW_matched"].copy()

    for _, exp in experiment_design.iterrows():
        experiment_id = exp["experiment_id"]

        hsi_row = hsi_perf[hsi_perf["experiment_id"] == experiment_id].iloc[0]
        ew_row = ew_perf[ew_perf["experiment_id"] == experiment_id].iloc[0]
        turnover_row = turnover_summary[turnover_summary["experiment_id"] == experiment_id].iloc[0]

        state_dist = state_distribution[
            (state_distribution["experiment_id"] == experiment_id)
            & (state_distribution["state_valid"] == True)
        ]

        if len(state_dist) > 0:
            max_state_share = state_dist["share_valid_months"].max()
            dominant_state = state_dist.loc[state_dist["share_valid_months"].idxmax(), "hsi_state"]
            valid_state_count = state_dist["hsi_state"].nunique()
        else:
            max_state_share = np.nan
            dominant_state = ""
            valid_state_count = 0

        cagr_gap = hsi_row["CAGR"] - ew_row["CAGR"]
        mdd_improvement = hsi_row["MDD"] - ew_row["MDD"]
        sharpe_gap = hsi_row["Sharpe"] - ew_row["Sharpe"]
        calmar_gap = hsi_row["Calmar"] - ew_row["Calmar"]

        avg_turnover = turnover_row["avg_turnover"]
        max_turnover = turnover_row["max_turnover"]

        reasons = []

        if mdd_improvement > 0:
            reasons.append("MDD improved vs matched EW")
        else:
            reasons.append("MDD not improved vs matched EW")

        if avg_turnover <= 0.05:
            reasons.append("avg turnover <= 5%")
        else:
            reasons.append("avg turnover > 5%")

        if max_turnover <= 0.25:
            reasons.append("max turnover <= 25%")
        else:
            reasons.append("max turnover > 25%")

        if valid_state_count >= 3 and (not pd.isna(max_state_share)) and max_state_share <= 0.60:
            reasons.append("state distribution is not overly concentrated")
        else:
            reasons.append("state distribution concentration needs review")

        if mdd_improvement > 0 and avg_turnover <= 0.05 and max_turnover <= 0.25:
            judgement = "candidate"
        elif max_turnover <= 0.25:
            judgement = "review"
        else:
            judgement = "exclude_or_revise"

        rows.append({
            "experiment_id": experiment_id,
            "experiment_name": exp["experiment_name"],
            "signal_set_type": exp["signal_set_type"],
            "judgement": judgement,
            "months": hsi_row["months"],
            "CAGR_pct": hsi_row["CAGR_pct"],
            "EW_CAGR_pct": ew_row["CAGR_pct"],
            "CAGR_gap_pct": cagr_gap * 100.0,
            "MDD_pct": hsi_row["MDD_pct"],
            "EW_MDD_pct": ew_row["MDD_pct"],
            "MDD_improvement_pct": mdd_improvement * 100.0,
            "Sharpe": hsi_row["Sharpe"],
            "EW_Sharpe": ew_row["Sharpe"],
            "Sharpe_gap": sharpe_gap,
            "Calmar": hsi_row["Calmar"],
            "EW_Calmar": ew_row["Calmar"],
            "Calmar_gap": calmar_gap,
            "avg_turnover_pct": turnover_row["avg_turnover_pct"],
            "max_turnover_pct": turnover_row["max_turnover_pct"],
            "dominant_state": dominant_state,
            "max_state_share": max_state_share,
            "valid_state_count": valid_state_count,
            "selection_reason": " | ".join(reasons),
            "caution": "성과 1등이 아니라 MDD, Turnover, 상태분포, 해석 가능성을 함께 검토해야 함",
        })

    return pd.DataFrame(rows).sort_values(
        ["judgement", "MDD_improvement_pct", "Calmar_gap"],
        ascending=[True, False, False],
    )


def build_alignment_check(
    state_table: pd.DataFrame,
    rebalance_weights: pd.DataFrame,
    backtest_ts: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    for experiment_id, g in state_table.groupby("experiment_id"):
        valid_state_months = int(g["state_valid"].sum())

        rb = rebalance_weights[rebalance_weights["experiment_id"] == experiment_id]
        bt = backtest_ts[
            (backtest_ts["experiment_id"] == experiment_id)
            & (backtest_ts["strategy_type"] == "HSI_combo")
        ]

        rows.append({
            "experiment_id": experiment_id,
            "valid_state_months": valid_state_months,
            "signal_months_used": rb["signal_month"].nunique() if len(rb) > 0 else 0,
            "return_months_used": bt["return_month"].nunique() if len(bt) > 0 else 0,
            "first_valid_state_month": (
                g.loc[g["state_valid"], "year_month"].iloc[0]
                if valid_state_months > 0
                else ""
            ),
            "last_valid_state_month": (
                g.loc[g["state_valid"], "year_month"].iloc[-1]
                if valid_state_months > 0
                else ""
            ),
            "alignment_rule": "signal_month_t_to_return_month_t_plus_1",
            "status": "OK" if len(bt) > 0 else "CHECK",
            "note": "월말 HSI 상태를 다음 달 수익률에 적용",
        })

    return pd.DataFrame(rows)


# ============================================================
# 7. Markdown 노트
# ============================================================

def make_markdown_note(
    experiment_design: pd.DataFrame,
    performance_summary: pd.DataFrame,
    turnover_summary: pd.DataFrame,
    candidate_judgement: pd.DataFrame,
) -> str:
    lines = []

    lines.append("# main_v3 신호 조합별 백테스트 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "35번에서 생성한 추가 지표 후보를 사용해 신호 조합별 HSI 상태분류와 "
        "main_v2b 기준 백테스트를 수행하였다. "
        "ETF 유니버스와 비중 규칙은 고정하고, 신호 조합만 바꾸었다."
    )
    lines.append("")
    lines.append("## 2. 실험 설계")
    lines.append("")
    lines.append("| experiment_id | experiment_name | signal_count | main_question |")
    lines.append("|---|---|---:|---|")

    for _, row in experiment_design.iterrows():
        lines.append(
            f"| {row['experiment_id']} | {row['experiment_name']} | "
            f"{row['signal_count']} | {row['main_question']} |"
        )

    lines.append("")
    lines.append("## 3. 성과 요약")
    lines.append("")
    lines.append("| strategy_name | strategy_type | months | CAGR_pct | MDD_pct | Sharpe | Calmar | WinRate_pct |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")

    display_perf = performance_summary[
        performance_summary["strategy_type"] == "HSI_combo"
    ].copy()

    for _, row in display_perf.iterrows():
        lines.append(
            f"| {row['strategy_name']} | {row['strategy_type']} | {row['months']} | "
            f"{row['CAGR_pct']:.2f} | {row['MDD_pct']:.2f} | "
            f"{row['Sharpe']:.4f} | {row['Calmar']:.4f} | {row['WinRate_pct']:.2f} |"
        )

    lines.append("")
    lines.append("## 4. Turnover 요약")
    lines.append("")
    lines.append("| experiment_id | avg_turnover_pct | max_turnover_pct | total_turnover_pct |")
    lines.append("|---|---:|---:|---:|")

    for _, row in turnover_summary.iterrows():
        lines.append(
            f"| {row['experiment_id']} | {row['avg_turnover_pct']:.2f} | "
            f"{row['max_turnover_pct']:.2f} | {row['total_turnover_pct']:.2f} |"
        )

    lines.append("")
    lines.append("## 5. 후보 판단")
    lines.append("")
    lines.append("| experiment_id | judgement | CAGR_gap_pct | MDD_improvement_pct | avg_turnover_pct | max_turnover_pct | selection_reason |")
    lines.append("|---|---|---:|---:|---:|---:|---|")

    for _, row in candidate_judgement.iterrows():
        lines.append(
            f"| {row['experiment_id']} | {row['judgement']} | "
            f"{row['CAGR_gap_pct']:.2f} | {row['MDD_improvement_pct']:.2f} | "
            f"{row['avg_turnover_pct']:.2f} | {row['max_turnover_pct']:.2f} | "
            f"{row['selection_reason']} |"
        )

    lines.append("")
    lines.append("## 6. 해석 원칙")
    lines.append("")
    lines.append(
        "이번 실험은 가장 높은 CAGR을 찾기 위한 절차가 아니라, "
        "추가 신호 조합이 MDD, Turnover, 상태분포, 위험조정 성과 측면에서 "
        "기본 HSI보다 개선되는지 확인하기 위한 비교 실험이다."
    )
    lines.append("")
    lines.append("## 7. 다음 단계")
    lines.append("")
    lines.append(
        "다음 단계에서는 성과표와 후보 판단표를 확인한 뒤, "
        "후보 조합에 대해 θ 민감도 또는 사건균형지표 보조 진단을 붙일지 결정한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 8. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("36_main_v3_run_signal_combo_backtests.py 실행 시작")
    print("=" * 80)

    print("[1] 입력 파일 확인")
    require_file(INPUT_EXTENDED_LONG)
    require_file(INPUT_MONTHLY_RETURNS)

    print(f"    OK: {INPUT_EXTENDED_LONG}")
    print(f"    OK: {INPUT_MONTHLY_RETURNS}")

    print("[2] 입력 데이터 로드")
    monthly_signal_long = pd.read_csv(
        INPUT_EXTENDED_LONG,
        dtype={"ticker": str},
        encoding="utf-8-sig",
    )
    monthly_signal_long["ticker"] = monthly_signal_long["ticker"].astype(str).str.zfill(6)
    monthly_signal_long["year_month"] = monthly_signal_long["year_month"].astype(str)

    monthly_returns_decimal = read_monthly_returns(INPUT_MONTHLY_RETURNS)

    print(f"    monthly_signal_long shape = {monthly_signal_long.shape}")
    print(f"    monthly_returns_decimal shape = {monthly_returns_decimal.shape}")

    print("[3] 신호 조합 실험 설계표 생성")
    experiment_design = make_experiment_design()

    print("[4] 신호 조합별 HSI 5상태 분류")
    state_table = build_all_state_tables(
        monthly_signal_long=monthly_signal_long,
        experiment_design=experiment_design,
    )

    print("[5] 상태분포 생성")
    state_distribution = build_state_distribution(state_table)

    print("[6] HSI 상태표 → 리밸런싱 비중표 생성")
    rebalance_weights = build_rebalance_weights(
        state_table=state_table,
        monthly_returns_decimal=monthly_returns_decimal,
    )

    print("[7] 신호 조합별 HSI 전략 수익률 계산")
    hsi_returns = build_strategy_returns(
        rebalance_weights=rebalance_weights,
        monthly_returns_decimal=monthly_returns_decimal,
    )

    print("[8] 각 조합별 matched EW 수익률 계산")
    ew_returns = build_matched_ew_returns(
        hsi_returns=hsi_returns,
        monthly_returns_decimal=monthly_returns_decimal,
    )

    print("[9] 누적수익률 및 Drawdown 계산")
    all_returns = pd.concat([hsi_returns, ew_returns], ignore_index=True)
    backtest_ts = add_cumulative_and_drawdown(all_returns)

    print("[10] 성과요약 계산")
    performance_summary = calculate_performance_summary(backtest_ts)

    print("[11] Turnover 요약 계산")
    turnover_summary = calculate_turnover_summary(rebalance_weights)

    print("[12] 후보 판단표 생성")
    candidate_judgement = build_candidate_judgement(
        experiment_design=experiment_design,
        performance_summary=performance_summary,
        turnover_summary=turnover_summary,
        state_distribution=state_distribution,
    )

    print("[13] 시점 정합성 점검표 생성")
    alignment_check = build_alignment_check(
        state_table=state_table,
        rebalance_weights=rebalance_weights,
        backtest_ts=backtest_ts,
    )

    print("[14] CSV 저장")
    state_table.to_csv(OUTPUT_STATE_TABLE, index=False, encoding="utf-8-sig")
    rebalance_weights.to_csv(OUTPUT_REBALANCE_WEIGHTS, index=False, encoding="utf-8-sig")
    backtest_ts.to_csv(OUTPUT_BACKTEST_TS, index=False, encoding="utf-8-sig")

    experiment_design.to_csv(OUTPUT_EXPERIMENT_DESIGN, index=False, encoding="utf-8-sig")
    state_distribution.to_csv(OUTPUT_STATE_DISTRIBUTION, index=False, encoding="utf-8-sig")
    performance_summary.to_csv(OUTPUT_PERFORMANCE, index=False, encoding="utf-8-sig")
    turnover_summary.to_csv(OUTPUT_TURNOVER, index=False, encoding="utf-8-sig")
    candidate_judgement.to_csv(OUTPUT_CANDIDATE_JUDGEMENT, index=False, encoding="utf-8-sig")
    alignment_check.to_csv(OUTPUT_ALIGNMENT_CHECK, index=False, encoding="utf-8-sig")

    print("[15] Markdown 노트 저장")
    note = make_markdown_note(
        experiment_design=experiment_design,
        performance_summary=performance_summary,
        turnover_summary=turnover_summary,
        candidate_judgement=candidate_judgement,
    )
    OUTPUT_NOTE.write_text(note, encoding="utf-8")

    print("\n[저장 완료]")
    for path in [
        OUTPUT_STATE_TABLE,
        OUTPUT_REBALANCE_WEIGHTS,
        OUTPUT_BACKTEST_TS,
        OUTPUT_EXPERIMENT_DESIGN,
        OUTPUT_STATE_DISTRIBUTION,
        OUTPUT_PERFORMANCE,
        OUTPUT_TURNOVER,
        OUTPUT_CANDIDATE_JUDGEMENT,
        OUTPUT_ALIGNMENT_CHECK,
        OUTPUT_NOTE,
    ]:
        print(f"- {path}")

    print("\n[HSI 조합별 성과요약]")
    display_cols = [
        "experiment_id",
        "strategy_name",
        "months",
        "CAGR_pct",
        "annual_volatility_pct",
        "MDD_pct",
        "Sharpe",
        "Sortino",
        "Calmar",
        "WinRate_pct",
    ]

    print(
        performance_summary[
            performance_summary["strategy_type"] == "HSI_combo"
        ][display_cols].to_string(index=False)
    )

    print("\n[Turnover 요약]")
    print(turnover_summary.to_string(index=False))

    print("\n[후보 판단]")
    judgement_cols = [
        "experiment_id",
        "judgement",
        "CAGR_gap_pct",
        "MDD_improvement_pct",
        "Sharpe_gap",
        "Calmar_gap",
        "avg_turnover_pct",
        "max_turnover_pct",
        "dominant_state",
        "max_state_share",
        "selection_reason",
    ]
    print(candidate_judgement[judgement_cols].to_string(index=False))

    print("\n[시점 정합성 점검]")
    print(alignment_check.to_string(index=False))

    print("\n" + "=" * 80)
    print("36_main_v3_run_signal_combo_backtests.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()