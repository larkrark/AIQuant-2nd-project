"""
11_flex_check_data_quality.py

목적
----
현재 확보된 예비 산출물을 이용해 데이터 품질을 점검한다.

이 파일은 최종 전략 성과를 계산하는 코드가 아니다.
가격 데이터와 월간 수익률 데이터가 백테스트에 연결 가능한 상태인지
확인하기 위한 flex 파이프라인의 첫 번째 점검 코드이다.

입력 파일
---------
data/processed/daily_prices.csv
data/processed/monthly_prices.csv
data/processed/monthly_returns.csv
output/tables/selected_etf_universe.csv

출력 파일
---------
output/tables/flex_data_quality_summary.csv
output/tables/flex_missing_value_check.csv
output/tables/flex_available_period_check.csv
output/tables/flex_monthly_return_check.csv
output/tables/flex_asset_group_count.csv
"""

from pathlib import Path

import pandas as pd


# ============================================================
# 1. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"

OUTPUT_DIR = PROJECT_ROOT / "output"
TABLE_DIR = OUTPUT_DIR / "tables"

TABLE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. 입력 파일 경로
# ============================================================

DAILY_PRICES_PATH = PROCESSED_DIR / "daily_prices.csv"
MONTHLY_PRICES_PATH = PROCESSED_DIR / "monthly_prices.csv"
MONTHLY_RETURNS_PATH = PROCESSED_DIR / "monthly_returns.csv"
SELECTED_ETF_PATH = TABLE_DIR / "selected_etf_universe.csv"


# ============================================================
# 3. 공통 함수
# ============================================================

def read_csv_with_date(path: Path) -> pd.DataFrame:
    """
    Date 컬럼을 날짜형 인덱스로 읽어오는 함수.

    Parameters
    ----------
    path : Path
        읽어올 CSV 파일 경로

    Returns
    -------
    pd.DataFrame
        Date를 DatetimeIndex로 가진 데이터프레임
    """
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    df = pd.read_csv(path)

    if "Date" not in df.columns:
        raise ValueError(f"Date 컬럼이 없습니다: {path}")

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")
    df = df.sort_index()

    return df


def check_basic_quality(df: pd.DataFrame, dataset_name: str) -> dict:
    """
    데이터프레임 단위의 기본 품질 정보를 계산한다.
    """
    is_date_sorted = df.index.is_monotonic_increasing
    has_duplicate_dates = df.index.duplicated().any()

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    non_numeric_columns = [col for col in df.columns if col not in numeric_columns]

    total_cells = df.shape[0] * df.shape[1]
    missing_cells = int(df.isna().sum().sum())
    missing_ratio = missing_cells / total_cells if total_cells > 0 else 0

    return {
        "dataset": dataset_name,
        "rows": df.shape[0],
        "columns": df.shape[1],
        "start_date": df.index.min(),
        "end_date": df.index.max(),
        "is_date_sorted": is_date_sorted,
        "has_duplicate_dates": has_duplicate_dates,
        "numeric_column_count": len(numeric_columns),
        "non_numeric_column_count": len(non_numeric_columns),
        "non_numeric_columns": ", ".join(non_numeric_columns),
        "missing_cells": missing_cells,
        "missing_ratio": missing_ratio,
    }


def make_missing_value_check(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """
    컬럼별 결측치 개수와 비율을 계산한다.
    """
    result = pd.DataFrame({
        "dataset": dataset_name,
        "column": df.columns,
        "missing_count": df.isna().sum().values,
        "missing_ratio": df.isna().mean().values,
    })

    return result


def make_available_period_check(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """
    ETF별 사용 가능 기간과 관측치 수를 계산한다.
    """
    rows = []

    for col in df.columns:
        valid = df[col].dropna()

        if valid.empty:
            rows.append({
                "dataset": dataset_name,
                "ticker": col,
                "start_date": pd.NaT,
                "end_date": pd.NaT,
                "observation_count": 0,
                "missing_count": int(df[col].isna().sum()),
                "missing_ratio": float(df[col].isna().mean()),
            })
        else:
            rows.append({
                "dataset": dataset_name,
                "ticker": col,
                "start_date": valid.index.min(),
                "end_date": valid.index.max(),
                "observation_count": valid.shape[0],
                "missing_count": int(df[col].isna().sum()),
                "missing_ratio": float(df[col].isna().mean()),
            })

    return pd.DataFrame(rows)


def make_monthly_return_check(monthly_returns: pd.DataFrame) -> pd.DataFrame:
    """
    월간 수익률의 기초 통계와 이상치 후보를 점검한다.

    여기서 extreme_abs_return_count는 절대수익률 30% 초과 월의 개수이다.
    예비 점검 기준이며, 최종 이상치 판단은 별도 해석이 필요하다.
    """
    rows = []

    for col in monthly_returns.columns:
        s = monthly_returns[col].dropna()

        if s.empty:
            rows.append({
                "ticker": col,
                "count": 0,
                "mean_return": None,
                "std_return": None,
                "min_return": None,
                "max_return": None,
                "extreme_abs_return_count": None,
            })
            continue

        rows.append({
            "ticker": col,
            "count": s.shape[0],
            "mean_return": s.mean(),
            "std_return": s.std(),
            "min_return": s.min(),
            "max_return": s.max(),
            "extreme_abs_return_count": int((s.abs() > 0.30).sum()),
        })

    return pd.DataFrame(rows)


def make_asset_group_count(selected_etf_path: Path) -> pd.DataFrame:
    """
    selected_etf_universe.csv가 있을 경우 자산군별 ETF 수를 계산한다.

    파일이나 컬럼 구조가 다를 수 있으므로, 가능한 컬럼을 유연하게 탐색한다.
    """
    if not selected_etf_path.exists():
        return pd.DataFrame({
            "message": ["selected_etf_universe.csv 파일이 없어 자산군별 개수를 계산하지 못했습니다."]
        })

    selected = pd.read_csv(selected_etf_path)

    possible_group_cols = [
        "asset_class",
        "risk_group",
        "role",
        "category",
        "type",
    ]

    group_col = None
    for col in possible_group_cols:
        if col in selected.columns:
            group_col = col
            break

    if group_col is None:
        return pd.DataFrame({
            "message": ["자산군 분류 컬럼을 찾지 못했습니다."],
            "available_columns": [", ".join(selected.columns)],
        })

    result = (
        selected.groupby(group_col)
        .size()
        .reset_index(name="etf_count")
        .rename(columns={group_col: "group"})
    )

    result.insert(0, "group_column_used", group_col)

    return result


# ============================================================
# 4. 메인 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("11_flex_check_data_quality.py 실행 시작")
    print("=" * 70)

    # --------------------------------------------------------
    # 데이터 읽기
    # --------------------------------------------------------
    daily_prices = read_csv_with_date(DAILY_PRICES_PATH)
    monthly_prices = read_csv_with_date(MONTHLY_PRICES_PATH)
    monthly_returns = read_csv_with_date(MONTHLY_RETURNS_PATH)

    print("[로드 완료]")
    print(f"- daily_prices: {daily_prices.shape}")
    print(f"- monthly_prices: {monthly_prices.shape}")
    print(f"- monthly_returns: {monthly_returns.shape}")

    # --------------------------------------------------------
    # 기본 품질 요약
    # --------------------------------------------------------
    quality_summary = pd.DataFrame([
        check_basic_quality(daily_prices, "daily_prices"),
        check_basic_quality(monthly_prices, "monthly_prices"),
        check_basic_quality(monthly_returns, "monthly_returns"),
    ])

    # --------------------------------------------------------
    # 결측치 점검
    # --------------------------------------------------------
    missing_value_check = pd.concat([
        make_missing_value_check(daily_prices, "daily_prices"),
        make_missing_value_check(monthly_prices, "monthly_prices"),
        make_missing_value_check(monthly_returns, "monthly_returns"),
    ], ignore_index=True)

    # --------------------------------------------------------
    # 사용 가능 기간 점검
    # --------------------------------------------------------
    available_period_check = pd.concat([
        make_available_period_check(daily_prices, "daily_prices"),
        make_available_period_check(monthly_prices, "monthly_prices"),
        make_available_period_check(monthly_returns, "monthly_returns"),
    ], ignore_index=True)

    # --------------------------------------------------------
    # 월간 수익률 점검
    # --------------------------------------------------------
    monthly_return_check = make_monthly_return_check(monthly_returns)

    # --------------------------------------------------------
    # 자산군 개수 점검
    # --------------------------------------------------------
    asset_group_count = make_asset_group_count(SELECTED_ETF_PATH)

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------
    quality_summary.to_csv(
        TABLE_DIR / "flex_data_quality_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    missing_value_check.to_csv(
        TABLE_DIR / "flex_missing_value_check.csv",
        index=False,
        encoding="utf-8-sig",
    )

    available_period_check.to_csv(
        TABLE_DIR / "flex_available_period_check.csv",
        index=False,
        encoding="utf-8-sig",
    )

    monthly_return_check.to_csv(
        TABLE_DIR / "flex_monthly_return_check.csv",
        index=False,
        encoding="utf-8-sig",
    )

    asset_group_count.to_csv(
        TABLE_DIR / "flex_asset_group_count.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # 콘솔 요약 출력
    # --------------------------------------------------------
    print()
    print("[저장 완료]")
    print(f"- {TABLE_DIR / 'flex_data_quality_summary.csv'}")
    print(f"- {TABLE_DIR / 'flex_missing_value_check.csv'}")
    print(f"- {TABLE_DIR / 'flex_available_period_check.csv'}")
    print(f"- {TABLE_DIR / 'flex_monthly_return_check.csv'}")
    print(f"- {TABLE_DIR / 'flex_asset_group_count.csv'}")

    print()
    print("[품질 요약]")
    print(quality_summary)

    print()
    print("=" * 70)
    print("11_flex_check_data_quality.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()


