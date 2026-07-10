from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
03_prepare_monthly_signal_inputs.py

목적
----
hsi_data_bundle.xlsx에서 분리한 일별 HSI 관련 자료를 월말 기준으로 정리한다.

이 파일은 HSI 5상태를 아직 만들지 않는다.
역할은 04_build_hsi_state5_baseline.py가 바로 사용할 수 있도록
월말 HSI 점수, direction, raw 3단계 signal, 원신호, 사건균형지표를
한 곳에 정리하는 것이다.

입력
----
data/processed/main_final_signal_inputs.csv
data/processed/main_final_hsi_scaled_scores.csv
data/processed/main_final_hsi_direction.csv
data/processed/main_final_hsi_signal_raw3.csv
data/processed/main_final_monthly_return_decimal.csv
data/processed/main_final_hsi_event_balance_monthly.csv

출력
----
data/processed/main_final_monthly_signal_scores_wide.csv
data/processed/main_final_monthly_signal_inputs_long.csv
data/processed/main_final_monthly_signal_inputs_wide.csv
data/processed/main_final_monthly_signal_return_alignment_preview.csv

output/tables/main_final_monthly_signal_column_map.csv
output/tables/main_final_monthly_signal_availability_check.csv
output/tables/main_final_monthly_signal_quality_check.csv

docs/main_final_monthly_signal_input_note.md
"""


# ============================================================
# 1. 입력 경로
# ============================================================

INPUT_SIGNAL_INPUTS = cfg.PROCESSED_DIR / "main_final_signal_inputs.csv"
INPUT_HSI_SCORES = cfg.PROCESSED_DIR / "main_final_hsi_scaled_scores.csv"
INPUT_HSI_DIRECTION = cfg.PROCESSED_DIR / "main_final_hsi_direction.csv"
INPUT_HSI_SIGNAL_RAW3 = cfg.PROCESSED_DIR / "main_final_hsi_signal_raw3.csv"
INPUT_MONTHLY_RETURNS = cfg.PROCESSED_DIR / "main_final_monthly_return_decimal.csv"
INPUT_EVENT_BALANCE_MONTHLY = cfg.PROCESSED_DIR / "main_final_hsi_event_balance_monthly.csv"


# ============================================================
# 2. 출력 경로
# ============================================================

OUTPUT_MONTHLY_SCORES_WIDE = cfg.PROCESSED_DIR / "main_final_monthly_signal_scores_wide.csv"
OUTPUT_MONTHLY_INPUTS_LONG = cfg.PROCESSED_DIR / "main_final_monthly_signal_inputs_long.csv"
OUTPUT_MONTHLY_INPUTS_WIDE = cfg.PROCESSED_DIR / "main_final_monthly_signal_inputs_wide.csv"
OUTPUT_ALIGNMENT_PREVIEW = cfg.PROCESSED_DIR / "main_final_monthly_signal_return_alignment_preview.csv"

OUTPUT_COLUMN_MAP = cfg.TABLE_DIR / "main_final_monthly_signal_column_map.csv"
OUTPUT_AVAILABILITY_CHECK = cfg.TABLE_DIR / "main_final_monthly_signal_availability_check.csv"
OUTPUT_QUALITY_CHECK = cfg.TABLE_DIR / "main_final_monthly_signal_quality_check.csv"

OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_monthly_signal_input_note.md"


# ============================================================
# 3. 기본 설정
# ============================================================

DATE_COL = "Date"
YEAR_MONTH_COL = "year_month"
TICKER_COL = "ticker"

SCORE_SIGNAL_NAMES = [
    "return",
    "ma_pos",
    "momentum",
    "vol",
    "rs",
]

RAW_SIGNAL_COLUMNS = [
    "ret_1m",
    "ret_3m",
    "ma_gap",
    "momentum",
    "volatility",
    "relative_strength",
    "ret_6m",
    "ret_12m",
    "drawdown",
    "shock_count",
    "defensive_rs",
]

EVENT_BALANCE_COLUMNS = [
    "event_balance_raw",
    "event_intensity_raw",
    "event_balance_13612w",
    "event_intensity_13612w",
    "event_balance_13612w_label",
    "event_intensity_13612w_label",
]

MONTH_END_RULE = "ME"


# ============================================================
# 4. 공통 유틸
# ============================================================

def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")


def require_input(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"{label} 파일이 없습니다: {path}\n"
            "앞 단계가 정상 실행되었는지 확인하세요."
        )


def read_csv(path: Path, label: str) -> pd.DataFrame:
    require_input(path, label)
    return pd.read_csv(path, encoding="utf-8-sig")


def normalize_date_column(df: pd.DataFrame, date_col: str = DATE_COL) -> pd.DataFrame:
    out = df.copy()

    if date_col not in out.columns:
        first_col = out.columns[0]
        if str(first_col).startswith("Unnamed"):
            out = out.rename(columns={first_col: date_col})
        else:
            out = out.rename(columns={first_col: date_col})

    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out = out.dropna(subset=[date_col])
    out = out.sort_values(date_col).reset_index(drop=True)

    return out


def normalize_year_month_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if YEAR_MONTH_COL not in out.columns:
        first_col = out.columns[0]
        if str(first_col).startswith("Unnamed"):
            out = out.rename(columns={first_col: YEAR_MONTH_COL})
        else:
            out = out.rename(columns={first_col: YEAR_MONTH_COL})

    out[YEAR_MONTH_COL] = out[YEAR_MONTH_COL].astype(str)

    return out


def resample_month_end_wide(df: pd.DataFrame, date_label: str) -> pd.DataFrame:
    """
    Date 컬럼이 있는 일별 wide DataFrame을 월말 기준으로 last 추출한다.
    """
    temp = normalize_date_column(df, DATE_COL)
    temp = temp.set_index(DATE_COL).sort_index()

    try:
        monthly = temp.resample(MONTH_END_RULE).last()
    except ValueError:
        monthly = temp.resample("M").last()

    monthly = monthly.reset_index()
    monthly[YEAR_MONTH_COL] = monthly[DATE_COL].dt.to_period("M").astype(str)
    monthly[date_label] = monthly[DATE_COL].dt.strftime("%Y-%m-%d")
    monthly = monthly.drop(columns=[DATE_COL])

    cols = [YEAR_MONTH_COL, date_label] + [
        c for c in monthly.columns if c not in [YEAR_MONTH_COL, date_label]
    ]
    monthly = monthly[cols]

    return monthly


# ============================================================
# 5. 월말 raw signal_inputs 생성
# ============================================================

def make_monthly_raw_signal_inputs(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    signal_inputs long 자료를 ticker별 월말 기준으로 정리한다.
    """
    df = raw_df.copy()

    if "Ticker" in df.columns and TICKER_COL not in df.columns:
        df = df.rename(columns={"Ticker": TICKER_COL})

    if DATE_COL not in df.columns:
        raise ValueError(f"signal_inputs에 {DATE_COL} 컬럼이 없습니다.")

    if TICKER_COL not in df.columns:
        raise ValueError(f"signal_inputs에 {TICKER_COL} 컬럼이 없습니다.")

    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df[TICKER_COL] = df[TICKER_COL].astype(str).str.zfill(6)
    df = df.dropna(subset=[DATE_COL])
    df = df.sort_values([TICKER_COL, DATE_COL])

    frames = []

    for ticker, group in df.groupby(TICKER_COL):
        temp = group.set_index(DATE_COL).sort_index()

        try:
            monthly = temp.resample(MONTH_END_RULE).last()
        except ValueError:
            monthly = temp.resample("M").last()

        monthly = monthly.reset_index()
        monthly[TICKER_COL] = ticker
        monthly[YEAR_MONTH_COL] = monthly[DATE_COL].dt.to_period("M").astype(str)
        monthly["raw_signal_date"] = monthly[DATE_COL].dt.strftime("%Y-%m-%d")
        monthly = monthly.drop(columns=[DATE_COL])

        frames.append(monthly)

    out = pd.concat(frames, ignore_index=True)
    out[TICKER_COL] = out[TICKER_COL].astype(str).str.zfill(6)

    cols = [YEAR_MONTH_COL, "raw_signal_date", TICKER_COL] + [
        c for c in out.columns if c not in [YEAR_MONTH_COL, "raw_signal_date", TICKER_COL]
    ]
    out = out[cols]

    return out


# ============================================================
# 6. 월말 score wide → long 변환
# ============================================================

def make_score_long(
    monthly_scores: pd.DataFrame,
    monthly_direction: pd.DataFrame,
    monthly_raw3: pd.DataFrame,
) -> pd.DataFrame:
    """
    월말 hsi_scaled_scores wide 자료를 ticker별 long 자료로 변환하고,
    hsi_direction, raw 3단계 signal을 붙인다.
    """
    rows = []

    for _, row in monthly_scores.iterrows():
        for ticker in cfg.TICKERS:
            item = {
                YEAR_MONTH_COL: row[YEAR_MONTH_COL],
                "score_date": row["score_date"],
                TICKER_COL: ticker,
                "ticker_name": cfg.TICKER_NAME_MAP.get(ticker, ""),
                "ticker_role": cfg.TICKER_ROLE_MAP.get(ticker, ""),
            }

            for sig in SCORE_SIGNAL_NAMES:
                source_col = f"{ticker}_{sig}"
                item[f"score_{sig}"] = row[source_col] if source_col in monthly_scores.columns else np.nan

            rows.append(item)

    score_long = pd.DataFrame(rows)

    # direction 붙이기
    direction_rows = []
    for _, row in monthly_direction.iterrows():
        for ticker in cfg.TICKERS:
            col = f"{ticker}_direction"
            direction_rows.append({
                YEAR_MONTH_COL: row[YEAR_MONTH_COL],
                TICKER_COL: ticker,
                "direction_date": row["direction_date"],
                "hsi_direction": row[col] if col in monthly_direction.columns else np.nan,
            })

    direction_long = pd.DataFrame(direction_rows)

    # raw 3단계 signal 붙이기
    raw3_rows = []
    for _, row in monthly_raw3.iterrows():
        for ticker in cfg.TICKERS:
            col = f"{ticker}_signal"
            raw3_rows.append({
                YEAR_MONTH_COL: row[YEAR_MONTH_COL],
                TICKER_COL: ticker,
                "raw3_signal_date": row["raw3_signal_date"],
                "raw3_signal": row[col] if col in monthly_raw3.columns else np.nan,
            })

    raw3_long = pd.DataFrame(raw3_rows)

    out = score_long.merge(
        direction_long,
        on=[YEAR_MONTH_COL, TICKER_COL],
        how="left",
    ).merge(
        raw3_long,
        on=[YEAR_MONTH_COL, TICKER_COL],
        how="left",
    )

    return out


# ============================================================
# 7. 사건균형지표 병합
# ============================================================

def maybe_merge_event_balance(df: pd.DataFrame) -> pd.DataFrame:
    """
    02번 사건균형지표가 있으면 year_month 기준으로 병합한다.
    없으면 원본을 그대로 반환한다.
    """
    if not INPUT_EVENT_BALANCE_MONTHLY.exists():
        print("    INFO: 사건균형지표 파일이 아직 없습니다. event_balance 병합은 건너뜁니다.")
        return df

    event_df = pd.read_csv(INPUT_EVENT_BALANCE_MONTHLY, encoding="utf-8-sig")
    event_df = normalize_year_month_column(event_df)

    keep_cols = [YEAR_MONTH_COL] + [
        c for c in EVENT_BALANCE_COLUMNS if c in event_df.columns
    ]

    if len(keep_cols) <= 1:
        print("    INFO: 사건균형지표에 병합할 컬럼이 없습니다.")
        return df

    out = df.merge(event_df[keep_cols], on=YEAR_MONTH_COL, how="left")
    return out


# ============================================================
# 8. alignment preview
# ============================================================

def make_alignment_preview(monthly_wide: pd.DataFrame, monthly_returns: pd.DataFrame) -> pd.DataFrame:
    """
    signal_month t → return_month t+1 정렬 미리보기 생성.
    """
    signals = monthly_wide[[YEAR_MONTH_COL]].drop_duplicates().copy()
    signals[YEAR_MONTH_COL] = signals[YEAR_MONTH_COL].astype(str)
    signals["return_year_month"] = (
        pd.PeriodIndex(signals[YEAR_MONTH_COL], freq="M") + 1
    ).astype(str)

    returns = normalize_year_month_column(monthly_returns)

    for ticker in cfg.TICKERS:
        if ticker in returns.columns:
            returns[ticker] = pd.to_numeric(returns[ticker], errors="coerce")

    keep_cols = [YEAR_MONTH_COL] + [t for t in cfg.TICKERS if t in returns.columns]
    returns = returns[keep_cols].rename(columns={YEAR_MONTH_COL: "return_year_month"})

    aligned = signals.merge(returns, on="return_year_month", how="left")

    rename_map = {t: f"next_return_{t}" for t in cfg.TICKERS if t in aligned.columns}
    aligned = aligned.rename(columns=rename_map)

    aligned["alignment_rule"] = cfg.ALIGNMENT_RULE

    return aligned


# ============================================================
# 9. 점검표
# ============================================================

def build_column_map(monthly_long: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for col in monthly_long.columns:
        if col.startswith("score_"):
            source = "hsi_scaled_scores"
            role = "표준화·부호통일·스케일링된 HSI 점수"
        elif col in RAW_SIGNAL_COLUMNS:
            source = "signal_inputs"
            role = "부호 반전 전 원신호"
        elif col.startswith("event_"):
            source = "event_balance_monthly"
            role = "20/80 분위수 기반 사건균형·위험누적지표"
        elif col == "hsi_direction":
            source = "hsi_direction"
            role = "HSI 위험 악화/완화 방향 점수"
        elif col == "raw3_signal":
            source = "hsi_signal"
            role = "데이터 파트 3단계 raw signal"
        else:
            source = "derived_or_metadata"
            role = "식별자 또는 날짜 정보"

        rows.append({
            "column_name": col,
            "source": source,
            "role": role,
        })

    return pd.DataFrame(rows)


def build_availability_check(monthly_long: pd.DataFrame) -> pd.DataFrame:
    rows = []

    check_cols = [
        c for c in monthly_long.columns
        if c.startswith("score_")
        or c in RAW_SIGNAL_COLUMNS
        or c in ["hsi_direction", "raw3_signal"]
        or c in EVENT_BALANCE_COLUMNS
    ]

    for ticker in cfg.TICKERS:
        sub = monthly_long[monthly_long[TICKER_COL] == ticker].copy()

        for col in check_cols:
            if col not in sub.columns:
                continue

            valid = sub[sub[col].notna()]
            rows.append({
                "ticker": ticker,
                "ticker_name": cfg.TICKER_NAME_MAP.get(ticker, ""),
                "column_name": col,
                "valid_count": len(valid),
                "total_count": len(sub),
                "valid_ratio": len(valid) / len(sub) if len(sub) > 0 else np.nan,
                "first_valid_month": valid[YEAR_MONTH_COL].min() if not valid.empty else "N/A",
                "last_valid_month": valid[YEAR_MONTH_COL].max() if not valid.empty else "N/A",
                "status": "OK" if len(valid) > 0 else "CHECK",
            })

    return pd.DataFrame(rows)


def build_quality_check(
    monthly_scores: pd.DataFrame,
    monthly_long: pd.DataFrame,
    monthly_wide: pd.DataFrame,
    alignment_preview: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    rows.append({
        "item": "monthly_scores_wide_rows",
        "value": len(monthly_scores),
        "status": "OK" if len(monthly_scores) > 0 else "CHECK",
        "note": "월말 HSI score wide 행 수",
    })

    rows.append({
        "item": "monthly_signal_long_rows",
        "value": len(monthly_long),
        "status": "OK" if len(monthly_long) > 0 else "CHECK",
        "note": "월말 HSI signal long 행 수",
    })

    rows.append({
        "item": "monthly_signal_wide_rows",
        "value": len(monthly_wide),
        "status": "OK" if len(monthly_wide) > 0 else "CHECK",
        "note": "월말 HSI signal wide 행 수",
    })

    rows.append({
        "item": "ticker_count_in_long",
        "value": monthly_long[TICKER_COL].nunique(),
        "status": "OK" if monthly_long[TICKER_COL].nunique() == len(cfg.TICKERS) else "CHECK",
        "note": "long table 내 ETF 수",
    })

    rows.append({
        "item": "first_signal_month",
        "value": monthly_wide[YEAR_MONTH_COL].min(),
        "status": "OK",
        "note": "월말 신호 첫 월",
    })

    rows.append({
        "item": "last_signal_month",
        "value": monthly_wide[YEAR_MONTH_COL].max(),
        "status": "OK",
        "note": "월말 신호 마지막 월",
    })

    next_return_cols = [c for c in alignment_preview.columns if c.startswith("next_return_")]
    missing_return_cells = alignment_preview[next_return_cols].isna().sum().sum() if next_return_cols else 0

    rows.append({
        "item": "alignment_preview_rows",
        "value": len(alignment_preview),
        "status": "OK" if len(alignment_preview) > 0 else "CHECK",
        "note": "signal_month t → return_month t+1 정렬 행 수",
    })

    rows.append({
        "item": "alignment_missing_return_cells",
        "value": int(missing_return_cells),
        "status": "OK" if missing_return_cells <= len(next_return_cols) else "CHECK",
        "note": "마지막 월은 다음 달 수익률이 없어 정상 결측 가능",
    })

    event_cols_available = [c for c in EVENT_BALANCE_COLUMNS if c in monthly_long.columns]
    rows.append({
        "item": "event_balance_columns_merged",
        "value": ", ".join(event_cols_available) if event_cols_available else "N/A",
        "status": "OK" if event_cols_available else "INFO",
        "note": "02번 결과가 있으면 월말 신호표에 병합",
    })

    return pd.DataFrame(rows)


# ============================================================
# 10. Markdown 노트
# ============================================================

def build_note(
    column_map: pd.DataFrame,
    availability: pd.DataFrame,
    quality: pd.DataFrame,
) -> str:
    lines = []

    lines.append("# main_final 월말 HSI 신호 입력표 정리 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 단계는 일별 HSI 점수, direction, raw 3단계 signal, 원신호 입력표, 사건균형지표를 "
        "월말 기준으로 정리하여 다음 단계의 HSI 5상태 분류가 바로 사용할 수 있게 만드는 연결 단계이다."
    )
    lines.append("")
    lines.append("## 2. 시점 정합성")
    lines.append("")
    lines.append(f"- `{cfg.ALIGNMENT_RULE}`")
    lines.append("- 월말에 관측 가능한 HSI 신호를 다음 달 ETF 월간 수익률에 적용한다.")
    lines.append("")
    lines.append("## 3. 컬럼 역할")
    lines.append("")
    lines.append("| column | source | role |")
    lines.append("|---|---|---|")
    for _, row in column_map.iterrows():
        lines.append(f"| {row['column_name']} | {row['source']} | {row['role']} |")
    lines.append("")
    lines.append("## 4. 품질 점검 요약")
    lines.append("")
    lines.append("| item | value | status | note |")
    lines.append("|---|---:|---|---|")
    for _, row in quality.iterrows():
        lines.append(f"| {row['item']} | {row['value']} | {row['status']} | {row['note']} |")
    lines.append("")
    lines.append("## 5. 다음 단계")
    lines.append("")
    lines.append(
        "다음 단계인 `04_build_hsi_state5_baseline.py`에서는 "
        "`main_final_monthly_signal_inputs_long.csv`를 사용해 "
        "risk_relief, neutral_watch, conflict, risk_warning, accident_zone의 HSI 5상태를 생성한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 11. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("03_prepare_monthly_signal_inputs.py 실행 시작")
    print("=" * 80)

    print("[1] 최종 폴더 확인")
    cfg.ensure_final_directories()
    print("    OK")

    print("[2] 입력 파일 로드")
    signal_inputs = read_csv(INPUT_SIGNAL_INPUTS, "HSI 원신호 입력표")
    hsi_scores = read_csv(INPUT_HSI_SCORES, "HSI scaled scores")
    hsi_direction = read_csv(INPUT_HSI_DIRECTION, "HSI direction")
    hsi_raw3 = read_csv(INPUT_HSI_SIGNAL_RAW3, "HSI raw 3단계 signal")
    monthly_returns = read_csv(INPUT_MONTHLY_RETURNS, "월간 수익률 decimal")
    print("    OK")

    print("[3] 일별 wide 자료를 월말 기준으로 변환")
    monthly_scores = resample_month_end_wide(hsi_scores, date_label="score_date")
    monthly_direction = resample_month_end_wide(hsi_direction, date_label="direction_date")
    monthly_raw3 = resample_month_end_wide(hsi_raw3, date_label="raw3_signal_date")
    print(f"    monthly_scores shape    = {monthly_scores.shape}")
    print(f"    monthly_direction shape = {monthly_direction.shape}")
    print(f"    monthly_raw3 shape      = {monthly_raw3.shape}")

    print("[4] 월말 score long 생성")
    score_long = make_score_long(monthly_scores, monthly_direction, monthly_raw3)
    print(f"    score_long shape = {score_long.shape}")

    print("[5] 월말 원신호 signal_inputs 생성")
    monthly_raw_inputs = make_monthly_raw_signal_inputs(signal_inputs)
    print(f"    monthly_raw_inputs shape = {monthly_raw_inputs.shape}")

    print("[6] score long + raw signal_inputs 병합")
    raw_merge_cols = [
        YEAR_MONTH_COL,
        TICKER_COL,
        "raw_signal_date",
    ] + [c for c in RAW_SIGNAL_COLUMNS if c in monthly_raw_inputs.columns]

    monthly_long = score_long.merge(
        monthly_raw_inputs[raw_merge_cols],
        on=[YEAR_MONTH_COL, TICKER_COL],
        how="left",
    )

    print("[7] 사건균형지표 병합")
    monthly_long = maybe_merge_event_balance(monthly_long)

    print("[8] monthly wide 생성")
    monthly_wide = monthly_scores.merge(
        monthly_direction,
        on=YEAR_MONTH_COL,
        how="left",
    ).merge(
        monthly_raw3,
        on=YEAR_MONTH_COL,
        how="left",
    )

    monthly_wide = maybe_merge_event_balance(monthly_wide)

    print("[9] signal_month t → return_month t+1 alignment preview 생성")
    alignment_preview = make_alignment_preview(monthly_wide, monthly_returns)

    print("[10] 점검표 생성")
    column_map = build_column_map(monthly_long)
    availability = build_availability_check(monthly_long)
    quality = build_quality_check(
        monthly_scores=monthly_scores,
        monthly_long=monthly_long,
        monthly_wide=monthly_wide,
        alignment_preview=alignment_preview,
    )

    print("[11] CSV 저장")
    save_csv(monthly_scores, OUTPUT_MONTHLY_SCORES_WIDE)
    save_csv(monthly_long, OUTPUT_MONTHLY_INPUTS_LONG)
    save_csv(monthly_wide, OUTPUT_MONTHLY_INPUTS_WIDE)
    save_csv(alignment_preview, OUTPUT_ALIGNMENT_PREVIEW)

    save_csv(column_map, OUTPUT_COLUMN_MAP)
    save_csv(availability, OUTPUT_AVAILABILITY_CHECK)
    save_csv(quality, OUTPUT_QUALITY_CHECK)

    print(f"    저장: {OUTPUT_MONTHLY_SCORES_WIDE}")
    print(f"    저장: {OUTPUT_MONTHLY_INPUTS_LONG}")
    print(f"    저장: {OUTPUT_MONTHLY_INPUTS_WIDE}")
    print(f"    저장: {OUTPUT_ALIGNMENT_PREVIEW}")
    print(f"    저장: {OUTPUT_COLUMN_MAP}")
    print(f"    저장: {OUTPUT_AVAILABILITY_CHECK}")
    print(f"    저장: {OUTPUT_QUALITY_CHECK}")

    print("[12] Markdown 노트 저장")
    note = build_note(column_map, availability, quality)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[품질 점검]")
    print(quality.to_string(index=False))

    print("\n[월말 long 최근 9행]")
    preview_cols = [
        YEAR_MONTH_COL,
        TICKER_COL,
        "score_return",
        "score_ma_pos",
        "score_momentum",
        "score_vol",
        "score_rs",
        "hsi_direction",
        "raw3_signal",
        "event_balance_13612w",
        "event_intensity_13612w",
    ]
    preview_cols = [c for c in preview_cols if c in monthly_long.columns]
    print(monthly_long[preview_cols].tail(9).to_string(index=False))

    print("\n[alignment preview 최근 5행]")
    print(alignment_preview.tail(5).to_string(index=False))

    print("=" * 80)
    print("03_prepare_monthly_signal_inputs.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()