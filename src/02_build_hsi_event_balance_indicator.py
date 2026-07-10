from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
02_build_hsi_event_balance_indicator.py

목적
----
HSI 입력 신호의 과거 분포를 기준으로
20/80 분위수 기반 위험 사건 / 완화 사건을 정의하고,
날짜별 사건균형지표와 사건강도지표를 생성한다.

중요
----
이 지표는 외부 사건 달력이 아니다.
HSI 입력 신호 자체에서 위험 악화 또는 위험 완화 방향의 극단 신호가
최근 기간 동안 얼마나 반복되었는지 확인하는 내부 보조지표이다.

이 파일은 전략 비중을 직접 결정하지 않는다.
이후 08번 정합성 진단과 09번 보조 필터 백테스트에서 사용한다.

입력
----
data/processed/main_final_signal_inputs.csv

출력
----
data/processed/main_final_hsi_event_signal_flags.csv
data/processed/main_final_hsi_event_balance_daily.csv
data/processed/main_final_hsi_event_balance_monthly.csv

output/tables/main_final_hsi_event_balance_signal_map.csv
output/tables/main_final_hsi_event_balance_summary.csv

docs/main_final_hsi_event_balance_note.md
"""


# ============================================================
# 1. 입력 / 출력 경로
# ============================================================

INPUT_SIGNAL_PATH = cfg.PROCESSED_DIR / "main_final_signal_inputs.csv"

OUTPUT_SIGNAL_FLAGS_PATH = cfg.PROCESSED_DIR / "main_final_hsi_event_signal_flags.csv"
OUTPUT_DAILY_PATH = cfg.PROCESSED_DIR / "main_final_hsi_event_balance_daily.csv"
OUTPUT_MONTHLY_PATH = cfg.PROCESSED_DIR / "main_final_hsi_event_balance_monthly.csv"

OUTPUT_SIGNAL_MAP_PATH = cfg.TABLE_DIR / "main_final_hsi_event_balance_signal_map.csv"
OUTPUT_SUMMARY_PATH = cfg.TABLE_DIR / "main_final_hsi_event_balance_summary.csv"

OUTPUT_NOTE_PATH = cfg.DOCS_DIR / "main_final_hsi_event_balance_note.md"


# ============================================================
# 2. 설정값
# ============================================================

DATE_COL = "Date"
TICKER_COL = "ticker"

# signal_inputs에 존재하면 사용하는 신호 후보
SIGNAL_COLUMNS = [
    # 기본 6개
    "ret_1m",
    "ret_3m",
    "ma_gap",
    "momentum",
    "volatility",
    "relative_strength",

    # 확장 5개
    "ret_6m",
    "ret_12m",
    "drawdown",
    "shock_count",
    "defensive_rs",
]

# HSI 위험 방향 통일 규칙
# +1: 원신호가 클수록 위험 악화
# -1: 원신호가 클수록 위험 완화이므로 부호 반전
DIRECTION_SIGN = {
    "ret_1m": -1,
    "ret_3m": -1,
    "ma_gap": -1,
    "momentum": -1,
    "volatility": 1,
    "relative_strength": -1,

    "ret_6m": -1,
    "ret_12m": -1,
    "drawdown": -1,       # drawdown은 더 음수일수록 위험 → -1 곱하면 위험 방향 양수
    "shock_count": 1,     # 급락일 수가 많을수록 위험
    "defensive_rs": -1,
}

SIGNAL_FAMILY = {
    "ret_1m": "return",
    "ret_3m": "return",
    "ma_gap": "trend",
    "momentum": "trend",
    "volatility": "risk_damage",
    "relative_strength": "relative_strength",

    "ret_6m": "return",
    "ret_12m": "return",
    "drawdown": "risk_damage",
    "shock_count": "risk_damage",
    "defensive_rs": "relative_strength",
}

LOW_Q = 0.20
HIGH_Q = 0.80

ROLLING_WINDOW = 252
MIN_PERIODS = 60

TIME_WINDOWS = {
    "1m": 21,
    "3m": 63,
    "6m": 126,
    "12m": 252,
}

TIME_WEIGHTS = {
    "1m": 0.40,
    "3m": 0.30,
    "6m": 0.20,
    "12m": 0.10,
}

MONTH_END_RULE = "ME"


# ============================================================
# 3. 저장 유틸
# ============================================================

def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")


# ============================================================
# 4. 입력 로드
# ============================================================

def read_signal_inputs(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"입력 파일이 없습니다: {path}\n"
            "먼저 01_load_bundle_and_make_structure_tables.py를 실행하세요."
        )

    df = pd.read_csv(path, encoding="utf-8-sig")

    if "Ticker" in df.columns and TICKER_COL not in df.columns:
        df = df.rename(columns={"Ticker": TICKER_COL})

    required = [DATE_COL, TICKER_COL]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {missing}. 현재 컬럼: {df.columns.tolist()}")

    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df[TICKER_COL] = df[TICKER_COL].astype(str).str.zfill(6)

    df = df.dropna(subset=[DATE_COL])
    df = df.sort_values([TICKER_COL, DATE_COL]).reset_index(drop=True)

    return df


def get_available_signal_columns(df: pd.DataFrame) -> list[str]:
    available = [col for col in SIGNAL_COLUMNS if col in df.columns]

    if not available:
        raise ValueError(
            "사용 가능한 HSI 입력 신호 컬럼이 없습니다. "
            f"현재 컬럼: {df.columns.tolist()}"
        )

    return available


# ============================================================
# 5. 신호 방향 통일
# ============================================================

def make_signal_map(signal_cols: list[str]) -> pd.DataFrame:
    rows = []

    for col in signal_cols:
        sign = DIRECTION_SIGN[col]
        family = SIGNAL_FAMILY.get(col, "other")

        if sign == 1:
            rule = "raw_high_is_risk_worsening"
            note = "원신호가 클수록 위험 악화 방향으로 해석한다."
        else:
            rule = "raw_high_is_risk_relief_then_flip"
            note = "원신호가 클수록 위험 완화 방향이므로 -1을 곱해 위험 방향으로 통일한다."

        rows.append({
            "signal_name": col,
            "signal_family": family,
            "direction_sign": sign,
            "direction_rule": rule,
            "hsi_direction_interpretation": "positive = risk worsening, negative = risk relief",
            "note": note,
        })

    return pd.DataFrame(rows)


def convert_to_hsi_direction(df: pd.DataFrame, signal_cols: list[str]) -> pd.DataFrame:
    result = df.copy()

    for col in signal_cols:
        sign = DIRECTION_SIGN[col]
        result[col] = pd.to_numeric(result[col], errors="coerce")
        result[f"{col}_hsi_direction"] = result[col] * sign

    return result


# ============================================================
# 6. 20/80 분위수 사건 플래그
# ============================================================

def add_rolling_quantile_flags(df: pd.DataFrame, signal_cols: list[str]) -> pd.DataFrame:
    """
    ETF별·신호별 과거 rolling 분포의 q20/q80을 계산한다.

    중요:
    shift(1)을 적용해 현재 값을 분위수 기준 계산에 포함하지 않는다.
    """
    result = df.copy()

    for col in signal_cols:
        direction_col = f"{col}_hsi_direction"
        q20_col = f"{col}_q20"
        q80_col = f"{col}_q80"
        eligible_col = f"{col}_event_eligible"
        risk_col = f"{col}_risk_event"
        relief_col = f"{col}_relief_event"

        result[q20_col] = (
            result
            .groupby(TICKER_COL)[direction_col]
            .transform(
                lambda s: (
                    s.rolling(window=ROLLING_WINDOW, min_periods=MIN_PERIODS)
                    .quantile(LOW_Q)
                    .shift(1)
                )
            )
        )

        result[q80_col] = (
            result
            .groupby(TICKER_COL)[direction_col]
            .transform(
                lambda s: (
                    s.rolling(window=ROLLING_WINDOW, min_periods=MIN_PERIODS)
                    .quantile(HIGH_Q)
                    .shift(1)
                )
            )
        )

        result[eligible_col] = (
            result[direction_col].notna()
            & result[q20_col].notna()
            & result[q80_col].notna()
            & (result[q80_col] > result[q20_col])
        )

        result[risk_col] = np.where(
            result[eligible_col] & (result[direction_col] >= result[q80_col]),
            1,
            0,
        )

        result[relief_col] = np.where(
            result[eligible_col] & (result[direction_col] <= result[q20_col]),
            1,
            0,
        )

    return result


# ============================================================
# 7. 일별 사건균형지표
# ============================================================

def make_daily_event_balance(df: pd.DataFrame, signal_cols: list[str]) -> pd.DataFrame:
    eligible_cols = [f"{col}_event_eligible" for col in signal_cols]
    risk_cols = [f"{col}_risk_event" for col in signal_cols]
    relief_cols = [f"{col}_relief_event" for col in signal_cols]

    temp = df.copy()

    temp["eligible_signal_count"] = temp[eligible_cols].sum(axis=1)
    temp["risk_event_count"] = temp[risk_cols].sum(axis=1)
    temp["relief_event_count"] = temp[relief_cols].sum(axis=1)

    daily = (
        temp
        .groupby(DATE_COL)
        .agg(
            etf_count=(TICKER_COL, "nunique"),
            eligible_signal_count=("eligible_signal_count", "sum"),
            risk_event_count=("risk_event_count", "sum"),
            relief_event_count=("relief_event_count", "sum"),
        )
        .reset_index()
        .sort_values(DATE_COL)
    )

    daily["risk_event_ratio"] = np.where(
        daily["eligible_signal_count"] > 0,
        daily["risk_event_count"] / daily["eligible_signal_count"],
        np.nan,
    )

    daily["relief_event_ratio"] = np.where(
        daily["eligible_signal_count"] > 0,
        daily["relief_event_count"] / daily["eligible_signal_count"],
        np.nan,
    )

    daily["event_balance_raw"] = daily["risk_event_ratio"] - daily["relief_event_ratio"]
    daily["event_intensity_raw"] = daily["risk_event_ratio"] + daily["relief_event_ratio"]

    daily["event_balance_label"] = np.select(
        [
            daily["event_balance_raw"] > 0.05,
            daily["event_balance_raw"] < -0.05,
        ],
        [
            "risk_event_dominant",
            "relief_event_dominant",
        ],
        default="mixed_or_neutral",
    )

    daily["event_intensity_label"] = np.select(
        [
            daily["event_intensity_raw"] >= 0.40,
            daily["event_intensity_raw"] >= 0.20,
        ],
        [
            "high_intensity",
            "medium_intensity",
        ],
        default="low_intensity",
    )

    return daily.reset_index(drop=True)


# ============================================================
# 8. 이동평균 및 13612W
# ============================================================

def add_moving_average_features(daily: pd.DataFrame) -> pd.DataFrame:
    result = daily.copy()

    for label, window in TIME_WINDOWS.items():
        min_periods = max(5, window // 3)

        result[f"event_balance_ma_{label}"] = (
            result["event_balance_raw"]
            .rolling(window=window, min_periods=min_periods)
            .mean()
        )

        result[f"event_intensity_ma_{label}"] = (
            result["event_intensity_raw"]
            .rolling(window=window, min_periods=min_periods)
            .mean()
        )

    return result


def add_13612w_features(daily: pd.DataFrame) -> pd.DataFrame:
    result = daily.copy()

    result["event_balance_13612w"] = 0.0
    result["event_intensity_13612w"] = 0.0

    for label, weight in TIME_WEIGHTS.items():
        result["event_balance_13612w"] += weight * result[f"event_balance_ma_{label}"]
        result["event_intensity_13612w"] += weight * result[f"event_intensity_ma_{label}"]

    result["event_balance_13612w_label"] = np.select(
        [
            result["event_balance_13612w"] > 0.05,
            result["event_balance_13612w"] < -0.05,
        ],
        [
            "risk_accumulation",
            "relief_accumulation",
        ],
        default="mixed_or_neutral",
    )

    result["event_intensity_13612w_label"] = np.select(
        [
            result["event_intensity_13612w"] >= 0.40,
            result["event_intensity_13612w"] >= 0.20,
        ],
        [
            "high_accumulated_intensity",
            "medium_accumulated_intensity",
        ],
        default="low_accumulated_intensity",
    )

    return result


# ============================================================
# 9. 월말 사건균형지표
# ============================================================

def make_monthly_event_balance(daily: pd.DataFrame) -> pd.DataFrame:
    temp = daily.copy()
    temp[DATE_COL] = pd.to_datetime(temp[DATE_COL])
    temp = temp.set_index(DATE_COL).sort_index()

    try:
        monthly = temp.resample(MONTH_END_RULE).last()
    except ValueError:
        monthly = temp.resample("M").last()

    monthly = monthly.reset_index()
    monthly["year_month"] = monthly[DATE_COL].dt.to_period("M").astype(str)
    monthly[DATE_COL] = monthly[DATE_COL].dt.strftime("%Y-%m-%d")

    # year_month를 앞쪽으로 이동
    cols = ["year_month", DATE_COL] + [c for c in monthly.columns if c not in ["year_month", DATE_COL]]
    monthly = monthly[cols]

    return monthly


# ============================================================
# 10. 요약표 / 노트
# ============================================================

def build_summary(
    signal_cols: list[str],
    flag_df: pd.DataFrame,
    daily: pd.DataFrame,
    monthly: pd.DataFrame,
) -> pd.DataFrame:
    valid_daily = daily.dropna(subset=["event_balance_13612w", "event_intensity_13612w"])
    valid_monthly = monthly.dropna(subset=["event_balance_13612w", "event_intensity_13612w"])

    rows = [
        {
            "item": "input_file",
            "value": str(INPUT_SIGNAL_PATH),
            "status": "OK",
            "note": "01번에서 생성한 HSI 원신호 입력표",
        },
        {
            "item": "signal_columns",
            "value": ", ".join(signal_cols),
            "status": "OK",
            "note": "사건균형지표 계산에 사용한 신호",
        },
        {
            "item": "quantile_rule",
            "value": f"q20={LOW_Q}, q80={HIGH_Q}",
            "status": "OK",
            "note": "q80 이상 위험 사건, q20 이하 완화 사건",
        },
        {
            "item": "rolling_window",
            "value": str(ROLLING_WINDOW),
            "status": "OK",
            "note": "과거 분위수 계산 기준 길이",
        },
        {
            "item": "min_periods",
            "value": str(MIN_PERIODS),
            "status": "OK",
            "note": "분위수 계산 최소 관측치",
        },
        {
            "item": "time_weights",
            "value": str(TIME_WEIGHTS),
            "status": "OK",
            "note": "13612W 시간가중 구조",
        },
        {
            "item": "flag_rows",
            "value": str(len(flag_df)),
            "status": "OK",
            "note": "ETF·날짜별 사건 플래그 행 수",
        },
        {
            "item": "daily_rows",
            "value": str(len(daily)),
            "status": "OK",
            "note": "일별 사건균형지표 행 수",
        },
        {
            "item": "monthly_rows",
            "value": str(len(monthly)),
            "status": "OK",
            "note": "월말 사건균형지표 행 수",
        },
        {
            "item": "first_valid_daily_13612w",
            "value": str(valid_daily[DATE_COL].min()) if not valid_daily.empty else "N/A",
            "status": "OK" if not valid_daily.empty else "CHECK",
            "note": "13612W 지표가 처음 유효해진 일자",
        },
        {
            "item": "first_valid_monthly_13612w",
            "value": str(valid_monthly["year_month"].min()) if not valid_monthly.empty else "N/A",
            "status": "OK" if not valid_monthly.empty else "CHECK",
            "note": "13612W 월말 지표가 처음 유효해진 월",
        },
        {
            "item": "event_balance_mean",
            "value": str(round(valid_monthly["event_balance_13612w"].mean(), 6)) if not valid_monthly.empty else "N/A",
            "status": "OK" if not valid_monthly.empty else "CHECK",
            "note": "월말 사건균형 13612W 평균",
        },
        {
            "item": "event_intensity_mean",
            "value": str(round(valid_monthly["event_intensity_13612w"].mean(), 6)) if not valid_monthly.empty else "N/A",
            "status": "OK" if not valid_monthly.empty else "CHECK",
            "note": "월말 사건강도 13612W 평균",
        },
    ]

    return pd.DataFrame(rows)


def build_note(summary: pd.DataFrame, signal_map: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_final HSI 사건균형·위험누적지표 생성 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "사건균형지표는 외부 사건 달력이 아니라, HSI 입력 신호 자체에서 위험 악화 또는 위험 완화 방향의 "
        "극단 신호가 최근 기간 동안 얼마나 반복되었는지 확인하는 내부 보조지표이다."
    )
    lines.append("")
    lines.append("## 2. 계산 방식")
    lines.append("")
    lines.append("1. 각 원신호를 HSI 위험 방향 기준으로 통일한다.")
    lines.append("2. ETF별·신호별 과거 rolling 분포에서 20분위수와 80분위수를 계산한다.")
    lines.append("3. 현재 값이 80분위수 이상이면 위험 사건, 20분위수 이하이면 완화 사건으로 표시한다.")
    lines.append("4. 날짜별 위험 사건 비율과 완화 사건 비율을 계산한다.")
    lines.append("5. 사건균형과 사건강도를 계산한다.")
    lines.append("")
    lines.append("```text")
    lines.append("event_balance = risk_event_ratio - relief_event_ratio")
    lines.append("event_intensity = risk_event_ratio + relief_event_ratio")
    lines.append("```")
    lines.append("")
    lines.append("## 3. 해석")
    lines.append("")
    lines.append("- event_balance > 0: 위험 사건 우세")
    lines.append("- event_balance < 0: 완화 사건 우세")
    lines.append("- event_intensity 높음: 방향과 무관하게 극단 신호가 많음")
    lines.append("- event_balance ≈ 0 이고 event_intensity 높음: 위험·완화 신호가 충돌하는 혼합 국면 가능성")
    lines.append("")
    lines.append("## 4. 사용 신호")
    lines.append("")
    lines.append("| signal | family | direction_sign | note |")
    lines.append("|---|---|---:|---|")
    for _, row in signal_map.iterrows():
        lines.append(
            f"| {row['signal_name']} | {row['signal_family']} | "
            f"{row['direction_sign']} | {row['note']} |"
        )
    lines.append("")
    lines.append("## 5. 생성 결과 요약")
    lines.append("")
    lines.append("| item | value | status | note |")
    lines.append("|---|---|---|---|")
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['item']} | {row['value']} | {row['status']} | {row['note']} |"
        )
    lines.append("")
    lines.append("## 6. 다음 단계")
    lines.append("")
    lines.append(
        "다음 단계에서는 월말 사건균형지표를 HSI 5상태표와 대조하여 "
        "risk_warning, accident_zone, conflict 상태에서 사건균형과 사건강도가 해석상 정합적인지 확인한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 11. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("02_build_hsi_event_balance_indicator.py 실행 시작")
    print("=" * 80)

    print("[1] 최종 폴더 확인")
    cfg.ensure_final_directories()
    print("    OK")

    print("[2] HSI 원신호 입력표 로드")
    signal_df = read_signal_inputs(INPUT_SIGNAL_PATH)
    print(f"    signal_inputs shape = {signal_df.shape}")

    print("[3] 사용 가능한 신호 컬럼 확인")
    signal_cols = get_available_signal_columns(signal_df)
    print(f"    사용 신호 {len(signal_cols)}개: {signal_cols}")

    print("[4] 신호 방향 정의표 생성")
    signal_map = make_signal_map(signal_cols)
    save_csv(signal_map, OUTPUT_SIGNAL_MAP_PATH)
    print(f"    저장: {OUTPUT_SIGNAL_MAP_PATH}")

    print("[5] HSI 위험 방향 기준으로 부호 통일")
    direction_df = convert_to_hsi_direction(signal_df, signal_cols)
    print("    OK")

    print("[6] 20/80 rolling 분위수 기반 사건 플래그 생성")
    flag_df = add_rolling_quantile_flags(direction_df, signal_cols)
    save_csv(flag_df, OUTPUT_SIGNAL_FLAGS_PATH)
    print(f"    저장: {OUTPUT_SIGNAL_FLAGS_PATH}")

    print("[7] 일별 사건균형지표 생성")
    daily = make_daily_event_balance(flag_df, signal_cols)
    daily = add_moving_average_features(daily)
    daily = add_13612w_features(daily)
    save_csv(daily, OUTPUT_DAILY_PATH)
    print(f"    저장: {OUTPUT_DAILY_PATH}")

    print("[8] 월말 사건균형지표 생성")
    monthly = make_monthly_event_balance(daily)
    save_csv(monthly, OUTPUT_MONTHLY_PATH)
    print(f"    저장: {OUTPUT_MONTHLY_PATH}")

    print("[9] 요약표 생성")
    summary = build_summary(signal_cols, flag_df, daily, monthly)
    save_csv(summary, OUTPUT_SUMMARY_PATH)
    print(f"    저장: {OUTPUT_SUMMARY_PATH}")

    print("[10] Markdown 노트 저장")
    note = build_note(summary, signal_map)
    OUTPUT_NOTE_PATH.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE_PATH}")

    print("\n[요약]")
    print(summary.to_string(index=False))

    print("\n[월말 사건균형지표 최근 12개월]")
    preview_cols = [
        "year_month",
        "event_balance_raw",
        "event_intensity_raw",
        "event_balance_13612w",
        "event_intensity_13612w",
        "event_balance_13612w_label",
        "event_intensity_13612w_label",
    ]
    available_preview_cols = [c for c in preview_cols if c in monthly.columns]
    print(monthly[available_preview_cols].tail(12).to_string(index=False))

    print("=" * 80)
    print("02_build_hsi_event_balance_indicator.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()