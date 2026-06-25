from pathlib import Path
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_DIR / "output" / "tables"

DESIGN_START = "2014-03"
DESIGN_END = "2022-12"
VALIDATION_START = "2023-01"
VALIDATION_END = "2026-06"


INPUT_FILES = [
    "monthly_hsi_state_labels.csv",
    "monthly_wave_features.csv",
    "monthly_wave_market_summary.csv",
    "monthly_event_counts.csv",
]


def read_csv_safely(path: Path) -> pd.DataFrame:
    """
    CSV 파일을 안전하게 읽는다.

    파일이 없거나 비어 있으면 바로 오류를 발생시켜,
    이후 단계에서 빈 결과가 조용히 생성되는 문제를 막는다.
    """
    if not path.exists():
        raise FileNotFoundError(f"파일이 없습니다: {path}")

    df = pd.read_csv(path, encoding="utf-8-sig")

    if df.empty:
        raise ValueError(f"파일이 비어 있습니다: {path}")

    return df


def split_by_month(
    df: pd.DataFrame,
    month_col: str = "Month",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Month 컬럼을 기준으로 설계용 기간과 검증용 기간을 나눈다.

    Month 값은 YYYY-MM 또는 YYYY-MM-DD 형태가 섞여 있을 수 있으므로
    앞의 7자리만 사용하여 YYYY-MM 기준으로 통일한다.
    """
    if month_col not in df.columns:
        raise ValueError(f"Month 컬럼이 없습니다. 현재 컬럼: {df.columns.tolist()}")

    temp = df.copy()
    temp[month_col] = temp[month_col].astype(str).str.slice(0, 7)

    design = temp[
        (temp[month_col] >= DESIGN_START) &
        (temp[month_col] <= DESIGN_END)
    ].copy()

    validation = temp[
        (temp[month_col] >= VALIDATION_START) &
        (temp[month_col] <= VALIDATION_END)
    ].copy()

    return design, validation


def summarize_state_labels(df: pd.DataFrame, period_name: str) -> pd.DataFrame:
    """
    HSI 상태명 분포를 요약한다.
    """
    if "HSIStateLabel" not in df.columns:
        return pd.DataFrame()

    summary = (
        df["HSIStateLabel"]
        .value_counts()
        .reset_index()
    )

    summary.columns = ["HSIStateLabel", "Count"]
    summary.insert(0, "Period", period_name)

    total = summary["Count"].sum()
    summary["Share"] = summary["Count"] / total if total > 0 else 0

    return summary


def summarize_wave_market(df: pd.DataFrame, period_name: str) -> pd.DataFrame:
    """
    P파/S파, 양방향 충격, 고변동성 혼합구간 관련 시장 평균을 요약한다.
    """
    numeric_cols = [
        "p_wave_avg",
        "s_wave_avg",
        "two_sided_shock_ratio_avg",
        "vol_spike_share",
        "high_vol_mixed_share",
        "risk_score_avg",
        "overheat_score_avg",
        "recovery_score_avg",
    ]

    available_cols = [col for col in numeric_cols if col in df.columns]

    if not available_cols:
        return pd.DataFrame()

    summary = df[available_cols].mean().to_frame().T
    summary.insert(0, "Period", period_name)

    if "Month" in df.columns and len(df) > 0:
        summary["StartMonth"] = df["Month"].min()
        summary["EndMonth"] = df["Month"].max()
    else:
        summary["StartMonth"] = ""
        summary["EndMonth"] = ""

    summary["RowCount"] = len(df)

    return summary


def save_split_files(filename: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    하나의 결과 파일을 설계용 기간과 검증용 기간으로 나누어 저장한다.
    """
    input_path = TABLE_DIR / filename
    df = read_csv_safely(input_path)

    design, validation = split_by_month(df)

    stem = input_path.stem

    design_path = TABLE_DIR / f"{stem}_design.csv"
    validation_path = TABLE_DIR / f"{stem}_validation.csv"

    design.to_csv(design_path, index=False, encoding="utf-8-sig")
    validation.to_csv(validation_path, index=False, encoding="utf-8-sig")

    print(f"[분리 완료] {filename}")
    print(f"- design rows: {len(design)} -> {design_path.name}")
    print(f"- validation rows: {len(validation)} -> {validation_path.name}")
    print()

    return design, validation


def main() -> None:
    print("[시작] 설계용 기간 / 검증용 기간 분리")
    print(f"- 설계용 기간: {DESIGN_START} ~ {DESIGN_END}")
    print(f"- 검증용 기간: {VALIDATION_START} ~ {VALIDATION_END}")
    print()
    print("[주의]")
    print("- 이 결과는 완전한 out-of-sample 검증이라기보다, 탐색적 HSI 기준의 기간별 안정성 확인입니다.")
    print("- 상태명 기준 자체는 별도 설계 문서에서 고정한 뒤 해석하는 것이 안전합니다.")
    print()

    all_state_summaries = []
    all_wave_summaries = []

    for filename in INPUT_FILES:
        input_path = TABLE_DIR / filename

        if not input_path.exists():
            print(f"[건너뜀] 파일 없음: {input_path}")
            continue

        design, validation = save_split_files(filename)

        if filename == "monthly_hsi_state_labels.csv":
            all_state_summaries.append(summarize_state_labels(design, "design"))
            all_state_summaries.append(summarize_state_labels(validation, "validation"))

        if filename == "monthly_wave_market_summary.csv":
            all_wave_summaries.append(summarize_wave_market(design, "design"))
            all_wave_summaries.append(summarize_wave_market(validation, "validation"))

    if all_state_summaries:
        state_summary = pd.concat(all_state_summaries, ignore_index=True)
        state_summary_path = TABLE_DIR / "design_validation_state_summary.csv"
        state_summary.to_csv(
            state_summary_path,
            index=False,
            encoding="utf-8-sig",
        )
        print(f"[생성] {state_summary_path.name}")

    if all_wave_summaries:
        wave_summary = pd.concat(all_wave_summaries, ignore_index=True)
        wave_summary_path = TABLE_DIR / "design_validation_wave_summary.csv"
        wave_summary.to_csv(
            wave_summary_path,
            index=False,
            encoding="utf-8-sig",
        )
        print(f"[생성] {wave_summary_path.name}")

    print()
    print("[완료] 기간 분리 작업 종료")
    print()
    print("[출력 파일]")
    print("- monthly_hsi_state_labels_design.csv")
    print("- monthly_hsi_state_labels_validation.csv")
    print("- monthly_wave_features_design.csv")
    print("- monthly_wave_features_validation.csv")
    print("- monthly_wave_market_summary_design.csv")
    print("- monthly_wave_market_summary_validation.csv")
    print("- monthly_event_counts_design.csv")
    print("- monthly_event_counts_validation.csv")
    print("- design_validation_state_summary.csv")
    print("- design_validation_wave_summary.csv")


if __name__ == "__main__":
    main()