from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd


"""
32_main_v3_prepare_monthly_signal_inputs.py

목적
----
31번에서 생성된 일별 HSI 원점수(hsi_raw_scores.csv)를
월말 기준 HSI 신호 입력표로 변환한다.

현재 단계에서는 백테스트, Grid Search, Robustness를 실행하지 않는다.
이 파일의 목적은 main_v3 실험으로 넘어가기 위한 월별 신호 입력 구조를 만드는 것이다.

입력
----
data/processed/hsi_raw_scores.csv
data/processed/monthly_returns.csv
data/processed/selected_etf_universe.csv
data/processed/asset_class_map.csv

출력
----
data/processed/main_v3_monthly_signal_inputs_wide.csv
data/processed/main_v3_monthly_signal_inputs_long.csv
data/processed/main_v3_monthly_signal_return_alignment_preview.csv

output/tables/main_v3_signal_input_column_map.csv
output/tables/main_v3_signal_input_availability_check.csv
output/tables/main_v3_signal_input_quality_summary.csv

docs/main_v3_monthly_signal_input_note.md
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

INPUT_HSI_RAW_SCORES = DATA_PROCESSED_DIR / "hsi_raw_scores.csv"
INPUT_MONTHLY_RETURNS = DATA_PROCESSED_DIR / "monthly_returns.csv"
INPUT_SELECTED_ETF = DATA_PROCESSED_DIR / "selected_etf_universe.csv"
INPUT_ASSET_CLASS = DATA_PROCESSED_DIR / "asset_class_map.csv"

OUTPUT_MONTHLY_SIGNAL_WIDE = DATA_PROCESSED_DIR / "main_v3_monthly_signal_inputs_wide.csv"
OUTPUT_MONTHLY_SIGNAL_LONG = DATA_PROCESSED_DIR / "main_v3_monthly_signal_inputs_long.csv"
OUTPUT_ALIGNMENT_PREVIEW = DATA_PROCESSED_DIR / "main_v3_monthly_signal_return_alignment_preview.csv"

OUTPUT_COLUMN_MAP = TABLE_DIR / "main_v3_signal_input_column_map.csv"
OUTPUT_AVAILABILITY_CHECK = TABLE_DIR / "main_v3_signal_input_availability_check.csv"
OUTPUT_QUALITY_SUMMARY = TABLE_DIR / "main_v3_signal_input_quality_summary.csv"

OUTPUT_NOTE = DOCS_DIR / "main_v3_monthly_signal_input_note.md"


# ============================================================
# 1. 설정
# ============================================================

BASIC_SIGNAL_NAMES = ["return", "ma_pos", "momentum", "vol", "rs"]

# main_v3 설계표에 적어 둔 확장 후보.
# 현재 주원님 기본 파이프라인 산출물에는 아직 없을 가능성이 높다.
EXTENDED_SIGNAL_CANDIDATES = [
    "ma20_gap",
    "ma60_gap",
    "vol20",
    "drawdown_60",
    "risk_vs_cash_ret20",
]

BENCHMARK_TICKER = "069500"


# ============================================================
# 2. 유틸 함수
# ============================================================

def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"필수 입력 파일을 찾을 수 없습니다: {path}")


def read_indexed_csv(path: Path, parse_date_index: bool = True) -> pd.DataFrame:
    require_file(path)

    if parse_date_index:
        df = pd.read_csv(path, index_col=0)
        df.index = pd.to_datetime(df.index)
    else:
        df = pd.read_csv(path)

    return df


def resample_month_end(df: pd.DataFrame) -> pd.DataFrame:
    """
    일별 데이터를 월말 값으로 변환한다.
    pandas 버전에 따라 'ME'가 안 될 수 있으므로 fallback을 둔다.
    """
    try:
        monthly = df.resample("ME").last()
    except ValueError:
        monthly = df.resample("M").last()

    monthly.index = monthly.index.to_period("M").astype(str)
    monthly.index.name = "year_month"
    return monthly


def parse_score_column(col: str) -> tuple[str, str]:
    """
    예: 069500_return -> ("069500", "return")
    """
    parts = col.split("_", 1)

    if len(parts) != 2:
        return col, ""

    ticker, signal_name = parts[0], parts[1]
    return ticker, signal_name


def build_column_map(raw_scores: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for col in raw_scores.columns:
        ticker, signal_name = parse_score_column(col)
        rows.append({
            "source_column": col,
            "ticker": ticker,
            "signal_name": signal_name,
            "is_basic_signal": signal_name in BASIC_SIGNAL_NAMES,
            "is_extended_candidate": signal_name in EXTENDED_SIGNAL_CANDIDATES,
            "note": (
                "benchmark 자기비교로 rs는 NaN 가능"
                if ticker == BENCHMARK_TICKER and signal_name == "rs"
                else ""
            ),
        })

    return pd.DataFrame(rows)


def build_monthly_signal_long(
    monthly_signal_wide: pd.DataFrame,
    selected_etf: pd.DataFrame,
) -> pd.DataFrame:
    """
    wide 형식:
      year_month | 069500_return | 069500_ma_pos | ...

    long 형식:
      year_month | ticker | score_return | score_ma_pos | ...
    """
    etf_meta = selected_etf.set_index("ticker").to_dict(orient="index")
    rows = []

    tickers = sorted({parse_score_column(c)[0] for c in monthly_signal_wide.columns})

    for year_month, row in monthly_signal_wide.iterrows():
        for ticker in tickers:
            out = {
                "year_month": year_month,
                "ticker": ticker,
                "name": etf_meta.get(ticker, {}).get("name", ""),
                "asset_class": etf_meta.get(ticker, {}).get("asset_class", ""),
                "underlying_asset": etf_meta.get(ticker, {}).get("underlying_asset", ""),
                "risk_group": etf_meta.get(ticker, {}).get("risk_group", ""),
                "score_method_source": "zscore_from_data_pipeline",
                "benchmark_rs_note": (
                    "benchmark_self_comparison"
                    if ticker == BENCHMARK_TICKER
                    else ""
                ),
            }

            for signal_name in BASIC_SIGNAL_NAMES + EXTENDED_SIGNAL_CANDIDATES:
                col = f"{ticker}_{signal_name}"
                out[f"score_{signal_name}"] = row[col] if col in monthly_signal_wide.columns else np.nan

            rows.append(out)

    long_df = pd.DataFrame(rows)

    ordered_cols = [
        "year_month",
        "ticker",
        "name",
        "asset_class",
        "underlying_asset",
        "risk_group",
        "score_method_source",
        "benchmark_rs_note",
    ] + [f"score_{s}" for s in BASIC_SIGNAL_NAMES + EXTENDED_SIGNAL_CANDIDATES]

    return long_df[ordered_cols]


def build_availability_check(
    monthly_signal_long: pd.DataFrame,
    selected_etf: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    tickers = selected_etf["ticker"].astype(str).tolist()

    for ticker in tickers:
        ticker_df = monthly_signal_long[monthly_signal_long["ticker"] == ticker]

        for signal_name in BASIC_SIGNAL_NAMES + EXTENDED_SIGNAL_CANDIDATES:
            col = f"score_{signal_name}"

            total_rows = len(ticker_df)
            non_null_count = int(ticker_df[col].notna().sum()) if col in ticker_df.columns else 0
            missing_count = total_rows - non_null_count
            missing_ratio = round(missing_count / total_rows, 4) if total_rows > 0 else np.nan

            if ticker == BENCHMARK_TICKER and signal_name == "rs":
                status = "OK_BENCHMARK_NA_ALLOWED"
                note = "069500은 benchmark 자기비교이므로 rs NaN 허용"
            elif signal_name in EXTENDED_SIGNAL_CANDIDATES and non_null_count == 0:
                status = "NOT_AVAILABLE_YET"
                note = "main_v3 확장 후보이나 현재 기본 파이프라인에는 없음"
            elif non_null_count > 0:
                status = "OK"
                note = "월말 신호 생성됨"
            else:
                status = "CHECK"
                note = "값이 생성되지 않음"

            rows.append({
                "ticker": ticker,
                "signal_name": signal_name,
                "total_months": total_rows,
                "non_null_count": non_null_count,
                "missing_count": missing_count,
                "missing_ratio": missing_ratio,
                "status": status,
                "note": note,
            })

    return pd.DataFrame(rows)


def build_quality_summary(
    monthly_signal_wide: pd.DataFrame,
    monthly_signal_long: pd.DataFrame,
    monthly_returns: pd.DataFrame,
    availability_check: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    basic_ok = availability_check[
        (availability_check["signal_name"].isin(BASIC_SIGNAL_NAMES))
        & (~availability_check["status"].isin(["CHECK"]))
    ]

    extended_available = availability_check[
        (availability_check["signal_name"].isin(EXTENDED_SIGNAL_CANDIDATES))
        & (availability_check["status"] == "OK")
    ]

    rows.append({
        "check_item": "monthly_signal_wide_shape",
        "result": f"{monthly_signal_wide.shape[0]} rows x {monthly_signal_wide.shape[1]} columns",
        "status": "OK" if monthly_signal_wide.shape[0] > 0 else "CHECK",
        "note": "일별 HSI 원점수의 월말 변환 결과",
    })

    rows.append({
        "check_item": "monthly_signal_long_shape",
        "result": f"{monthly_signal_long.shape[0]} rows x {monthly_signal_long.shape[1]} columns",
        "status": "OK" if monthly_signal_long.shape[0] > 0 else "CHECK",
        "note": "월별·ETF별 long format 변환 결과",
    })

    rows.append({
        "check_item": "monthly_returns_shape",
        "result": f"{monthly_returns.shape[0]} rows x {monthly_returns.shape[1]} columns",
        "status": "OK" if monthly_returns.shape[0] > 0 else "CHECK",
        "note": "다음 단계에서 월말 신호와 연결할 수익률표",
    })

    rows.append({
        "check_item": "basic_signal_available_count",
        "result": len(basic_ok),
        "status": "OK" if len(basic_ok) >= 14 else "CHECK",
        "note": "3개 ETF × 5개 기본 신호 중 benchmark rs는 NaN 허용",
    })

    rows.append({
        "check_item": "extended_signal_available_count",
        "result": len(extended_available),
        "status": "INFO",
        "note": "확장 후보 신호는 현재 파일에 없을 수 있음. 후속 파일 또는 추가 계산 필요.",
    })

    rows.append({
        "check_item": "score_method_source",
        "result": "zscore_from_data_pipeline",
        "status": "INFO",
        "note": "우리 프로젝트 최종 실험에서는 rank 기본, zscore 보조 비교로 유지",
    })

    return pd.DataFrame(rows)


def build_alignment_preview(
    monthly_signal_long: pd.DataFrame,
    monthly_returns: pd.DataFrame,
) -> pd.DataFrame:
    """
    아직 백테스트는 하지 않는다.
    월말 신호가 다음 달 수익률과 연결될 수 있는지 preview만 만든다.
    """
    returns = monthly_returns.copy()
    returns.index = returns.index.astype(str)
    returns.index.name = "return_month"

    return_long = (
        returns
        .reset_index()
        .melt(
            id_vars="return_month",
            var_name="ticker",
            value_name="next_month_return"
        )
    )

    return_long["signal_month"] = (
        pd.PeriodIndex(return_long["return_month"], freq="M") - 1
    ).astype(str)

    signal_cols = [
        "year_month",
        "ticker",
        "score_return",
        "score_ma_pos",
        "score_momentum",
        "score_vol",
        "score_rs",
        "score_method_source",
        "benchmark_rs_note",
    ]

    signal_small = monthly_signal_long[signal_cols].copy()
    signal_small = signal_small.rename(columns={"year_month": "signal_month"})

    aligned = pd.merge(
        signal_small,
        return_long,
        on=["signal_month", "ticker"],
        how="inner",
    )

    aligned["alignment_rule"] = "signal_month_t_to_return_month_t_plus_1"

    ordered_cols = [
        "signal_month",
        "return_month",
        "ticker",
        "score_method_source",
        "score_return",
        "score_ma_pos",
        "score_momentum",
        "score_vol",
        "score_rs",
        "benchmark_rs_note",
        "next_month_return",
        "alignment_rule",
    ]

    return aligned[ordered_cols]


def make_markdown_note(
    monthly_signal_wide: pd.DataFrame,
    monthly_signal_long: pd.DataFrame,
    monthly_returns: pd.DataFrame,
    availability_check: pd.DataFrame,
    quality_summary: pd.DataFrame,
    alignment_preview: pd.DataFrame,
) -> str:
    lines = []

    lines.append("# main_v3 월말 신호 입력표 생성 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "31번에서 생성된 일별 HSI 원점수(`hsi_raw_scores.csv`)를 "
        "월말 기준 신호 입력표로 변환하였다. "
        "이 파일은 main_v3 신호 조합 실험과 HSI 상태분류로 넘어가기 위한 중간 연결 고리이다."
    )
    lines.append("")
    lines.append("## 2. 생성 파일")
    lines.append("")
    lines.append("- `data/processed/main_v3_monthly_signal_inputs_wide.csv`")
    lines.append("- `data/processed/main_v3_monthly_signal_inputs_long.csv`")
    lines.append("- `data/processed/main_v3_monthly_signal_return_alignment_preview.csv`")
    lines.append("- `output/tables/main_v3_signal_input_column_map.csv`")
    lines.append("- `output/tables/main_v3_signal_input_availability_check.csv`")
    lines.append("- `output/tables/main_v3_signal_input_quality_summary.csv`")
    lines.append("")
    lines.append("## 3. 크기 요약")
    lines.append("")
    lines.append(f"- 월말 신호 wide: `{monthly_signal_wide.shape[0]} rows × {monthly_signal_wide.shape[1]} columns`")
    lines.append(f"- 월말 신호 long: `{monthly_signal_long.shape[0]} rows × {monthly_signal_long.shape[1]} columns`")
    lines.append(f"- 월간 수익률: `{monthly_returns.shape[0]} rows × {monthly_returns.shape[1]} columns`")
    lines.append(f"- 신호-다음달 수익률 연결 preview: `{alignment_preview.shape[0]} rows × {alignment_preview.shape[1]} columns`")
    lines.append("")
    lines.append("## 4. 기본 신호와 확장 신호")
    lines.append("")
    lines.append("기본 신호는 다음 5개이다.")
    lines.append("")
    for sig in BASIC_SIGNAL_NAMES:
        lines.append(f"- `{sig}`")
    lines.append("")
    lines.append("main_v3 확장 후보 신호는 다음 5개이다.")
    lines.append("")
    for sig in EXTENDED_SIGNAL_CANDIDATES:
        lines.append(f"- `{sig}`")
    lines.append("")
    lines.append(
        "현재 데이터 담당 파이프라인의 기본 산출물에는 기본 HSI 5신호가 중심으로 들어 있으며, "
        "확장 후보 신호는 아직 없을 수 있다. 확장 후보 신호는 후속 파일 수령 또는 별도 계산으로 보강한다."
    )
    lines.append("")
    lines.append("## 5. benchmark rs 처리")
    lines.append("")
    lines.append(
        "`069500`은 상대강도 계산의 기준자산이므로, 자기 자신과의 `rs`는 정보량이 없다. "
        "따라서 `score_rs`가 NaN이어도 계산 오류로 보지 않고, "
        "`benchmark_rs_note`에 `benchmark_self_comparison`으로 표시하였다."
    )
    lines.append("")
    lines.append("## 6. 시점 정합성")
    lines.append("")
    lines.append(
        "이번 단계에서는 월말 신호를 다음 달 수익률에 연결할 수 있는지 preview만 만들었다. "
        "실제 백테스트에서는 `signal_month`의 HSI 상태를 `return_month`의 수익률에 적용한다."
    )
    lines.append("")
    lines.append("## 7. 품질 점검 요약")
    lines.append("")
    lines.append("| check_item | result | status | note |")
    lines.append("|---|---|---|---|")

    for _, row in quality_summary.iterrows():
        lines.append(
            f"| {row['check_item']} | {row['result']} | {row['status']} | {row['note']} |"
        )

    lines.append("")
    lines.append("## 8. 다음 단계")
    lines.append("")
    lines.append(
        "다음 단계에서는 이 월말 신호 입력표를 사용해 HSI 5상태 분류표를 재생성하고, "
        "`main_v2b` 기준 비중 규칙과 연결한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 3. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("32_main_v3_prepare_monthly_signal_inputs.py 실행 시작")
    print("=" * 80)

    print("[1] 입력 파일 확인")
    for path in [
        INPUT_HSI_RAW_SCORES,
        INPUT_MONTHLY_RETURNS,
        INPUT_SELECTED_ETF,
        INPUT_ASSET_CLASS,
    ]:
        require_file(path)
        print(f"    OK: {path}")

    print("[2] 입력 데이터 로드")
    hsi_raw_scores = read_indexed_csv(INPUT_HSI_RAW_SCORES, parse_date_index=True)
    monthly_returns = read_indexed_csv(INPUT_MONTHLY_RETURNS, parse_date_index=False)
    selected_etf = pd.read_csv(INPUT_SELECTED_ETF, dtype={"ticker": str})
    asset_class = pd.read_csv(INPUT_ASSET_CLASS, dtype={"ticker": str})

    # monthly_returns는 첫 컬럼이 year_month일 가능성이 높다.
    if "year_month" in monthly_returns.columns:
        monthly_returns = monthly_returns.set_index("year_month")
    else:
        monthly_returns = pd.read_csv(INPUT_MONTHLY_RETURNS, index_col=0)

    monthly_returns.index = monthly_returns.index.astype(str)

    print(f"    hsi_raw_scores shape = {hsi_raw_scores.shape}")
    print(f"    monthly_returns shape = {monthly_returns.shape}")
    print(f"    selected_etf shape = {selected_etf.shape}")
    print(f"    asset_class shape = {asset_class.shape}")

    print("[3] 컬럼 매핑표 생성")
    column_map = build_column_map(hsi_raw_scores)

    print("[4] 일별 HSI 원점수 → 월말 HSI 신호 입력표 변환")
    monthly_signal_wide = resample_month_end(hsi_raw_scores)

    print("[5] long format 변환")
    monthly_signal_long = build_monthly_signal_long(
        monthly_signal_wide=monthly_signal_wide,
        selected_etf=selected_etf,
    )

    print("[6] 신호 사용 가능성 점검")
    availability_check = build_availability_check(
        monthly_signal_long=monthly_signal_long,
        selected_etf=selected_etf,
    )

    print("[7] 월말 신호와 다음 달 수익률 연결 preview 생성")
    alignment_preview = build_alignment_preview(
        monthly_signal_long=monthly_signal_long,
        monthly_returns=monthly_returns,
    )

    print("[8] 품질 요약 생성")
    quality_summary = build_quality_summary(
        monthly_signal_wide=monthly_signal_wide,
        monthly_signal_long=monthly_signal_long,
        monthly_returns=monthly_returns,
        availability_check=availability_check,
    )

    print("[9] CSV 저장")
    monthly_signal_wide.to_csv(OUTPUT_MONTHLY_SIGNAL_WIDE, encoding="utf-8-sig")
    monthly_signal_long.to_csv(OUTPUT_MONTHLY_SIGNAL_LONG, index=False, encoding="utf-8-sig")
    alignment_preview.to_csv(OUTPUT_ALIGNMENT_PREVIEW, index=False, encoding="utf-8-sig")

    column_map.to_csv(OUTPUT_COLUMN_MAP, index=False, encoding="utf-8-sig")
    availability_check.to_csv(OUTPUT_AVAILABILITY_CHECK, index=False, encoding="utf-8-sig")
    quality_summary.to_csv(OUTPUT_QUALITY_SUMMARY, index=False, encoding="utf-8-sig")

    print("[10] Markdown 노트 저장")
    note = make_markdown_note(
        monthly_signal_wide=monthly_signal_wide,
        monthly_signal_long=monthly_signal_long,
        monthly_returns=monthly_returns,
        availability_check=availability_check,
        quality_summary=quality_summary,
        alignment_preview=alignment_preview,
    )
    OUTPUT_NOTE.write_text(note, encoding="utf-8")

    print("\n[저장 완료]")
    for path in [
        OUTPUT_MONTHLY_SIGNAL_WIDE,
        OUTPUT_MONTHLY_SIGNAL_LONG,
        OUTPUT_ALIGNMENT_PREVIEW,
        OUTPUT_COLUMN_MAP,
        OUTPUT_AVAILABILITY_CHECK,
        OUTPUT_QUALITY_SUMMARY,
        OUTPUT_NOTE,
    ]:
        print(f"- {path}")

    print("\n[품질 요약]")
    print(quality_summary.to_string(index=False))

    print("\n[신호 사용 가능성 요약]")
    status_summary = (
        availability_check
        .groupby(["signal_name", "status"])
        .size()
        .reset_index(name="count")
    )
    print(status_summary.to_string(index=False))

    print("\n[연결 preview]")
    print(alignment_preview.head(10).to_string(index=False))

    print("\n" + "=" * 80)
    print("32_main_v3_prepare_monthly_signal_inputs.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()