from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd


"""
12_build_macro_companion_layer.py

목적
----
금리, 환율, GDP 성장률을 이용해 HSI baseline을 보조적으로 해석하는
macro companion layer를 만든다.

중요
----
이 파일은 HSI 상태분류와 baseline 백테스트를 직접 수정하지 않는다.
즉, main_final baseline의 직접 입력 신호가 아니라,
가격 기반 HSI 상태가 어떤 매크로 환경에서 발생했는지 확인하는
해석 보조 장치이다.

사용 자료
--------
data/raw/2014년 이후 금리 자료.csv
data/raw/2014년 이후 금리 자료(RP).csv
data/raw/2014년 이후 환율 데이터.csv
data/raw/2. 2014년 이후 매크로 데이터(GDP 성장률).csv

산출물
------
data/processed/main_final_macro_companion_features_monthly.csv
output/tables/main_final_macro_companion_quality_check.csv
output/tables/main_final_macro_companion_signal_summary.csv
docs/main_final_macro_companion_note.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
DOCS_DIR = PROJECT_ROOT / "docs"

for d in [RAW_DIR, PROCESSED_DIR, TABLE_DIR, DOCS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


INPUT_RATE = RAW_DIR / "2014년 이후 금리 자료.csv"
INPUT_RP = RAW_DIR / "2014년 이후 금리 자료(RP).csv"
INPUT_FX = RAW_DIR / "2014년 이후 환율 데이터.csv"
INPUT_GDP = RAW_DIR / "2. 2014년 이후 매크로 데이터(GDP 성장률).csv"

INPUT_FINAL_RETURN = PROCESSED_DIR / "main_final_monthly_return_decimal.csv"

OUTPUT_FEATURES = PROCESSED_DIR / "main_final_macro_companion_features_monthly.csv"
OUTPUT_QUALITY = TABLE_DIR / "main_final_macro_companion_quality_check.csv"
OUTPUT_SIGNAL_SUMMARY = TABLE_DIR / "main_final_macro_companion_signal_summary.csv"
OUTPUT_NOTE = DOCS_DIR / "main_final_macro_companion_note.md"


# ============================================================
# 1. 설정값
# ============================================================

# GDP 성장률은 최종적으로 decimal 단위로 사용한다.
# 예: 0.02 = 2%
GDP_STABLE_LOW = 0.02
GDP_STABLE_HIGH = 0.03

DEPARTURE_THRESHOLD = 0.60
EPS = 1e-9


# ============================================================
# 2. 공통 유틸
# ============================================================

def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"필수 입력 파일을 찾을 수 없습니다: {path}")


def read_csv_korean(path: Path) -> pd.DataFrame:
    require_file(path)

    encodings = ["utf-8-sig", "cp949", "euc-kr", "utf-8"]
    last_error = None

    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_error = e

    raise RuntimeError(f"CSV 파일을 읽지 못했습니다: {path}\n마지막 오류: {last_error}")


def clean_column_name(col) -> str:
    return str(col).strip().replace("\n", " ").replace("\r", " ")


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [clean_column_name(c) for c in df.columns]
    df = df.dropna(how="all")
    return df


def to_numeric_clean(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace({"": np.nan, "nan": np.nan, "NaN": np.nan, "-": np.nan})
        .pipe(pd.to_numeric, errors="coerce")
    )


def parse_date_value(x):
    if pd.isna(x):
        return pd.NaT

    text = str(x).strip()

    if text.isdigit() and len(text) == 8:
        return pd.to_datetime(text, format="%Y%m%d", errors="coerce")

    if text.isdigit() and len(text) == 6:
        return pd.to_datetime(text + "01", format="%Y%m%d", errors="coerce")

    text = text.replace(".", "-").replace("/", "-")
    return pd.to_datetime(text, errors="coerce")


def find_date_column(df: pd.DataFrame) -> str:
    for candidate in ["date", "Date", "DATE", "날짜", "일자", "시점", "연월", "Unnamed: 0"]:
        if candidate in df.columns:
            return candidate

    return df.columns[0]


def resample_month_end_last(temp: pd.DataFrame) -> pd.DataFrame:
    """
    pandas 버전 차이를 피하기 위한 월말 리샘플링 함수.
    최신 pandas에서는 ME가 권장되지만, 일부 환경에서는 M만 가능한 경우도 있다.
    """
    try:
        return temp.resample("ME").last()
    except Exception:
        return temp.resample("M").last()


def month_end_last(df: pd.DataFrame, value_cols: list[str], date_col: str | None = None) -> pd.DataFrame:
    """
    일별 또는 월중 자료를 월말 기준 자료로 변환한다.
    """
    df = clean_dataframe(df)

    if date_col is None:
        date_col = find_date_column(df)

    if date_col not in df.columns:
        raise KeyError(f"날짜 컬럼을 찾을 수 없습니다: {date_col}")

    missing_cols = [c for c in value_cols if c not in df.columns]
    if missing_cols:
        raise KeyError(f"월말 변환에 필요한 컬럼이 없습니다: {missing_cols}")

    temp = df[[date_col] + value_cols].copy()
    temp[date_col] = temp[date_col].apply(parse_date_value)
    temp = temp.dropna(subset=[date_col])
    temp = temp.set_index(date_col).sort_index()

    monthly = resample_month_end_last(temp)

    # Period 변환은 M 사용
    monthly.index = monthly.index.to_period("M").astype(str)
    monthly.index.name = "year_month"

    return monthly.reset_index()


def rolling_z_no_lookahead(s: pd.Series, window: int = 36, min_periods: int = 12) -> pd.Series:
    """
    현재값을 평가할 때 과거 window만 사용하도록 평균과 표준편차를 1개월 shift한다.
    """
    s = s.astype(float)

    mean = s.rolling(window=window, min_periods=min_periods).mean().shift(1)
    std = s.rolling(window=window, min_periods=min_periods).std(ddof=1).shift(1)

    z = (s - mean) / std.replace(0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan).fillna(0.0)


# ============================================================
# 3. 금리 처리
# ============================================================

def build_rate_monthly() -> pd.DataFrame:
    rate_df = clean_dataframe(read_csv_korean(INPUT_RATE))
    rp_df = clean_dataframe(read_csv_korean(INPUT_RP))

    required_rate_cols = {
        "시장금리:콜(1일물)(%)": "call_rate",
        "시장금리:CD유통수익률(91)(%)": "cd91_rate",
        "시장금리:회사채(무보증3년AA-)(%)": "corp_aa3y_rate",
        "시장금리:국고1년(%)": "gov1y_rate",
        "시장금리:국고3년(국채관리기금채3년)(%)": "gov3y_rate",
        "시장금리:국고10년(%)": "gov10y_rate",
        "시장금리:회사채(무보증3년BBB-)(%)": "corp_bbb3y_rate",
        "시장금리:CP(91일)(%)": "cp91_rate",
    }

    for raw_col, new_col in required_rate_cols.items():
        if raw_col not in rate_df.columns:
            raise KeyError(f"시장금리 파일에 필요한 컬럼이 없습니다: {raw_col}")

        rate_df[new_col] = to_numeric_clean(rate_df[raw_col])

    if "RP금리" not in rp_df.columns:
        raise KeyError("RP 금리 파일에 'RP금리' 컬럼이 없습니다.")

    rp_df["rp_rate"] = to_numeric_clean(rp_df["RP금리"])

    rate_value_cols = list(required_rate_cols.values())

    rate_monthly = month_end_last(
        rate_df,
        value_cols=rate_value_cols,
    )

    rp_monthly = month_end_last(
        rp_df,
        value_cols=["rp_rate"],
    )

    out = pd.merge(
        rate_monthly,
        rp_monthly,
        on="year_month",
        how="outer",
    ).sort_values("year_month").reset_index(drop=True)

    # 대표 금리는 국고3년을 기본값으로 사용한다.
    out["rate_level"] = out["gov3y_rate"]
    out["rate_source"] = "gov3y_rate"

    # 금리 변화폭: percentage point 변화
    out["rate_change_1m"] = out["rate_level"].diff()
    out["rate_up_flag"] = (out["rate_change_1m"] > 0).astype(int)
    out["rate_z"] = rolling_z_no_lookahead(out["rate_change_1m"])

    # 보조 금리 스프레드
    out["term_spread_10y_1y"] = out["gov10y_rate"] - out["gov1y_rate"]
    out["credit_spread_aa_gov3y"] = out["corp_aa3y_rate"] - out["gov3y_rate"]
    out["cp_cd_spread"] = out["cp91_rate"] - out["cd91_rate"]

    return out


# ============================================================
# 4. 환율 처리
# ============================================================

def build_fx_monthly() -> pd.DataFrame:
    fx_df = clean_dataframe(read_csv_korean(INPUT_FX))

    required_fx_cols = {
        "시장평균_미국(달러)(통화대원)": "usdkrw",
        "시장평균_일본(100엔)((100)통화)": "jpykrw_100",
        "시장평균_EU(유로)(통화대원)": "eurkrw",
    }

    for raw_col, new_col in required_fx_cols.items():
        if raw_col not in fx_df.columns:
            raise KeyError(f"환율 파일에 필요한 컬럼이 없습니다: {raw_col}")

        fx_df[new_col] = to_numeric_clean(fx_df[raw_col])

    fx_monthly = month_end_last(
        fx_df,
        value_cols=list(required_fx_cols.values()),
    )

    fx_monthly["usdkrw_return_1m"] = fx_monthly["usdkrw"].pct_change()
    fx_monthly["usdkrw_change_1m"] = fx_monthly["usdkrw"].diff()

    # 원/달러 상승 = 원화 약세 방향
    fx_monthly["fx_up_flag"] = (fx_monthly["usdkrw_return_1m"] > 0).astype(int)
    fx_monthly["fx_z"] = rolling_z_no_lookahead(fx_monthly["usdkrw_return_1m"])

    return fx_monthly


# ============================================================
# 5. GDP 처리
# ============================================================

def build_gdp_monthly() -> pd.DataFrame:
    gdp_df = clean_dataframe(read_csv_korean(INPUT_GDP))

    if "국내총생산(시장가격, GDP)(십억원)" not in gdp_df.columns:
        raise KeyError("GDP 파일에 '국내총생산(시장가격, GDP)(십억원)' 컬럼이 없습니다.")

    if "성장률" not in gdp_df.columns:
        raise KeyError("GDP 파일에 '성장률' 컬럼이 없습니다.")

    date_col = find_date_column(gdp_df)

    gdp_df["date"] = gdp_df[date_col].apply(parse_date_value)
    gdp_df["gdp_level_billion_krw"] = to_numeric_clean(
        gdp_df["국내총생산(시장가격, GDP)(십억원)"]
    )

    gdp_growth_raw = to_numeric_clean(gdp_df["성장률"])

    # 성장률 단위 자동 판별:
    # 0.02 형태면 decimal, 2.0 형태면 percent로 보고 /100
    max_abs_growth = gdp_growth_raw.abs().max(skipna=True)

    if max_abs_growth > 1:
        gdp_df["gdp_growth_decimal"] = gdp_growth_raw / 100.0
        gdp_unit = "percent_to_decimal"
    else:
        gdp_df["gdp_growth_decimal"] = gdp_growth_raw
        gdp_unit = "decimal_as_is"

    gdp_df = gdp_df.dropna(subset=["date"]).copy()
    gdp_df = gdp_df.set_index("date").sort_index()

    temp = gdp_df[["gdp_level_billion_krw", "gdp_growth_decimal"]].copy()

    monthly = resample_month_end_last(temp).ffill()
    monthly.index = monthly.index.to_period("M").astype(str)
    monthly.index.name = "year_month"

    out = monthly.reset_index()

    # 실제 발표시차를 엄밀히 반영하지 못하므로 우선 1개월 lag 적용
    out["gdp_growth_decimal_lagged"] = out["gdp_growth_decimal"].shift(1)
    out["gdp_growth_pct_lagged"] = out["gdp_growth_decimal_lagged"] * 100.0
    out["gdp_unit_detected"] = gdp_unit

    conditions = [
        out["gdp_growth_decimal_lagged"] < 0,
        (out["gdp_growth_decimal_lagged"] >= 0)
        & (out["gdp_growth_decimal_lagged"] < GDP_STABLE_LOW),
        (out["gdp_growth_decimal_lagged"] >= GDP_STABLE_LOW)
        & (out["gdp_growth_decimal_lagged"] <= GDP_STABLE_HIGH),
        out["gdp_growth_decimal_lagged"] > GDP_STABLE_HIGH,
    ]

    choices = [
        "contraction_below_0",
        "slowdown_0_to_2",
        "stable_2_to_3",
        "strong_above_3",
    ]

    out["gdp_growth_band"] = np.select(conditions, choices, default="unknown")
    out["gdp_below_2_flag"] = (out["gdp_growth_decimal_lagged"] < GDP_STABLE_LOW).astype(int)
    out["gdp_stable_2_3_flag"] = (
        (out["gdp_growth_decimal_lagged"] >= GDP_STABLE_LOW)
        & (out["gdp_growth_decimal_lagged"] <= GDP_STABLE_HIGH)
    ).astype(int)

    return out


# ============================================================
# 6. 매크로 보조 신호 계산
# ============================================================

def build_macro_companion_features(
    rate_monthly: pd.DataFrame,
    fx_monthly: pd.DataFrame,
    gdp_monthly: pd.DataFrame,
) -> pd.DataFrame:
    df = pd.merge(rate_monthly, fx_monthly, on="year_month", how="outer")
    df = pd.merge(df, gdp_monthly, on="year_month", how="outer")
    df = df.sort_values("year_month").reset_index(drop=True)

    numerator = (df["rate_z"] + df["fx_z"]).abs()
    denominator = df["rate_z"].abs() + df["fx_z"].abs() + EPS

    df["rate_fx_departure"] = (numerator / denominator).clip(0, 1)

    df["rate_fx_risk_departure_flag"] = (
        (df["rate_change_1m"] > 0)
        & (df["usdkrw_return_1m"] > 0)
        & (df["rate_fx_departure"] >= DEPARTURE_THRESHOLD)
    ).astype(int)

    df["rate_fx_relief_departure_flag"] = (
        (df["rate_change_1m"] < 0)
        & (df["usdkrw_return_1m"] < 0)
        & (df["rate_fx_departure"] >= DEPARTURE_THRESHOLD)
    ).astype(int)

    df["policy_growth_pressure_flag"] = (
        (df["rate_up_flag"] == 1)
        & (df["gdp_below_2_flag"] == 1)
    ).astype(int)

    df["macro_defense_addon"] = 0.0

    # 금리 상승 + 원/달러 상승 + 이탈률 높음
    df.loc[df["rate_fx_risk_departure_flag"] == 1, "macro_defense_addon"] += 0.010

    # 금리 상승 + GDP 성장률 2% 미만
    df.loc[df["policy_growth_pressure_flag"] == 1, "macro_defense_addon"] += 0.010

    # 원/달러 상승 + GDP 성장률 2% 미만
    df.loc[
        (df["fx_up_flag"] == 1) & (df["gdp_below_2_flag"] == 1),
        "macro_defense_addon",
    ] += 0.005

    df["macro_defense_addon"] = df["macro_defense_addon"].clip(0, 0.030)

    df["macro_relief_addon"] = 0.0
    df.loc[
        (df["rate_fx_relief_departure_flag"] == 1)
        & (df["gdp_stable_2_3_flag"] == 1),
        "macro_relief_addon",
    ] = 0.005

    conditions = [
        (df["rate_fx_risk_departure_flag"] == 1)
        & (df["policy_growth_pressure_flag"] == 1),
        df["policy_growth_pressure_flag"] == 1,
        df["rate_fx_risk_departure_flag"] == 1,
        df["rate_fx_relief_departure_flag"] == 1,
    ]

    choices = [
        "risk_departure_plus_growth_pressure",
        "policy_growth_pressure",
        "rate_fx_risk_departure",
        "rate_fx_relief_departure",
    ]

    df["macro_companion_regime"] = np.select(conditions, choices, default="neutral")

    return df


# ============================================================
# 7. main_final 월 기준 정렬
# ============================================================

def align_to_main_final_months(macro_features: pd.DataFrame) -> pd.DataFrame:
    if not INPUT_FINAL_RETURN.exists():
        print(f"[WARN] main_final 수익률 파일이 없어 전체 macro 월을 저장합니다: {INPUT_FINAL_RETURN}")
        return macro_features

    final_return = pd.read_csv(INPUT_FINAL_RETURN)

    if "year_month" not in final_return.columns:
        raise KeyError("main_final_monthly_return_decimal.csv에 year_month 컬럼이 없습니다.")

    months = final_return[["year_month"]].copy()
    months["year_month"] = months["year_month"].astype(str)

    out = pd.merge(months, macro_features, on="year_month", how="left")
    return out


def add_availability_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    main_final 월 기준으로 정렬한 뒤 생기는 NaN의 의미를 명시한다.

    macro_data_available:
        금리, 환율, 금리-환율 이탈률이 모두 있으면 1

    gdp_data_available:
        lagged GDP 성장률이 있으면 1

    macro_companion_regime_filled:
        매크로 자료가 아예 없는 구간은 macro_data_unavailable로 표시
    """
    df = df.copy()

    macro_required_cols = [
        "rate_level",
        "usdkrw",
        "rate_fx_departure",
    ]

    if all(col in df.columns for col in macro_required_cols):
        df["macro_data_available"] = (
            df[macro_required_cols].notna().all(axis=1).astype(int)
        )
    else:
        df["macro_data_available"] = 0

    if "gdp_growth_decimal_lagged" in df.columns:
        df["gdp_data_available"] = (
            df["gdp_growth_decimal_lagged"].notna().astype(int)
        )
    else:
        df["gdp_data_available"] = 0

    if "macro_companion_regime" in df.columns:
        df["macro_companion_regime_filled"] = df["macro_companion_regime"].copy()
    else:
        df["macro_companion_regime_filled"] = np.nan

    # 매크로 자료 자체가 없는 구간: 판정 제외
    df.loc[
        df["macro_data_available"] == 0,
        "macro_companion_regime_filled",
    ] = "macro_data_unavailable"

    # 금리·환율 자료는 있는데 regime만 비어 있으면 중립으로 처리
    df.loc[
        (df["macro_data_available"] == 1)
        & (df["macro_companion_regime_filled"].isna()),
        "macro_companion_regime_filled",
    ] = "neutral"

    # GDP만 없는 경우는 별도 상태 컬럼으로 남긴다.
    df["gdp_availability_status"] = np.where(
        df["gdp_data_available"] == 1,
        "gdp_available",
        "gdp_unavailable",
    )

    return df


# ============================================================
# 8. 점검표와 노트
# ============================================================

def make_quality_check(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    rows.append({
        "check_item": "row_count",
        "result": len(df),
        "status": "OK" if len(df) > 0 else "CHECK",
        "note": "main_final 월 기준으로 정렬된 macro companion row 수",
    })

    if len(df) > 0:
        rows.append({
            "check_item": "date_range",
            "result": f"{df['year_month'].min()} ~ {df['year_month'].max()}",
            "status": "OK",
            "note": "macro companion feature coverage",
        })

    key_cols = [
        "rate_level",
        "rate_change_1m",
        "usdkrw",
        "usdkrw_return_1m",
        "gdp_growth_decimal_lagged",
        "gdp_growth_pct_lagged",
        "rate_fx_departure",
        "macro_defense_addon",
    ]

    for col in key_cols:
        if col not in df.columns:
            rows.append({
                "check_item": f"missing_column_{col}",
                "result": "not_found",
                "status": "CHECK",
                "note": "필수 보조지표 컬럼이 없습니다.",
            })
            continue

        missing = int(df[col].isna().sum())
        rows.append({
            "check_item": f"missing_count_{col}",
            "result": missing,
            "status": "OK" if missing < len(df) else "CHECK",
            "note": f"{col} 결측치 수",
        })

    if "rate_fx_departure" in df.columns:
        min_departure = df["rate_fx_departure"].min(skipna=True)
        max_departure = df["rate_fx_departure"].max(skipna=True)

        rows.append({
            "check_item": "rate_fx_departure_range",
            "result": f"{min_departure:.4f} ~ {max_departure:.4f}",
            "status": "OK" if min_departure >= 0 and max_departure <= 1 else "CHECK",
            "note": "이탈률은 0~1 범위여야 합니다.",
        })

    if "macro_defense_addon" in df.columns:
        max_addon = df["macro_defense_addon"].max(skipna=True)

        rows.append({
            "check_item": "macro_defense_addon_max",
            "result": f"{max_addon:.4f}",
            "status": "OK" if max_addon <= 0.03 else "CHECK",
            "note": "방어 보조값은 최대 0.03으로 제한합니다.",
        })

    return pd.DataFrame(rows)


def make_signal_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    flag_cols = [
        "macro_data_available",
        "gdp_data_available",
        "rate_up_flag",
        "fx_up_flag",
        "gdp_below_2_flag",
        "gdp_stable_2_3_flag",
        "rate_fx_risk_departure_flag",
        "rate_fx_relief_departure_flag",
        "policy_growth_pressure_flag",
    ]

    for col in flag_cols:
        if col in df.columns:
            rows.append({
                "signal": col,
                "count_1": int(df[col].fillna(0).sum()),
                "ratio_1": float(df[col].fillna(0).mean()),
            })

    regime_col = (
        "macro_companion_regime_filled"
        if "macro_companion_regime_filled" in df.columns
        else "macro_companion_regime"
    )

    if regime_col in df.columns:
        regime_counts = df[regime_col].value_counts(dropna=False)

        for regime, count in regime_counts.items():
            rows.append({
                "signal": f"regime_{regime}",
                "count_1": int(count),
                "ratio_1": float(count / len(df)) if len(df) else np.nan,
            })

    return pd.DataFrame(rows)


def make_note() -> str:
    lines = []

    lines.append("# main_final macro companion layer note")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "본 파일은 금리, 환율, GDP 성장률을 이용하여 HSI 상태를 보조적으로 해석하기 위한 "
        "macro companion layer를 생성한다. 이 지표는 baseline HSI 상태분류의 직접 입력값이 아니라, "
        "가격 기반 HSI 상태가 어떤 매크로 환경에서 발생했는지 확인하기 위한 해석 보조 장치이다."
    )
    lines.append("")
    lines.append("## 2. 계산 고리")
    lines.append("")
    lines.append("- 일별 금리 자료를 월말 금리로 변환하고, 국고3년 금리의 월간 변화폭을 계산한다.")
    lines.append("- 일별 환율 자료를 월말 원/달러 환율로 변환하고, 원/달러 월간 변화율을 계산한다.")
    lines.append("- 금리 변화와 환율 변화는 각각 과거 rolling 기준으로 표준화한다.")
    lines.append("- `rate_fx_departure`는 금리와 환율이 기대되는 반대 방향 관계에서 얼마나 벗어났는지를 나타낸다.")
    lines.append("- GDP 성장률은 월별로 확장한 뒤 1개월 lag를 적용하여 성장 구간을 판단한다.")
    lines.append("")
    lines.append("## 3. 주요 규칙")
    lines.append("")
    lines.append("- 금리 상승과 원/달러 상승이 동시에 나타나고 이탈률이 높으면 위험형 이탈로 본다.")
    lines.append("- 금리 하락과 원/달러 하락이 동시에 나타나고 이탈률이 높으면 완화형 이탈로 본다.")
    lines.append("- 금리 상승과 GDP 성장률 2% 미만이 함께 나타나면 정책 성장 압력으로 본다.")
    lines.append("- 방어 보조값은 `macro_defense_addon`으로 저장하되, 최대 0.03으로 제한한다.")
    lines.append("")
    lines.append("## 4. 해석 주의")
    lines.append("")
    lines.append(
        "GDP 성장률 2~3% 구간은 중앙은행의 공식 목표가 아니라, 본 프로젝트 내부에서 사용하는 "
        "성장 안정 구간이다. GDP 자료는 분기 자료이므로 실제 발표 지연을 엄밀히 반영하려면 "
        "후속 실험에서 별도의 release lag를 적용해야 한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 9. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("12_build_macro_companion_layer.py 실행 시작")
    print("=" * 80)

    print("[1] 입력 파일 확인")
    for path in [INPUT_RATE, INPUT_RP, INPUT_FX, INPUT_GDP]:
        require_file(path)
        print(f"    OK: {path}")

    print("[2] 금리 월말 자료 생성")
    rate_monthly = build_rate_monthly()
    print(f"    rate_monthly shape = {rate_monthly.shape}")

    print("[3] 환율 월말 자료 생성")
    fx_monthly = build_fx_monthly()
    print(f"    fx_monthly shape = {fx_monthly.shape}")

    print("[4] GDP 월말 확장 자료 생성")
    gdp_monthly = build_gdp_monthly()
    print(f"    gdp_monthly shape = {gdp_monthly.shape}")

    print("[5] macro companion feature 생성")
    macro_features = build_macro_companion_features(
        rate_monthly=rate_monthly,
        fx_monthly=fx_monthly,
        gdp_monthly=gdp_monthly,
    )
    print(f"    macro_features shape = {macro_features.shape}")

    print("[6] main_final 월 기준 정렬")
    macro_aligned = align_to_main_final_months(macro_features)
    macro_aligned = add_availability_flags(macro_aligned)
    print(f"    macro_aligned shape = {macro_aligned.shape}")

    print("[7] 점검표 생성")
    quality = make_quality_check(macro_aligned)
    signal_summary = make_signal_summary(macro_aligned)

    print("[8] 저장")
    macro_aligned.to_csv(OUTPUT_FEATURES, index=False, encoding="utf-8-sig")
    quality.to_csv(OUTPUT_QUALITY, index=False, encoding="utf-8-sig")
    signal_summary.to_csv(OUTPUT_SIGNAL_SUMMARY, index=False, encoding="utf-8-sig")

    note = make_note()
    OUTPUT_NOTE.write_text(note, encoding="utf-8")

    print("\n[저장 완료]")
    for path in [
        OUTPUT_FEATURES,
        OUTPUT_QUALITY,
        OUTPUT_SIGNAL_SUMMARY,
        OUTPUT_NOTE,
    ]:
        print(f"- {path}")

    print("\n[품질 점검]")
    print(quality.to_string(index=False))

    print("\n[신호 요약]")
    print(signal_summary.to_string(index=False))

    print("\n[최근 10행]")
    preview_cols = [
        "year_month",
        "macro_data_available",
        "gdp_data_available",
        "rate_level",
        "rate_change_1m",
        "usdkrw",
        "usdkrw_return_1m",
        "gdp_growth_pct_lagged",
        "gdp_growth_band",
        "rate_fx_departure",
        "rate_fx_risk_departure_flag",
        "policy_growth_pressure_flag",
        "macro_defense_addon",
        "macro_companion_regime",
        "macro_companion_regime_filled",
        "gdp_availability_status",
    ]
    preview_cols = [c for c in preview_cols if c in macro_aligned.columns]
    print(macro_aligned[preview_cols].tail(10).to_string(index=False))

    print("\n" + "=" * 80)
    print("12_build_macro_companion_layer.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()