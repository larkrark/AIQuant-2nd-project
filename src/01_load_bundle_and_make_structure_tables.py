from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
01_load_bundle_and_make_structure_tables.py

목적
----
데이터 담당 최종 산출물인 hsi_data_bundle.xlsx를 읽고,
후속 실험에서 사용할 기준 입력 시트들을 CSV로 분리 저장한다.

중요
----
이 파일은 yfinance를 다시 호출하지 않는다.
데이터를 새로 만드는 파일이 아니라,
최종 데이터 번들을 후속 실험용 기준 입력으로 정리하는 파일이다.

입력
----
output/tables/hsi_data_bundle.xlsx

주요 시트
---------
monthly_return_decimal : 백테스트 계산용 decimal 수익률
monthly_return_pct     : 보고서·검토용 percent 수익률
signal_inputs          : HSI 원신호 입력표
hsi_scaled_scores      : 표준화·부호통일·스케일링된 HSI 점수
hsi_direction          : HSI direction
signal_direction_map   : 신호 방향 정의표

출력
----
data/processed/main_final_*.csv
output/tables/main_final_*.csv
docs/main_final_bundle_structure_note.md
"""


# ============================================================
# 1. 출력 경로
# ============================================================

PROCESSED_OUTPUTS = {
    "asset_class": cfg.PROCESSED_DIR / "main_final_asset_class.csv",
    "monthly_price": cfg.PROCESSED_DIR / "main_final_monthly_price.csv",
    "monthly_return_decimal": cfg.PROCESSED_DIR / "main_final_monthly_return_decimal.csv",
    "monthly_return_pct": cfg.PROCESSED_DIR / "main_final_monthly_return_pct.csv",
    "signal_inputs": cfg.PROCESSED_DIR / "main_final_signal_inputs.csv",
    "hsi_scaled_scores": cfg.PROCESSED_DIR / "main_final_hsi_scaled_scores.csv",
    "hsi_direction": cfg.PROCESSED_DIR / "main_final_hsi_direction.csv",
    "hsi_signal": cfg.PROCESSED_DIR / "main_final_hsi_signal_raw3.csv",
    "signal_direction_map": cfg.PROCESSED_DIR / "main_final_signal_direction_map.csv",
}

INPUT_STRUCTURE_OUTPUT = cfg.TABLE_DIR / "main_final_input_structure.csv"
OUTPUT_STRUCTURE_OUTPUT = cfg.TABLE_DIR / "main_final_output_structure.csv"
BUNDLE_UNIT_CHECK_OUTPUT = cfg.TABLE_DIR / "main_final_bundle_return_unit_check.csv"
BUNDLE_LOAD_SUMMARY_OUTPUT = cfg.TABLE_DIR / "main_final_bundle_load_summary.csv"
BUNDLE_STRUCTURE_NOTE = cfg.DOCS_DIR / "main_final_bundle_structure_note.md"


# ============================================================
# 2. 기본 유틸
# ============================================================

def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")


def read_sheet(bundle_path: Path, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(bundle_path, sheet_name=sheet_name)


def normalize_first_column(df: pd.DataFrame, preferred_name: str) -> pd.DataFrame:
    """
    엑셀에서 index가 저장된 시트의 첫 컬럼명을 정리한다.

    예:
    Unnamed: 0 → year_month 또는 Date
    """
    out = df.copy()
    first_col = out.columns[0]

    if str(first_col).startswith("Unnamed"):
        out = out.rename(columns={first_col: preferred_name})
    elif first_col not in ["Date", "date", "year_month", "ticker"]:
        # 첫 컬럼이 월/날짜 인덱스 역할인 경우를 보정
        out = out.rename(columns={first_col: preferred_name})

    return out


def normalize_ticker_columns(df: pd.DataFrame, skip_cols: list[str]) -> pd.DataFrame:
    """
    티커 컬럼을 6자리 문자열로 통일한다.
    """
    out = df.copy()
    new_cols = []

    for col in out.columns:
        if col in skip_cols:
            new_cols.append(col)
        else:
            text = str(col)
            if text.isdigit():
                new_cols.append(text.zfill(6))
            else:
                new_cols.append(text)

    out.columns = new_cols
    return out


def normalize_monthly_wide(df: pd.DataFrame, index_name: str = "year_month") -> pd.DataFrame:
    """
    monthly_price, monthly_return_pct, monthly_return_decimal 같은 wide 시트 정리.
    """
    out = normalize_first_column(df, index_name)
    out[index_name] = out[index_name].astype(str)
    out = normalize_ticker_columns(out, skip_cols=[index_name])
    return out


def normalize_date_index_wide(df: pd.DataFrame, date_name: str = "Date") -> pd.DataFrame:
    """
    hsi_scaled_scores, hsi_direction, hsi_signal처럼 날짜 index가 포함된 wide 시트 정리.
    """
    out = normalize_first_column(df, date_name)
    out[date_name] = pd.to_datetime(out[date_name], errors="coerce")
    out[date_name] = out[date_name].dt.strftime("%Y-%m-%d")
    return out


def normalize_signal_inputs(df: pd.DataFrame) -> pd.DataFrame:
    """
    signal_inputs 시트 정리.
    """
    out = df.copy()

    if "Ticker" in out.columns and "ticker" not in out.columns:
        out = out.rename(columns={"Ticker": "ticker"})

    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

    if "ticker" in out.columns:
        out["ticker"] = out["ticker"].astype(str).str.zfill(6)

    return out


# ============================================================
# 3. 수익률 단위 점검
# ============================================================

def build_return_unit_check(monthly_pct: pd.DataFrame, monthly_decimal: pd.DataFrame) -> pd.DataFrame:
    """
    monthly_return_pct와 monthly_return_decimal의 단위 일관성 확인.

    기대 관계:
    monthly_return_decimal ≈ monthly_return_pct / 100
    """
    pct = monthly_pct.copy()
    dec = monthly_decimal.copy()

    pct = normalize_monthly_wide(pct)
    dec = normalize_monthly_wide(dec)

    tickers = [t for t in cfg.TICKERS if t in pct.columns and t in dec.columns]

    merged = pct[["year_month"] + tickers].merge(
        dec[["year_month"] + tickers],
        on="year_month",
        suffixes=("_pct", "_decimal"),
        how="inner",
    )

    rows = []

    for ticker in tickers:
        pct_col = f"{ticker}_pct"
        dec_col = f"{ticker}_decimal"

        expected_decimal = merged[pct_col] / 100.0
        actual_decimal = merged[dec_col]
        diff = actual_decimal - expected_decimal

        max_abs_diff = diff.abs().max()
        p95_abs_decimal = actual_decimal.abs().quantile(0.95)
        max_abs_decimal = actual_decimal.abs().max()

        status = "OK"
        note = "pct/100과 decimal이 일치한다."

        if pd.isna(max_abs_diff):
            status = "CHECK"
            note = "비교 가능한 값이 부족하다."
        elif max_abs_diff > 1e-6:
            status = "CHECK"
            note = "pct/100과 decimal 사이에 차이가 있다."
        elif max_abs_decimal > 1.0:
            status = "CHECK"
            note = "decimal 수익률의 절대값이 1을 초과한다. 단위 확인 필요."

        rows.append({
            "ticker": ticker,
            "name": cfg.TICKER_NAME_MAP.get(ticker, ""),
            "rows_compared": len(merged),
            "max_abs_decimal": float(max_abs_decimal),
            "p95_abs_decimal": float(p95_abs_decimal),
            "max_abs_diff_decimal_vs_pct_div_100": float(max_abs_diff),
            "status": status,
            "note": note,
        })

    return pd.DataFrame(rows)


# ============================================================
# 4. 요약표와 노트
# ============================================================

def build_load_summary(saved_outputs: dict[str, pd.DataFrame], unit_check: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for key, df in saved_outputs.items():
        rows.append({
            "item": key,
            "rows": len(df),
            "columns": len(df.columns),
            "output_path": str(PROCESSED_OUTPUTS.get(key, "")),
            "status": "OK",
            "note": "번들 시트 로드 후 CSV 저장",
        })

    unit_status = "OK" if (unit_check["status"] == "OK").all() else "CHECK"

    rows.append({
        "item": "return_unit_check",
        "rows": len(unit_check),
        "columns": len(unit_check.columns),
        "output_path": str(BUNDLE_UNIT_CHECK_OUTPUT),
        "status": unit_status,
        "note": "monthly_return_pct와 monthly_return_decimal 단위 일관성 확인",
    })

    return pd.DataFrame(rows)


def build_note(bundle_path: Path, load_summary: pd.DataFrame, unit_check: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_final 번들 구조 정리 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 기준 번들: `{bundle_path}`")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 단계는 데이터 담당 최종 산출물인 `hsi_data_bundle.xlsx`를 후속 실험에서 읽기 쉬운 "
        "CSV 기준 입력으로 분리하는 단계이다. 이 파일은 데이터를 다시 다운로드하거나 다시 계산하지 않는다."
    )
    lines.append("")
    lines.append("## 2. 수익률 단위")
    lines.append("")
    lines.append("- `monthly_return_pct`: 사람이 검토하기 쉬운 percent 단위")
    lines.append("- `monthly_return_decimal`: 백테스트 계산용 decimal 단위")
    lines.append("")
    lines.append("예시:")
    lines.append("")
    lines.append("```text")
    lines.append("2.5% → monthly_return_pct = 2.5")
    lines.append("2.5% → monthly_return_decimal = 0.025")
    lines.append("```")
    lines.append("")
    lines.append("## 3. 저장된 핵심 CSV")
    lines.append("")
    lines.append("| item | rows | columns | status | output_path |")
    lines.append("|---|---:|---:|---|---|")

    for _, row in load_summary.iterrows():
        lines.append(
            f"| {row['item']} | {row['rows']} | {row['columns']} | "
            f"{row['status']} | `{row['output_path']}` |"
        )

    lines.append("")
    lines.append("## 4. 수익률 단위 점검 결과")
    lines.append("")
    lines.append("| ticker | status | max_abs_decimal | max_abs_diff | note |")
    lines.append("|---|---|---:|---:|---|")

    for _, row in unit_check.iterrows():
        lines.append(
            f"| {row['ticker']} | {row['status']} | "
            f"{row['max_abs_decimal']:.6f} | "
            f"{row['max_abs_diff_decimal_vs_pct_div_100']:.10f} | "
            f"{row['note']} |"
        )

    lines.append("")
    lines.append("## 5. 다음 단계")
    lines.append("")
    lines.append(
        "다음 단계인 `02_build_hsi_event_balance_indicator.py`에서는 "
        "`main_final_signal_inputs.csv` 또는 `main_final_hsi_scaled_scores.csv`를 이용해 "
        "20/80 분위수 기반 사건균형·위험누적지표를 생성한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 5. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("01_load_bundle_and_make_structure_tables.py 실행 시작")
    print("=" * 80)

    print("[1] 최종 폴더 확인")
    cfg.ensure_final_directories()
    print("    OK")

    print("[2] hsi_data_bundle.xlsx 찾기")
    bundle_path = cfg.find_data_bundle()
    print(f"    OK: {bundle_path}")

    print("[3] 핵심 시트 로드 및 정리")

    saved_outputs = {}

    # 구조표
    input_structure = read_sheet(bundle_path, "input_structure")
    output_structure = read_sheet(bundle_path, "output_structure")

    save_csv(input_structure, INPUT_STRUCTURE_OUTPUT)
    save_csv(output_structure, OUTPUT_STRUCTURE_OUTPUT)

    print(f"    저장: {INPUT_STRUCTURE_OUTPUT}")
    print(f"    저장: {OUTPUT_STRUCTURE_OUTPUT}")

    # 핵심 실험 입력 시트
    asset_class = read_sheet(bundle_path, "asset_class")
    monthly_price = normalize_monthly_wide(read_sheet(bundle_path, "monthly_price"))
    monthly_return_pct = normalize_monthly_wide(read_sheet(bundle_path, "monthly_return_pct"))
    monthly_return_decimal = normalize_monthly_wide(read_sheet(bundle_path, "monthly_return_decimal"))
    signal_inputs = normalize_signal_inputs(read_sheet(bundle_path, "signal_inputs"))
    hsi_scaled_scores = normalize_date_index_wide(read_sheet(bundle_path, "hsi_scaled_scores"))
    hsi_direction = normalize_date_index_wide(read_sheet(bundle_path, "hsi_direction"))
    hsi_signal = normalize_date_index_wide(read_sheet(bundle_path, "hsi_signal"))
    signal_direction_map = read_sheet(bundle_path, "signal_direction_map")

    saved_outputs["asset_class"] = asset_class
    saved_outputs["monthly_price"] = monthly_price
    saved_outputs["monthly_return_decimal"] = monthly_return_decimal
    saved_outputs["monthly_return_pct"] = monthly_return_pct
    saved_outputs["signal_inputs"] = signal_inputs
    saved_outputs["hsi_scaled_scores"] = hsi_scaled_scores
    saved_outputs["hsi_direction"] = hsi_direction
    saved_outputs["hsi_signal"] = hsi_signal
    saved_outputs["signal_direction_map"] = signal_direction_map

    for key, df in saved_outputs.items():
        path = PROCESSED_OUTPUTS[key]
        save_csv(df, path)
        print(f"    저장: {path}  shape={df.shape}")

    print("[4] 수익률 단위 점검")
    unit_check = build_return_unit_check(monthly_return_pct, monthly_return_decimal)
    save_csv(unit_check, BUNDLE_UNIT_CHECK_OUTPUT)
    print(f"    저장: {BUNDLE_UNIT_CHECK_OUTPUT}")

    if not (unit_check["status"] == "OK").all():
        print("    CHECK: 수익률 단위 점검에서 확인 필요 항목이 있습니다.")
        print(unit_check.to_string(index=False))
    else:
        print("    OK: monthly_return_pct / 100 == monthly_return_decimal")

    print("[5] 로드 요약표 저장")
    load_summary = build_load_summary(saved_outputs, unit_check)
    save_csv(load_summary, BUNDLE_LOAD_SUMMARY_OUTPUT)
    print(f"    저장: {BUNDLE_LOAD_SUMMARY_OUTPUT}")

    print("[6] Markdown 노트 저장")
    note = build_note(bundle_path, load_summary, unit_check)
    BUNDLE_STRUCTURE_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {BUNDLE_STRUCTURE_NOTE}")

    print("\n[수익률 단위 점검]")
    print(unit_check.to_string(index=False))

    print("\n[로드 요약]")
    print(load_summary.to_string(index=False))

    print("\n[monthly_return_decimal 최근 5행]")
    print(monthly_return_decimal.tail().to_string(index=False))

    print("\n[signal_inputs 최근 5행]")
    print(signal_inputs.tail().to_string(index=False))

    print("=" * 80)
    print("01_load_bundle_and_make_structure_tables.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()