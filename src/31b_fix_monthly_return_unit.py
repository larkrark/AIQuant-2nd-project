from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_TABLE_DIR = PROJECT_ROOT / "output" / "tables"

DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)


# 입력 후보
INPUT_CANDIDATES = [
    DATA_PROCESSED_DIR / "monthly_return.csv",
    DATA_PROCESSED_DIR / "monthly_returns_pct.csv",
    DATA_PROCESSED_DIR / "monthly_returns.csv",
    OUTPUT_TABLE_DIR / "monthly_return.csv",
    OUTPUT_TABLE_DIR / "monthly_returns.csv",
]

OUTPUT_DECIMAL_PATH = DATA_PROCESSED_DIR / "monthly_returns.csv"
OUTPUT_PCT_PATH = DATA_PROCESSED_DIR / "monthly_returns_pct.csv"
CHECK_PATH = OUTPUT_TABLE_DIR / "monthly_return_unit_check.csv"


def find_existing_input() -> Path:
    for path in INPUT_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError(
        "monthly_return 또는 monthly_returns 파일을 찾지 못했습니다. "
        "data/processed 또는 output/tables 위치를 확인하세요."
    )


def read_monthly_returns(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")

    # 첫 컬럼이 날짜/연월인 경우 처리
    first_col = df.columns[0]
    if first_col.lower() in ["date", "year_month", "month"]:
        df = df.rename(columns={first_col: "Date"})
        df["Date"] = df["Date"].astype(str)
        df = df.set_index("Date")
    else:
        df = df.set_index(first_col)

    # 티커 컬럼을 문자열 6자리로 정리
    df.columns = [str(col).zfill(6) for col in df.columns]

    # 숫자 변환
    df = df.apply(pd.to_numeric, errors="coerce")

    return df


def infer_unit(df: pd.DataFrame) -> str:
    """
    월간 수익률 단위를 추정한다.

    대략적인 기준:
    - 절대값이 1보다 큰 값이 자주 있으면 percent 가능성이 큼
    - 모든 값이 -1~1 근처면 decimal 가능성이 큼

    단, ETF 월간 수익률이 100%를 넘는 특수 상황은 거의 없다고 가정한다.
    """
    values = df.stack().dropna()

    if values.empty:
        raise ValueError("수익률 데이터가 비어 있습니다.")

    max_abs = values.abs().max()
    p95_abs = values.abs().quantile(0.95)

    if max_abs > 1.0 or p95_abs > 0.5:
        return "percent"

    return "decimal"


def main() -> None:
    input_path = find_existing_input()
    monthly = read_monthly_returns(input_path)

    detected_unit = infer_unit(monthly)

    if detected_unit == "percent":
        monthly_pct = monthly.copy()
        monthly_decimal = monthly / 100.0
    else:
        monthly_decimal = monthly.copy()
        monthly_pct = monthly * 100.0

    monthly_decimal.to_csv(OUTPUT_DECIMAL_PATH, encoding="utf-8-sig")
    monthly_pct.to_csv(OUTPUT_PCT_PATH, encoding="utf-8-sig")

    check = pd.DataFrame([
        {
            "input_file": str(input_path),
            "detected_unit": detected_unit,
            "decimal_output": str(OUTPUT_DECIMAL_PATH),
            "percent_backup_output": str(OUTPUT_PCT_PATH),
            "max_abs_input": float(monthly.stack().dropna().abs().max()),
            "p95_abs_input": float(monthly.stack().dropna().abs().quantile(0.95)),
            "note": "monthly_returns.csv는 백테스트용 decimal 단위로 저장했습니다.",
        }
    ])

    check.to_csv(CHECK_PATH, index=False, encoding="utf-8-sig")

    print("=" * 80)
    print("31b_fix_monthly_return_unit.py")
    print("=" * 80)
    print(f"[입력 파일] {input_path}")
    print(f"[추정 단위] {detected_unit}")
    print(f"[저장] decimal: {OUTPUT_DECIMAL_PATH}")
    print(f"[저장] percent backup: {OUTPUT_PCT_PATH}")
    print(f"[점검표] {CHECK_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    main()