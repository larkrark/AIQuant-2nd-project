from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
04_build_hsi_state5_baseline.py

목적
----
03번에서 만든 월말 HSI 신호 입력표를 이용해
최종 baseline HSI 5상태를 생성한다.

생성 상태
---------
risk_relief
neutral_watch
conflict
risk_warning
accident_zone
insufficient_data

중요
----
이 파일은 아직 백테스트를 하지 않는다.
월말 HSI 상태표를 만들고, 다음 달 수익률과 연결 가능한지 미리보기만 만든다.

입력
----
data/processed/main_final_monthly_signal_inputs_long.csv
data/processed/main_final_monthly_return_decimal.csv

출력
----
data/processed/main_final_hsi_state5_table.csv
data/processed/main_final_hsi_state_return_alignment_preview.csv

output/tables/main_final_hsi_state5_distribution.csv
output/tables/main_final_hsi_state5_quality_check.csv

docs/main_final_hsi_state5_note.md
"""


INPUT_MONTHLY_SIGNAL_LONG = cfg.PROCESSED_DIR / "main_final_monthly_signal_inputs_long.csv"
INPUT_MONTHLY_RETURNS = cfg.PROCESSED_DIR / "main_final_monthly_return_decimal.csv"

OUTPUT_STATE_TABLE = cfg.PROCESSED_DIR / "main_final_hsi_state5_table.csv"
OUTPUT_ALIGNMENT_PREVIEW = cfg.PROCESSED_DIR / "main_final_hsi_state_return_alignment_preview.csv"

OUTPUT_DISTRIBUTION = cfg.TABLE_DIR / "main_final_hsi_state5_distribution.csv"
OUTPUT_QUALITY_CHECK = cfg.TABLE_DIR / "main_final_hsi_state5_quality_check.csv"
OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_hsi_state5_note.md"


YEAR_MONTH_COL = "year_month"
TICKER_COL = "ticker"

MARKET_STATE_TICKER = cfg.RISK_TICKER

SCORE_COLS = [
    "score_return",
    "score_ma_pos",
    "score_momentum",
    "score_vol",
    "score_rs",
]

SCORE_SCALE = 10.0
MIN_VALID_SCORE_COUNT = 3

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


def classify_hsi_state(row: pd.Series) -> pd.Series:
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


def build_state_table(monthly_long: pd.DataFrame) -> pd.DataFrame:
    df = monthly_long.copy()
    df[TICKER_COL] = df[TICKER_COL].astype(str).str.zfill(6)

    market_df = df[df[TICKER_COL] == MARKET_STATE_TICKER].copy()

    if market_df.empty:
        raise ValueError(f"시장상태 기준 티커 {MARKET_STATE_TICKER} 행이 없습니다.")

    for col in SCORE_COLS:
        if col not in market_df.columns:
            market_df[col] = np.nan

    state_features = market_df.apply(classify_hsi_state, axis=1)

    keep_cols = [
        YEAR_MONTH_COL,
        TICKER_COL,
        "ticker_name",
        "ticker_role",
        "score_date",
        "direction_date",
        "raw3_signal_date",
        "hsi_direction",
        "raw3_signal",
    ] + SCORE_COLS

    optional_cols = [
        "event_balance_13612w",
        "event_intensity_13612w",
        "event_balance_13612w_label",
        "event_intensity_13612w_label",
    ]

    keep_cols = [c for c in keep_cols + optional_cols if c in market_df.columns]

    out = pd.concat(
        [
            market_df[keep_cols].reset_index(drop=True),
            state_features.reset_index(drop=True),
        ],
        axis=1,
    )

    out["state_kr"] = out["hsi_state"].map(cfg.HSI_STATE_KR)
    out["state_rule_version"] = "state5_baseline_v1"
    out["theta_common"] = THETA_COMMON
    out["accident_extra"] = ACCIDENT_EXTRA
    out["conflict_direction_band"] = CONFLICT_DIRECTION_BAND

    return out


def build_distribution(state_table: pd.DataFrame) -> pd.DataFrame:
    dist = (
        state_table["hsi_state"]
        .value_counts(dropna=False)
        .rename_axis("hsi_state")
        .reset_index(name="months")
    )

    total_months = dist["months"].sum()
    valid_total = state_table[state_table["hsi_state"] != "insufficient_data"].shape[0]

    dist["ratio_total"] = dist["months"] / total_months
    dist["ratio_valid"] = np.where(
        dist["hsi_state"] != "insufficient_data",
        dist["months"] / valid_total if valid_total > 0 else np.nan,
        np.nan,
    )
    dist["state_kr"] = dist["hsi_state"].map(cfg.HSI_STATE_KR)

    order = {
        "risk_relief": 1,
        "neutral_watch": 2,
        "conflict": 3,
        "risk_warning": 4,
        "accident_zone": 5,
        "insufficient_data": 6,
    }

    dist["state_order"] = dist["hsi_state"].map(order)
    dist = dist.sort_values("state_order").drop(columns=["state_order"]).reset_index(drop=True)

    return dist


def build_alignment_preview(state_table: pd.DataFrame, monthly_returns: pd.DataFrame) -> pd.DataFrame:
    returns = monthly_returns.copy()

    if YEAR_MONTH_COL not in returns.columns:
        first_col = returns.columns[0]
        returns = returns.rename(columns={first_col: YEAR_MONTH_COL})

    returns[YEAR_MONTH_COL] = returns[YEAR_MONTH_COL].astype(str)

    signals = state_table[[YEAR_MONTH_COL, "hsi_state", "state_kr"]].copy()
    signals["return_year_month"] = (
        pd.PeriodIndex(signals[YEAR_MONTH_COL], freq="M") + 1
    ).astype(str)

    keep_return_cols = [YEAR_MONTH_COL] + [t for t in cfg.TICKERS if t in returns.columns]
    returns = returns[keep_return_cols].rename(columns={YEAR_MONTH_COL: "return_year_month"})

    aligned = signals.merge(returns, on="return_year_month", how="left")

    for ticker in cfg.TICKERS:
        if ticker in aligned.columns:
            aligned = aligned.rename(columns={ticker: f"next_return_{ticker}"})

    aligned["alignment_rule"] = cfg.ALIGNMENT_RULE

    return aligned


def build_quality_check(state_table: pd.DataFrame, alignment_preview: pd.DataFrame) -> pd.DataFrame:
    valid = state_table[state_table["hsi_state"] != "insufficient_data"].copy()

    next_return_cols = [c for c in alignment_preview.columns if c.startswith("next_return_")]
    missing_return_cells = (
        alignment_preview[next_return_cols].isna().sum().sum()
        if next_return_cols else 0
    )

    rows = [
        {
            "item": "state_table_rows",
            "value": len(state_table),
            "status": "OK" if len(state_table) > 0 else "CHECK",
            "note": "월말 HSI 5상태표 행 수",
        },
        {
            "item": "valid_state_months",
            "value": len(valid),
            "status": "OK" if len(valid) > 0 else "CHECK",
            "note": "insufficient_data 제외 유효 상태 월 수",
        },
        {
            "item": "first_valid_month",
            "value": valid[YEAR_MONTH_COL].min() if not valid.empty else "N/A",
            "status": "OK" if not valid.empty else "CHECK",
            "note": "첫 유효 상태 월",
        },
        {
            "item": "last_valid_month",
            "value": valid[YEAR_MONTH_COL].max() if not valid.empty else "N/A",
            "status": "OK" if not valid.empty else "CHECK",
            "note": "마지막 유효 상태 월",
        },
        {
            "item": "state_type_count",
            "value": valid["hsi_state"].nunique() if not valid.empty else 0,
            "status": "OK" if valid["hsi_state"].nunique() >= 3 else "CHECK",
            "note": "유효 상태 종류 수",
        },
        {
            "item": "alignment_preview_rows",
            "value": len(alignment_preview),
            "status": "OK" if len(alignment_preview) > 0 else "CHECK",
            "note": "signal_month t → return_month t+1 정렬 미리보기 행 수",
        },
        {
            "item": "alignment_missing_return_cells",
            "value": int(missing_return_cells),
            "status": "OK" if missing_return_cells <= len(next_return_cols) else "CHECK",
            "note": "마지막 월은 다음 달 수익률이 없어 정상 결측 가능",
        },
    ]

    return pd.DataFrame(rows)


def build_note(distribution: pd.DataFrame, quality: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_final HSI 5상태 기준선 생성 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 단계는 월말 HSI 점수를 이용해 risk_relief, neutral_watch, conflict, "
        "risk_warning, accident_zone의 5상태를 생성한다. "
        "HSI는 미래 수익률 예측값이 아니라 시장상태 해석 보조지표이다."
    )
    lines.append("")
    lines.append("## 2. 상태분류 기준")
    lines.append("")
    lines.append(f"- 기준 티커: `{MARKET_STATE_TICKER}`")
    lines.append(f"- 최소 유효 점수 수: `{MIN_VALID_SCORE_COUNT}`")
    lines.append(f"- θ 기준값: `{THETA_COMMON}`")
    lines.append(f"- accident extra: `{ACCIDENT_EXTRA}`")
    lines.append(f"- conflict direction band: `{CONFLICT_DIRECTION_BAND}`")
    lines.append("")
    lines.append("## 3. 상태분포")
    lines.append("")
    lines.append("| hsi_state | state_kr | months | ratio_total | ratio_valid |")
    lines.append("|---|---|---:|---:|---:|")
    for _, row in distribution.iterrows():
        lines.append(
            f"| {row['hsi_state']} | {row['state_kr']} | {row['months']} | "
            f"{row['ratio_total']:.4f} | "
            f"{row['ratio_valid'] if pd.notna(row['ratio_valid']) else ''} |"
        )
    lines.append("")
    lines.append("## 4. 품질 점검")
    lines.append("")
    lines.append("| item | value | status | note |")
    lines.append("|---|---:|---|---|")
    for _, row in quality.iterrows():
        lines.append(f"| {row['item']} | {row['value']} | {row['status']} | {row['note']} |")
    lines.append("")
    lines.append("## 5. 다음 단계")
    lines.append("")
    lines.append(
        "`05_backtest_baseline_allocation_rule.py`에서 이 상태표를 최종 baseline 리밸런싱 규칙과 연결해 "
        "EW 대비 HSI overlay 성과, Drawdown, Turnover를 계산한다."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("04_build_hsi_state5_baseline.py 실행 시작")
    print("=" * 80)

    cfg.ensure_final_directories()

    print("[1] 입력 파일 로드")
    monthly_long = read_csv(INPUT_MONTHLY_SIGNAL_LONG, "월말 HSI signal long")
    monthly_returns = read_csv(INPUT_MONTHLY_RETURNS, "월간 수익률 decimal")
    print(f"    monthly_long shape = {monthly_long.shape}")
    print(f"    monthly_returns shape = {monthly_returns.shape}")

    print("[2] HSI 5상태 생성")
    state_table = build_state_table(monthly_long)
    save_csv(state_table, OUTPUT_STATE_TABLE)
    print(f"    저장: {OUTPUT_STATE_TABLE}")

    print("[3] 상태분포 생성")
    distribution = build_distribution(state_table)
    save_csv(distribution, OUTPUT_DISTRIBUTION)
    print(f"    저장: {OUTPUT_DISTRIBUTION}")

    print("[4] signal_month t → return_month t+1 정렬 미리보기 생성")
    alignment_preview = build_alignment_preview(state_table, monthly_returns)
    save_csv(alignment_preview, OUTPUT_ALIGNMENT_PREVIEW)
    print(f"    저장: {OUTPUT_ALIGNMENT_PREVIEW}")

    print("[5] 품질 점검표 생성")
    quality = build_quality_check(state_table, alignment_preview)
    save_csv(quality, OUTPUT_QUALITY_CHECK)
    print(f"    저장: {OUTPUT_QUALITY_CHECK}")

    print("[6] Markdown 노트 저장")
    note = build_note(distribution, quality)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[상태분포]")
    print(distribution.to_string(index=False))

    print("\n[품질 점검]")
    print(quality.to_string(index=False))

    print("\n[상태표 최근 12개월]")
    preview_cols = [
        YEAR_MONTH_COL,
        "hsi_state",
        "state_kr",
        "risk_component",
        "relief_component",
        "state_direction",
        "state_intensity",
        "state_reason",
    ]
    print(state_table[preview_cols].tail(12).to_string(index=False))

    print("=" * 80)
    print("04_build_hsi_state5_baseline.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()