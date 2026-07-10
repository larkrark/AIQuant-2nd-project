from pathlib import Path
from datetime import datetime
import importlib.util

import numpy as np
import pandas as pd


"""
35_main_v3_build_extended_signal_inputs.py

목적
----
main_v3 추가 지표 후보를 생성한다.

이 파일은 백테스트를 실행하지 않는다.
이 파일은 HSI 상태분류 규칙을 바꾸지 않는다.
이 파일은 비중 규칙을 바꾸지 않는다.

하는 일
-------
1. 데이터 담당 파이프라인 모듈을 불러와 일별 가격 데이터를 다시 로드한다.
2. 일별 가격으로 추가 지표 후보를 계산한다.
3. 각 지표를 HSI 방향 기준으로 통일한다.
   - 양수 = 위험 악화 방향
   - 음수 = 위험 완화 방향
4. rolling z-score를 이용해 -10 ~ +10 범위의 score로 변환한다.
5. 월말 기준으로 변환한다.
6. 32번에서 만든 월말 신호 입력표에 추가 지표 score를 붙인다.
7. 신호군 설계표와 품질 점검표를 저장한다.

입력
----
src/HSI_data_pipeline_0629_3.py
data/processed/main_v3_monthly_signal_inputs_long.csv

출력
----
data/processed/main_v3_extended_signal_scores_daily.csv
data/processed/main_v3_extended_signal_inputs_wide.csv
data/processed/main_v3_extended_signal_inputs_long.csv

output/tables/main_v3_extended_signal_family_design.csv
output/tables/main_v3_extended_signal_quality_check.csv
output/tables/main_v3_extended_signal_column_map.csv

docs/main_v3_extended_signal_input_note.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SRC_DIR = PROJECT_ROOT / "src"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
DOCS_DIR = PROJECT_ROOT / "docs"

DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

PIPELINE_PATH = SRC_DIR / "HSI_data_pipeline_0629_4.py"

INPUT_BASE_MONTHLY_LONG = DATA_PROCESSED_DIR / "main_v3_monthly_signal_inputs_long.csv"

OUTPUT_DAILY_EXTENDED = DATA_PROCESSED_DIR / "main_v3_extended_signal_scores_daily.csv"
OUTPUT_EXTENDED_WIDE = DATA_PROCESSED_DIR / "main_v3_extended_signal_inputs_wide.csv"
OUTPUT_EXTENDED_LONG = DATA_PROCESSED_DIR / "main_v3_extended_signal_inputs_long.csv"

OUTPUT_FAMILY_DESIGN = TABLE_DIR / "main_v3_extended_signal_family_design.csv"
OUTPUT_QUALITY_CHECK = TABLE_DIR / "main_v3_extended_signal_quality_check.csv"
OUTPUT_COLUMN_MAP = TABLE_DIR / "main_v3_extended_signal_column_map.csv"

OUTPUT_NOTE = DOCS_DIR / "main_v3_extended_signal_input_note.md"


# ============================================================
# 1. 설정
# ============================================================

RISK_TICKER = "069500"
BOND_TICKER = "114260"
CASH_TICKER = "153130"

TICKERS = [RISK_TICKER, BOND_TICKER, CASH_TICKER]

EXTENDED_SIGNALS = [
    "ma20_gap",
    "ma60_gap",
    "vol20",
    "drawdown_60",
    "risk_vs_cash_ret20",
]

# rolling z-score 설정
ZSCORE_WINDOW = 252
ZSCORE_MIN_PERIODS = 60
SCORE_CLIP = 10.0

# 지표별 HSI 방향 통일 규칙
# +1: 원지표가 클수록 위험 악화
# -1: 원지표가 클수록 위험 완화이므로 부호 반전
DIRECTION_SIGN = {
    "ma20_gap": -1,
    "ma60_gap": -1,
    "vol20": 1,
    "drawdown_60": -1,
    "risk_vs_cash_ret20": -1,
}


# ============================================================
# 2. 모듈 로드 및 유틸 함수
# ============================================================

def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"필수 파일을 찾을 수 없습니다: {path}")


def load_pipeline_module(module_path: Path):
    require_file(module_path)

    spec = importlib.util.spec_from_file_location(
        "hsi_data_pipeline_0629_3",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def safe_month_end_resample(df: pd.DataFrame) -> pd.DataFrame:
    try:
        monthly = df.resample("ME").last()
    except ValueError:
        monthly = df.resample("M").last()

    monthly.index = monthly.index.to_period("M").astype(str)
    monthly.index.name = "year_month"

    return monthly


def rolling_zscore_to_score(series: pd.Series) -> pd.Series:
    """
    rolling z-score를 -10 ~ +10 score로 변환한다.

    중요
    ----
    rolling mean/std 계산에는 shift(1)을 적용한다.
    즉, 오늘 값을 오늘 기준분포 계산에 포함하지 않는다.
    """
    mean = (
        series
        .rolling(window=ZSCORE_WINDOW, min_periods=ZSCORE_MIN_PERIODS)
        .mean()
        .shift(1)
    )

    std = (
        series
        .rolling(window=ZSCORE_WINDOW, min_periods=ZSCORE_MIN_PERIODS)
        .std(ddof=1)
        .shift(1)
    )

    z = (series - mean) / std
    score = z.clip(-SCORE_CLIP, SCORE_CLIP)

    return score


# ============================================================
# 3. 추가 지표 계산
# ============================================================

def calculate_extended_raw_signals(prices: pd.DataFrame) -> pd.DataFrame:
    """
    일별 가격으로 추가 지표 원값을 계산한다.
    """
    prices = prices.copy()
    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index()

    daily_returns = prices.pct_change()

    raw_frames = []

    for ticker in prices.columns:
        p = prices[ticker].astype(float)
        r = daily_returns[ticker].astype(float)

        ma20 = p.rolling(20, min_periods=20).mean()
        ma60 = p.rolling(60, min_periods=60).mean()

        ret20 = p / p.shift(20) - 1.0
        cash_ret20 = prices[CASH_TICKER].astype(float) / prices[CASH_TICKER].astype(float).shift(20) - 1.0

        raw = pd.DataFrame(index=prices.index)
        raw[f"{ticker}_ma20_gap_raw"] = p / ma20 - 1.0
        raw[f"{ticker}_ma60_gap_raw"] = p / ma60 - 1.0
        raw[f"{ticker}_vol20_raw"] = r.rolling(20, min_periods=20).std(ddof=1) * np.sqrt(252)
        raw[f"{ticker}_drawdown_60_raw"] = p / p.rolling(60, min_periods=60).max() - 1.0
        raw[f"{ticker}_risk_vs_cash_ret20_raw"] = ret20 - cash_ret20

        raw_frames.append(raw)

    raw_signals = pd.concat(raw_frames, axis=1)

    return raw_signals


def convert_raw_to_hsi_direction(raw_signals: pd.DataFrame) -> pd.DataFrame:
    """
    원지표를 HSI 방향 기준으로 변환한다.
    양수 = 위험 악화 방향
    음수 = 위험 완화 방향
    """
    direction_df = pd.DataFrame(index=raw_signals.index)

    for ticker in TICKERS:
        for signal_name in EXTENDED_SIGNALS:
            raw_col = f"{ticker}_{signal_name}_raw"
            direction_col = f"{ticker}_{signal_name}_direction"

            sign = DIRECTION_SIGN[signal_name]

            direction_df[direction_col] = raw_signals[raw_col] * sign

    return direction_df


def convert_direction_to_scores(direction_df: pd.DataFrame) -> pd.DataFrame:
    """
    HSI 방향 통일 지표를 rolling z-score 기반 score로 변환한다.
    """
    score_df = pd.DataFrame(index=direction_df.index)

    for col in direction_df.columns:
        score_col = col.replace("_direction", "")
        score_df[score_col] = rolling_zscore_to_score(direction_df[col])

    return score_df


def build_daily_extended_table(
    raw_signals: pd.DataFrame,
    direction_df: pd.DataFrame,
    score_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    원값, 방향변환값, score를 하나의 일별 표로 저장한다.
    """
    out = pd.concat(
        [
            raw_signals,
            direction_df,
            score_df.add_suffix("_score"),
        ],
        axis=1,
    )

    out.index.name = "date"

    return out


# ============================================================
# 4. 월말 wide / long 변환
# ============================================================

def build_monthly_extended_wide(score_df: pd.DataFrame) -> pd.DataFrame:
    """
    일별 score를 월말 score로 변환한다.
    """
    monthly = safe_month_end_resample(score_df)

    # 기존 naming과 맞추기 위해 score 컬럼명을 ticker_signal 형태로 유지한다.
    return monthly


def build_extended_long(
    base_monthly_long: pd.DataFrame,
    monthly_extended_wide: pd.DataFrame,
) -> pd.DataFrame:
    """
    32번 long format에 추가 지표 score를 병합한다.
    """
    rows = []

    monthly_extended_wide = monthly_extended_wide.copy()
    monthly_extended_wide.index = monthly_extended_wide.index.astype(str)

    for _, base_row in base_monthly_long.iterrows():
        year_month = str(base_row["year_month"])
        ticker = str(base_row["ticker"]).zfill(6)

        out = base_row.to_dict()

        for signal_name in EXTENDED_SIGNALS:
            col = f"{ticker}_{signal_name}"
            value = (
                monthly_extended_wide.loc[year_month, col]
                if year_month in monthly_extended_wide.index and col in monthly_extended_wide.columns
                else np.nan
            )
            out[f"score_{signal_name}"] = value

        out["extended_signal_source"] = "daily_price_derived_rolling_zscore"
        out["extended_signal_note"] = (
            "positive score = risk worsening, negative score = risk relief"
        )

        rows.append(out)

    extended_long = pd.DataFrame(rows)

    return extended_long


# ============================================================
# 5. 설계표 / 점검표 / 노트
# ============================================================

def make_signal_family_design() -> pd.DataFrame:
    rows = [
        {
            "signal_name": "ma20_gap",
            "signal_family": "trend",
            "speed_group": "fast",
            "raw_definition": "price / MA20 - 1",
            "hsi_direction_rule": "높을수록 위험 완화 → 부호 반전",
            "expected_role": "단기 추세 개선 또는 악화 감지",
            "caution": "단기 잡음에 민감할 수 있음",
        },
        {
            "signal_name": "ma60_gap",
            "signal_family": "trend",
            "speed_group": "slow",
            "raw_definition": "price / MA60 - 1",
            "hsi_direction_rule": "높을수록 위험 완화 → 부호 반전",
            "expected_role": "중기 추세 구조 확인",
            "caution": "반응이 늦을 수 있음",
        },
        {
            "signal_name": "vol20",
            "signal_family": "risk_damage",
            "speed_group": "fast",
            "raw_definition": "20-day realized volatility",
            "hsi_direction_rule": "높을수록 위험 악화",
            "expected_role": "단기 변동성 확대 감지",
            "caution": "급등락 이후 일시적으로 높게 유지될 수 있음",
        },
        {
            "signal_name": "drawdown_60",
            "signal_family": "risk_damage",
            "speed_group": "slow",
            "raw_definition": "price / rolling 60-day max - 1",
            "hsi_direction_rule": "값이 낮을수록 위험 악화 → 부호 반전",
            "expected_role": "누적 손상 정도 확인",
            "caution": "회복 초기에 후행할 수 있음",
        },
        {
            "signal_name": "risk_vs_cash_ret20",
            "signal_family": "relative_strength",
            "speed_group": "fast",
            "raw_definition": "20-day return of asset - 20-day return of cash-like ETF",
            "hsi_direction_rule": "높을수록 위험 완화 → 부호 반전",
            "expected_role": "위험자산이 현금성 자산 대비 강한지 확인",
            "caution": "현금성 ETF와 비교하므로 시장 국면에 따라 해석 필요",
        },
    ]

    return pd.DataFrame(rows)


def make_column_map(monthly_extended_wide: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for col in monthly_extended_wide.columns:
        parts = col.split("_", 1)
        ticker = parts[0]
        signal_name = parts[1] if len(parts) > 1 else ""

        rows.append({
            "column_name": col,
            "ticker": ticker,
            "signal_name": signal_name,
            "is_extended_signal": signal_name in EXTENDED_SIGNALS,
            "score_unit": "rolling_zscore_clipped_-10_to_10",
            "score_direction": "positive=risk_worsening, negative=risk_relief",
        })

    return pd.DataFrame(rows)


def make_quality_check(
    base_monthly_long: pd.DataFrame,
    extended_long: pd.DataFrame,
    monthly_extended_wide: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    rows.append({
        "check_item": "base_monthly_long_shape",
        "result": f"{base_monthly_long.shape[0]} rows x {base_monthly_long.shape[1]} columns",
        "status": "OK" if len(base_monthly_long) > 0 else "CHECK",
        "note": "32번 월말 신호 입력표",
    })

    rows.append({
        "check_item": "monthly_extended_wide_shape",
        "result": f"{monthly_extended_wide.shape[0]} rows x {monthly_extended_wide.shape[1]} columns",
        "status": "OK" if len(monthly_extended_wide) > 0 else "CHECK",
        "note": "추가 지표 월말 wide table",
    })

    rows.append({
        "check_item": "extended_long_shape",
        "result": f"{extended_long.shape[0]} rows x {extended_long.shape[1]} columns",
        "status": "OK" if len(extended_long) == len(base_monthly_long) else "CHECK",
        "note": "기존 월말 long table에 추가 지표 병합",
    })

    for signal_name in EXTENDED_SIGNALS:
        col = f"score_{signal_name}"

        total = len(extended_long)
        non_null = int(extended_long[col].notna().sum())
        missing = total - non_null
        missing_ratio = round(missing / total, 4) if total > 0 else np.nan

        if non_null > 0:
            status = "OK"
        else:
            status = "CHECK"

        rows.append({
            "check_item": f"{signal_name}_availability",
            "result": f"non_null={non_null}, missing={missing}, missing_ratio={missing_ratio}",
            "status": status,
            "note": "rolling 계산 초기 구간에는 결측이 자연스럽게 발생",
        })

    rows.append({
        "check_item": "score_direction_rule",
        "result": "positive=risk_worsening, negative=risk_relief",
        "status": "OK",
        "note": "기존 HSI 방향 기준과 동일하게 통일",
    })

    rows.append({
        "check_item": "use_in_strategy",
        "result": "not_yet",
        "status": "INFO",
        "note": "이번 파일은 추가 지표 입력표 생성 단계이며 백테스트는 다음 단계에서 수행",
    })

    return pd.DataFrame(rows)


def make_markdown_note(
    family_design: pd.DataFrame,
    quality_check: pd.DataFrame,
) -> str:
    lines = []

    lines.append("# main_v3 추가 지표 입력표 생성 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 파일은 main_v3 추가 지표 후보를 생성하기 위한 연결 단계이다. "
        "백테스트, 비중 규칙 변경, 최종 후보 선정은 아직 수행하지 않았다."
    )
    lines.append("")
    lines.append("## 2. 추가 지표 후보")
    lines.append("")
    lines.append("| signal_name | family | speed_group | expected_role | caution |")
    lines.append("|---|---|---|---|---|")

    for _, row in family_design.iterrows():
        lines.append(
            f"| {row['signal_name']} | {row['signal_family']} | "
            f"{row['speed_group']} | {row['expected_role']} | {row['caution']} |"
        )

    lines.append("")
    lines.append("## 3. 방향 통일")
    lines.append("")
    lines.append(
        "모든 추가 지표는 HSI 방향 기준으로 변환하였다. "
        "양수는 위험 악화 방향, 음수는 위험 완화 방향을 의미한다."
    )
    lines.append("")
    lines.append("## 4. 점수화 방식")
    lines.append("")
    lines.append(
        "각 추가 지표는 rolling z-score를 사용해 표준화한 뒤 -10에서 +10 사이로 제한하였다. "
        "rolling mean과 rolling standard deviation은 shift(1)을 적용해 현재 값을 기준분포 계산에 포함하지 않았다."
    )
    lines.append("")
    lines.append("## 5. 품질 점검")
    lines.append("")
    lines.append("| check_item | result | status | note |")
    lines.append("|---|---|---|---|")

    for _, row in quality_check.iterrows():
        lines.append(
            f"| {row['check_item']} | {row['result']} | {row['status']} | {row['note']} |"
        )

    lines.append("")
    lines.append("## 6. 다음 단계")
    lines.append("")
    lines.append(
        "다음 단계에서는 기본 HSI 신호와 추가 지표 조합을 비교하는 실험을 수행한다. "
        "main_v2b 비중 규칙은 고정하고, 신호 조합만 바꾸어 성과 차이를 확인한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 6. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("35_main_v3_build_extended_signal_inputs.py 실행 시작")
    print("=" * 80)

    print("[1] 입력 파일 확인")
    require_file(PIPELINE_PATH)
    require_file(INPUT_BASE_MONTHLY_LONG)

    print(f"    OK: {PIPELINE_PATH}")
    print(f"    OK: {INPUT_BASE_MONTHLY_LONG}")

    print("[2] 데이터 파이프라인 모듈 로드")
    pipe = load_pipeline_module(PIPELINE_PATH)

    print("[3] 일별 가격 데이터 로드")
    prices = pipe.load_price_data(
        tickers=TICKERS,
        start=pipe.DATA_START_DATE,
        source="yfinance",
    )
    prices.index = pd.to_datetime(prices.index)

    print(f"    prices shape = {prices.shape}")

    print("[4] 32번 월말 신호 long table 로드")
    base_monthly_long = pd.read_csv(
        INPUT_BASE_MONTHLY_LONG,
        dtype={"ticker": str},
        encoding="utf-8-sig",
    )
    base_monthly_long["ticker"] = base_monthly_long["ticker"].astype(str).str.zfill(6)
    base_monthly_long["year_month"] = base_monthly_long["year_month"].astype(str)

    print(f"    base_monthly_long shape = {base_monthly_long.shape}")

    print("[5] 추가 지표 원값 계산")
    raw_signals = calculate_extended_raw_signals(prices)

    print("[6] HSI 방향 기준으로 변환")
    direction_df = convert_raw_to_hsi_direction(raw_signals)

    print("[7] rolling z-score score 변환")
    score_df = convert_direction_to_scores(direction_df)

    print("[8] 일별 추가 지표 통합표 생성")
    daily_extended = build_daily_extended_table(
        raw_signals=raw_signals,
        direction_df=direction_df,
        score_df=score_df,
    )

    print("[9] 월말 추가 지표 wide table 생성")
    monthly_extended_wide = build_monthly_extended_wide(score_df)

    print("[10] 기존 월말 long table에 추가 지표 병합")
    extended_long = build_extended_long(
        base_monthly_long=base_monthly_long,
        monthly_extended_wide=monthly_extended_wide,
    )

    print("[11] 설계표 및 점검표 생성")
    family_design = make_signal_family_design()
    column_map = make_column_map(monthly_extended_wide)
    quality_check = make_quality_check(
        base_monthly_long=base_monthly_long,
        extended_long=extended_long,
        monthly_extended_wide=monthly_extended_wide,
    )

    print("[12] CSV 저장")
    daily_extended.to_csv(OUTPUT_DAILY_EXTENDED, encoding="utf-8-sig")
    monthly_extended_wide.to_csv(OUTPUT_EXTENDED_WIDE, encoding="utf-8-sig")
    extended_long.to_csv(OUTPUT_EXTENDED_LONG, index=False, encoding="utf-8-sig")

    family_design.to_csv(OUTPUT_FAMILY_DESIGN, index=False, encoding="utf-8-sig")
    quality_check.to_csv(OUTPUT_QUALITY_CHECK, index=False, encoding="utf-8-sig")
    column_map.to_csv(OUTPUT_COLUMN_MAP, index=False, encoding="utf-8-sig")

    print("[13] Markdown 노트 저장")
    note = make_markdown_note(
        family_design=family_design,
        quality_check=quality_check,
    )
    OUTPUT_NOTE.write_text(note, encoding="utf-8")

    print("\n[저장 완료]")
    for path in [
        OUTPUT_DAILY_EXTENDED,
        OUTPUT_EXTENDED_WIDE,
        OUTPUT_EXTENDED_LONG,
        OUTPUT_FAMILY_DESIGN,
        OUTPUT_QUALITY_CHECK,
        OUTPUT_COLUMN_MAP,
        OUTPUT_NOTE,
    ]:
        print(f"- {path}")

    print("\n[품질 점검]")
    print(quality_check.to_string(index=False))

    print("\n[추가 지표 설계표]")
    print(family_design.to_string(index=False))

    print("\n" + "=" * 80)
    print("35_main_v3_build_extended_signal_inputs.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()