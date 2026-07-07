"""
CSV 입출력 유틸리티.

엄격형(Date 필수)/관대형(있으면 파싱, signal_date도 파싱) 로더를 하나로 통합.
"""

from pathlib import Path

import pandas as pd


def read_csv_with_date(
    path: Path,
    *,
    require_date: bool = False,
    parse_signal_date: bool = True,
) -> pd.DataFrame:
    """
    CSV를 읽고 날짜 컬럼을 datetime으로 파싱한다.

    require_date=True 이면 Date 없을 때 ValueError(엄격형 동작).
    parse_signal_date=True 이고 signal_date 있으면 파싱(관대형 동작).
    """
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    df = pd.read_csv(path)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
    elif require_date:
        raise ValueError(f"Date 컬럼이 없습니다: {path}")

    if parse_signal_date and "signal_date" in df.columns:
        df["signal_date"] = pd.to_datetime(df["signal_date"])

    return df


def save_table(df: pd.DataFrame, path: Path) -> None:
    """표를 프로젝트 표준(utf-8-sig, index 미포함)으로 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
