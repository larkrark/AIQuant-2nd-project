"""
13_flex_align_hsi_with_returns.py

목적
----
월말 HSI 상태와 다음 달 월간 수익률을 정렬한다.

현재 HSI는 월말 상태로 정리되어 있고,
수익률은 월간 수익률로 저장되어 있다.

백테스트에서는 같은 달의 HSI와 같은 달의 수익률을 바로 연결하면 안 된다.
월말에 확인한 HSI 상태는 다음 달 투자 비중에 반영되어야 하므로,
t월 말 HSI 상태를 t+1월 수익률에 연결한다.

입력 파일
---------
data/processed/monthly_returns.csv
output/tables/flex_hsi_monthly_state_rank.csv
output/tables/flex_hsi_monthly_state_zscore.csv

출력 파일
---------
output/tables/flex_hsi_return_alignment_rank.csv
output/tables/flex_hsi_return_alignment_zscore.csv
output/tables/flex_hsi_return_alignment_check.csv
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

MONTHLY_RETURNS_PATH = PROCESSED_DIR / "monthly_returns.csv"

HSI_MONTHLY_RANK_PATH = TABLE_DIR / "flex_hsi_monthly_state_rank.csv"
HSI_MONTHLY_ZSCORE_PATH = TABLE_DIR / "flex_hsi_monthly_state_zscore.csv"


# ============================================================
# 3. 출력 파일 경로
# ============================================================

ALIGN_RANK_PATH = TABLE_DIR / "flex_hsi_return_alignment_rank.csv"
ALIGN_ZSCORE_PATH = TABLE_DIR / "flex_hsi_return_alignment_zscore.csv"
ALIGN_CHECK_PATH = TABLE_DIR / "flex_hsi_return_alignment_check.csv"


# ============================================================
# 4. 공통 함수
# ============================================================

def read_csv_with_date(path: Path) -> pd.DataFrame:
    """
    Date 컬럼을 날짜형 인덱스로 읽어오는 함수.
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


def get_tickers_from_returns(monthly_returns: pd.DataFrame) -> list[str]:
    """
    monthly_returns.csv의 컬럼명을 ETF 티커 목록으로 사용한다.
    """
    return monthly_returns.columns.tolist()


def align_hsi_with_next_month_returns(
    monthly_hsi: pd.DataFrame,
    monthly_returns: pd.DataFrame,
    method_name: str,
) -> pd.DataFrame:
    """
    t월 말 HSI 상태를 t+1월 월간 수익률과 연결한다.

    핵심 처리
    --------
    - monthly_hsi의 Date는 signal_date로 사용한다.
    - monthly_returns의 Date는 return_date로 사용한다.
    - 각 signal_date의 다음 월 return_date를 찾아 연결한다.

    예:
    2026-05-31 HSI 상태 → 2026-06-30 수익률
    """
    hsi = monthly_hsi.copy()
    returns = monthly_returns.copy()

    hsi.index.name = "signal_date"
    returns.index.name = "return_date"

    # 수익률 컬럼에는 _return 접미사 부여
    returns_for_join = returns.add_suffix("_return")

    # HSI를 한 달 뒤 수익률에 연결하기 위해
    # HSI 인덱스를 다음 달 월말 라벨로 이동시킨다.
    hsi_for_join = hsi.copy()

    try:
        hsi_for_join.index = hsi_for_join.index + pd.offsets.MonthEnd(1)
    except Exception as exc:
        raise RuntimeError("HSI 날짜를 다음 월말로 이동하는 중 오류가 발생했습니다.") from exc

    hsi_for_join.index.name = "return_date"

    aligned = hsi_for_join.join(returns_for_join, how="inner")

    aligned = aligned.reset_index()
    aligned = aligned.rename(columns={"return_date": "Date"})

    # 원래 HSI가 어느 날짜에서 온 것인지도 남긴다.
    aligned.insert(
        1,
        "signal_date",
        aligned["Date"] - pd.offsets.MonthEnd(1),
    )

    aligned.insert(2, "method", method_name)

    return aligned


def make_alignment_check(
    aligned_rank: pd.DataFrame,
    aligned_zscore: pd.DataFrame,
    monthly_returns: pd.DataFrame,
) -> pd.DataFrame:
    """
    정렬 결과가 정상인지 확인하는 요약표를 만든다.
    """
    rows = []

    for method_name, aligned in [
        ("rank", aligned_rank),
        ("zscore", aligned_zscore),
    ]:
        return_cols = [col for col in aligned.columns if col.endswith("_return")]
        signal_cols = [col for col in aligned.columns if col.endswith("_signal")]

        rows.append({
            "method": method_name,
            "aligned_rows": aligned.shape[0],
            "aligned_columns": aligned.shape[1],
            "start_return_date": aligned["Date"].min(),
            "end_return_date": aligned["Date"].max(),
            "signal_column_count": len(signal_cols),
            "return_column_count": len(return_cols),
            "missing_return_cells": int(aligned[return_cols].isna().sum().sum()) if return_cols else None,
            "missing_signal_cells": int(aligned[signal_cols].isna().sum().sum()) if signal_cols else None,
        })

    rows.append({
        "method": "monthly_returns_raw",
        "aligned_rows": monthly_returns.shape[0],
        "aligned_columns": monthly_returns.shape[1],
        "start_return_date": monthly_returns.index.min(),
        "end_return_date": monthly_returns.index.max(),
        "signal_column_count": None,
        "return_column_count": monthly_returns.shape[1],
        "missing_return_cells": int(monthly_returns.isna().sum().sum()),
        "missing_signal_cells": None,
    })

    return pd.DataFrame(rows)


# ============================================================
# 5. 메인 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("13_flex_align_hsi_with_returns.py 실행 시작")
    print("=" * 70)

    # --------------------------------------------------------
    # 데이터 읽기
    # --------------------------------------------------------
    monthly_returns = read_csv_with_date(MONTHLY_RETURNS_PATH)
    hsi_rank_monthly = read_csv_with_date(HSI_MONTHLY_RANK_PATH)
    hsi_zscore_monthly = read_csv_with_date(HSI_MONTHLY_ZSCORE_PATH)

    tickers = get_tickers_from_returns(monthly_returns)

    print("[로드 완료]")
    print(f"- monthly_returns: {monthly_returns.shape}")
    print(f"- hsi_rank_monthly: {hsi_rank_monthly.shape}")
    print(f"- hsi_zscore_monthly: {hsi_zscore_monthly.shape}")
    print(f"- tickers: {tickers}")

    # --------------------------------------------------------
    # HSI → 다음 달 수익률 연결
    # --------------------------------------------------------
    aligned_rank = align_hsi_with_next_month_returns(
        monthly_hsi=hsi_rank_monthly,
        monthly_returns=monthly_returns,
        method_name="rank",
    )

    aligned_zscore = align_hsi_with_next_month_returns(
        monthly_hsi=hsi_zscore_monthly,
        monthly_returns=monthly_returns,
        method_name="zscore",
    )

    print()
    print("[정렬 완료]")
    print(f"- aligned_rank: {aligned_rank.shape}")
    print(f"- aligned_zscore: {aligned_zscore.shape}")

    # --------------------------------------------------------
    # 정렬 점검표
    # --------------------------------------------------------
    alignment_check = make_alignment_check(
        aligned_rank=aligned_rank,
        aligned_zscore=aligned_zscore,
        monthly_returns=monthly_returns,
    )

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------
    aligned_rank.to_csv(
        ALIGN_RANK_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    aligned_zscore.to_csv(
        ALIGN_ZSCORE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    alignment_check.to_csv(
        ALIGN_CHECK_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("[저장 완료]")
    print(f"- {ALIGN_RANK_PATH}")
    print(f"- {ALIGN_ZSCORE_PATH}")
    print(f"- {ALIGN_CHECK_PATH}")

    print()
    print("[정렬 점검 요약]")
    print(alignment_check)

    print()
    print("[미리보기 - rank]")
    print(aligned_rank.head())

    print()
    print("=" * 70)
    print("13_flex_align_hsi_with_returns.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()