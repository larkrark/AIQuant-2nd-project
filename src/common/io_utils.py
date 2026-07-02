"""
CSV 입출력 유틸리티.

기존에 파일마다 복제되어 있던 두 종류의 `read_csv_with_date`
(엄격형: Date 없으면 raise / 관대형: 있으면 파싱, signal_date도 파싱)를
하나의 함수로 통합한다.
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

    Parameters
    ----------
    path : Path
        읽을 CSV 경로.
    require_date : bool, default False
        True이면 `Date` 컬럼이 없을 때 ValueError를 발생시킨다.
        (기존 엄격형 로더 동작)
    parse_signal_date : bool, default True
        True이고 `signal_date` 컬럼이 있으면 datetime으로 파싱한다.
        (기존 관대형 로더 동작)

    Notes
    -----
    - 기존 엄격형 호출부(17/19/25/26/27 등)는
      `require_date=True, parse_signal_date=False`로 동작을 그대로 재현한다.
    - 기존 관대형 호출부(18/20/21 등)는 기본 인자로 동작을 그대로 재현한다.
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
