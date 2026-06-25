from pathlib import Path
import pandas as pd
import numpy as np


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_DIR / "data" / "raw" / "korea_etf.csv"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
OUTPUT_TABLE_DIR = PROJECT_DIR / "output" / "tables"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)


def read_csv_safely(path: Path) -> pd.DataFrame:
    """여러 인코딩을 순서대로 시도하여 CSV를 읽는다."""
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
    last_error = None

    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as error:
            last_error = error

    raise RuntimeError(f"CSV 파일을 읽지 못했습니다: {path}\n마지막 오류: {last_error}")


def normalize_ticker(col) -> str:
    """
    한국 ETF 종목코드를 6자리 문자열로 정리한다.
    예: 69500 -> 069500
    """
    text = str(col).strip()

    if text.lower().startswith("unnamed"):
        return text

    # 69500.0처럼 읽힌 경우 처리
    if text.endswith(".0"):
        text = text[:-2]

    if text.isdigit() and len(text) <= 6:
        return text.zfill(6)

    return text


def detect_date_column(df: pd.DataFrame) -> str:
    """
    날짜 컬럼을 찾는다.
    보통 첫 번째 컬럼이 날짜이거나 Date라는 이름을 가진다.
    """
    for col in df.columns:
        if str(col).strip().lower() in ["date", "datetime", "날짜"]:
            return col

    return df.columns[0]


def main() -> None:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"원본 파일이 없습니다: {RAW_PATH}")

    raw = read_csv_safely(RAW_PATH)

    date_col = detect_date_column(raw)
    raw[date_col] = pd.to_datetime(raw[date_col], errors="coerce")
    raw = raw.dropna(subset=[date_col]).copy()
    raw = raw.sort_values(date_col).set_index(date_col)

    raw.columns = [normalize_ticker(c) for c in raw.columns]

    price = raw.apply(pd.to_numeric, errors="coerce")
    price = price.sort_index()

    quality_rows = []

    for ticker in price.columns:
        s = price[ticker]
        valid = s.dropna()

        first_valid = valid.index.min() if not valid.empty else pd.NaT
        last_valid = valid.index.max() if not valid.empty else pd.NaT
        missing_count = int(s.isna().sum())
        valid_count = int(s.notna().sum())
        missing_ratio = float(s.isna().mean())

        use_candidate = (
            valid_count >= 252 and
            missing_ratio <= 0.50
        )

        quality_rows.append({
            "Ticker": ticker,
            "FirstValidDate": first_valid.date().isoformat() if pd.notna(first_valid) else "",
            "LastValidDate": last_valid.date().isoformat() if pd.notna(last_valid) else "",
            "ValidCount": valid_count,
            "MissingCount": missing_count,
            "MissingRatio": round(missing_ratio, 4),
            "UseCandidate": use_candidate
        })

    quality = pd.DataFrame(quality_rows)

    candidate_tickers = quality.loc[quality["UseCandidate"], "Ticker"].tolist()

    if candidate_tickers:
        common_start = price[candidate_tickers].dropna().index.min()
        common_end = price[candidate_tickers].dropna().index.max()
        common_rows = len(price[candidate_tickers].dropna())
    else:
        common_start = pd.NaT
        common_end = pd.NaT
        common_rows = 0

    summary = pd.DataFrame([{
        "RawPath": str(RAW_PATH),
        "TotalRows": len(price),
        "TotalAssets": price.shape[1],
        "CandidateAssets": len(candidate_tickers),
        "CommonStartDate": common_start.date().isoformat() if pd.notna(common_start) else "",
        "CommonEndDate": common_end.date().isoformat() if pd.notna(common_end) else "",
        "CommonRowsAfterDropNA": common_rows
    }])

    price.to_csv(PROCESSED_DIR / "korea_etf_price_clean.csv", encoding="utf-8-sig")
    quality.to_csv(OUTPUT_TABLE_DIR / "korea_etf_data_quality.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTPUT_TABLE_DIR / "korea_etf_data_summary.csv", index=False, encoding="utf-8-sig")

    print("[완료] 한국 ETF 데이터 품질 점검")
    print(f"- 원본 파일: {RAW_PATH}")
    print(f"- 전체 행 수: {len(price)}")
    print(f"- 전체 자산 수: {price.shape[1]}")
    print(f"- 사용 후보 자산 수: {len(candidate_tickers)}")
    print(f"- 공통 기간 시작일: {summary.loc[0, 'CommonStartDate']}")
    print(f"- 공통 기간 종료일: {summary.loc[0, 'CommonEndDate']}")
    print(f"- 공통 기간 행 수: {common_rows}")
    print()
    print("[생성 파일]")
    print(f"- {PROCESSED_DIR / 'korea_etf_price_clean.csv'}")
    print(f"- {OUTPUT_TABLE_DIR / 'korea_etf_data_quality.csv'}")
    print(f"- {OUTPUT_TABLE_DIR / 'korea_etf_data_summary.csv'}")


if __name__ == "__main__":
    main()
