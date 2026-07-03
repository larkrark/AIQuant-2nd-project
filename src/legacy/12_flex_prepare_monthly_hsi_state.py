"""
12_flex_prepare_monthly_hsi_state.py

목적
----
일별 HSI 결과를 월말 HSI 상태로 변환한다.

현재 hsi_summary_rank.csv와 hsi_summary_zscore.csv는 일별 HSI 신호이다.
하지만 이후 백테스트는 monthly_returns.csv를 사용하는 월별 구조이므로,
일별 HSI 중 각 월의 마지막 관측값을 추출해 월말 HSI 상태표를 만든다.

이 파일은 최종 전략 성과를 계산하는 코드가 아니다.
일별 HSI와 월별 수익률을 연결하기 위한 flex 파이프라인의 두 번째 준비 코드이다.

입력 파일
---------
output/tables/hsi_summary_rank.csv
output/tables/hsi_summary_zscore.csv

출력 파일
---------
output/tables/flex_hsi_monthly_state_rank.csv
output/tables/flex_hsi_monthly_state_zscore.csv
output/tables/flex_hsi_monthly_state_compare.csv
"""

from pathlib import Path

import pandas as pd


# ============================================================
# 1. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "output"
TABLE_DIR = OUTPUT_DIR / "tables"

TABLE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. 입력 파일 경로
# ============================================================

HSI_RANK_PATH = TABLE_DIR / "hsi_summary_rank.csv"
HSI_ZSCORE_PATH = TABLE_DIR / "hsi_summary_zscore.csv"


# ============================================================
# 3. 출력 파일 경로
# ============================================================

FLEX_MONTHLY_RANK_PATH = TABLE_DIR / "flex_hsi_monthly_state_rank.csv"
FLEX_MONTHLY_ZSCORE_PATH = TABLE_DIR / "flex_hsi_monthly_state_zscore.csv"
FLEX_MONTHLY_COMPARE_PATH = TABLE_DIR / "flex_hsi_monthly_state_compare.csv"


# ============================================================
# 4. 공통 함수
# ============================================================

def read_hsi_summary(path: Path) -> pd.DataFrame:
    """
    HSI summary CSV를 Date 인덱스로 읽는다.

    Parameters
    ----------
    path : Path
        HSI summary CSV 경로

    Returns
    -------
    pd.DataFrame
        Date를 DatetimeIndex로 가진 HSI 데이터프레임
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


def make_monthly_hsi_state(daily_hsi: pd.DataFrame) -> pd.DataFrame:
    """
    일별 HSI 결과에서 월말 HSI 상태를 추출한다.

    월말 날짜 라벨을 사용하지만,
    실제 값은 해당 월의 마지막 관측일 HSI 값을 사용한다.

    예:
    2026-06-30 라벨이 붙더라도,
    실제 마지막 관측일이 2026-06-26이면 2026-06-26의 HSI 값을 사용한다.
    """
    try:
        monthly_hsi = daily_hsi.resample("ME").last()
    except ValueError:
        monthly_hsi = daily_hsi.resample("M").last()

    monthly_hsi = monthly_hsi.reset_index()

    return monthly_hsi


def extract_signal_columns(df: pd.DataFrame) -> list[str]:
    """
    HSI 결과에서 signal 컬럼만 추출한다.
    """
    return [col for col in df.columns if col.endswith("_signal")]


def make_signal_compare(
    monthly_rank: pd.DataFrame,
    monthly_zscore: pd.DataFrame,
) -> pd.DataFrame:
    """
    분위수 방식과 z-score 방식의 월말 signal을 비교한다.

    각 ETF별 signal이 같은지 여부를 확인해,
    두 점수화 방식이 월말 상태 판단에서 얼마나 비슷한지 점검한다.
    """
    rank = monthly_rank.copy()
    zscore = monthly_zscore.copy()

    rank["Date"] = pd.to_datetime(rank["Date"])
    zscore["Date"] = pd.to_datetime(zscore["Date"])

    rank_signal_cols = extract_signal_columns(rank)
    zscore_signal_cols = extract_signal_columns(zscore)

    common_signal_cols = sorted(set(rank_signal_cols).intersection(zscore_signal_cols))

    compare = pd.DataFrame({"Date": rank["Date"]})

    for col in common_signal_cols:
        rank_col = f"{col}_rank"
        zscore_col = f"{col}_zscore"
        same_col = f"{col}_same"

        compare[rank_col] = rank[col].values
        compare[zscore_col] = zscore[col].values
        compare[same_col] = compare[rank_col] == compare[zscore_col]

    if common_signal_cols:
        same_cols = [f"{col}_same" for col in common_signal_cols]
        compare["same_signal_count"] = compare[same_cols].sum(axis=1)
        compare["total_signal_count"] = len(common_signal_cols)
        compare["same_signal_ratio"] = (
            compare["same_signal_count"] / compare["total_signal_count"]
        )
    else:
        compare["same_signal_count"] = 0
        compare["total_signal_count"] = 0
        compare["same_signal_ratio"] = None

    return compare


def summarize_monthly_hsi(monthly_hsi: pd.DataFrame, method_name: str) -> pd.DataFrame:
    """
    월말 HSI 상태표의 간단한 요약 정보를 만든다.
    콘솔 확인용이다.
    """
    signal_cols = extract_signal_columns(monthly_hsi)

    rows = []

    for col in signal_cols:
        value_counts = monthly_hsi[col].value_counts(dropna=False)

        for signal, count in value_counts.items():
            rows.append({
                "method": method_name,
                "signal_column": col,
                "signal": signal,
                "count": count,
            })

    return pd.DataFrame(rows)


# ============================================================
# 5. 메인 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("12_flex_prepare_monthly_hsi_state.py 실행 시작")
    print("=" * 70)

    # --------------------------------------------------------
    # 일별 HSI 읽기
    # --------------------------------------------------------
    hsi_rank_daily = read_hsi_summary(HSI_RANK_PATH)
    hsi_zscore_daily = read_hsi_summary(HSI_ZSCORE_PATH)

    print("[로드 완료]")
    print(f"- hsi_summary_rank: {hsi_rank_daily.shape}")
    print(f"- hsi_summary_zscore: {hsi_zscore_daily.shape}")

    # --------------------------------------------------------
    # 월말 HSI 상태 추출
    # --------------------------------------------------------
    hsi_rank_monthly = make_monthly_hsi_state(hsi_rank_daily)
    hsi_zscore_monthly = make_monthly_hsi_state(hsi_zscore_daily)

    print()
    print("[월말 HSI 변환 완료]")
    print(f"- rank monthly: {hsi_rank_monthly.shape}")
    print(f"- zscore monthly: {hsi_zscore_monthly.shape}")

    # --------------------------------------------------------
    # rank / zscore signal 비교
    # --------------------------------------------------------
    hsi_monthly_compare = make_signal_compare(
        monthly_rank=hsi_rank_monthly,
        monthly_zscore=hsi_zscore_monthly,
    )

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------
    hsi_rank_monthly.to_csv(
        FLEX_MONTHLY_RANK_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    hsi_zscore_monthly.to_csv(
        FLEX_MONTHLY_ZSCORE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    hsi_monthly_compare.to_csv(
        FLEX_MONTHLY_COMPARE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("[저장 완료]")
    print(f"- {FLEX_MONTHLY_RANK_PATH}")
    print(f"- {FLEX_MONTHLY_ZSCORE_PATH}")
    print(f"- {FLEX_MONTHLY_COMPARE_PATH}")

    # --------------------------------------------------------
    # 콘솔 요약 출력
    # --------------------------------------------------------
    rank_summary = summarize_monthly_hsi(hsi_rank_monthly, "rank")
    zscore_summary = summarize_monthly_hsi(hsi_zscore_monthly, "zscore")

    print()
    print("[월말 signal 요약 - rank]")
    print(rank_summary)

    print()
    print("[월말 signal 요약 - zscore]")
    print(zscore_summary)

    print()
    print("[rank / zscore 월말 signal 일치율 요약]")
    if "same_signal_ratio" in hsi_monthly_compare.columns:
        print(hsi_monthly_compare["same_signal_ratio"].describe())
    else:
        print("signal 비교 컬럼이 없습니다.")

    print()
    print("=" * 70)
    print("12_flex_prepare_monthly_hsi_state.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()