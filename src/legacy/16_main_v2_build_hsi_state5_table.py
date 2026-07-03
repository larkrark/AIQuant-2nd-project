from pathlib import Path

import numpy as np
import pandas as pd


"""
16_main_v2_build_hsi_state5_table.py

목적
----
데이터 담당자님의 buy/watch/caution 3분류를 최종 전략 상태로 바로 쓰지 않고,
우리 프로젝트의 HSI 해석 체계인 5상태로 재분류한다.

5상태:
1. risk_relief      / 위험 완화 우세
2. neutral_watch    / 관찰·중립
3. conflict         / 충돌 상태
4. risk_warning     / 위험 악화 우세
5. accident_zone    / 강한 위험 악화, 방어전환 필요

입력
----
output/tables/flex_hsi_monthly_state_rank.csv
output/tables/flex_hsi_monthly_state_zscore.csv

출력
----
output/tables/main_v2_hsi_state5_table_rank.csv
output/tables/main_v2_hsi_state5_table_zscore.csv
output/tables/main_v2_hsi_state5_definition.csv
output/tables/main_v2_allocation_rule_table.csv
output/tables/main_v2_hsi_state5_distribution.csv
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"

INPUT_RANK_PATH = TABLE_DIR / "flex_hsi_monthly_state_rank.csv"
INPUT_ZSCORE_PATH = TABLE_DIR / "flex_hsi_monthly_state_zscore.csv"

OUTPUT_RANK_PATH = TABLE_DIR / "main_v2_hsi_state5_table_rank.csv"
OUTPUT_ZSCORE_PATH = TABLE_DIR / "main_v2_hsi_state5_table_zscore.csv"
OUTPUT_DEFINITION_PATH = TABLE_DIR / "main_v2_hsi_state5_definition.csv"
OUTPUT_ALLOCATION_RULE_PATH = TABLE_DIR / "main_v2_allocation_rule_table.csv"
OUTPUT_DISTRIBUTION_PATH = TABLE_DIR / "main_v2_hsi_state5_distribution.csv"


# ============================================================
# 1. 실험 기준 설정
# ============================================================

PRIMARY_RISK_TICKER = "069500"   # KODEX 200, 위험자산 대표 신호로 사용

# 방향성 HSI 해석 기준
# direction > +0.15 : 위험 악화 방향
# direction < -0.15 : 위험 완화 방향
# 그 사이 : 중립/관찰
NEUTRAL_BAND = 0.15

# intensity 상위 몇 %부터 강한 신호로 볼지
HIGH_INTENSITY_QUANTILE = 0.75

# accident_zone 판단용: 위험 악화 방향성이 상위 몇 % 이상인지
ACCIDENT_DIRECTION_QUANTILE = 0.85


# ============================================================
# 2. 유틸 함수
# ============================================================

def read_csv_with_date(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    df = pd.read_csv(path)

    if "Date" not in df.columns:
        raise ValueError(f"Date 컬럼이 없습니다: {path}")

    df["Date"] = pd.to_datetime(df["Date"])
    return df


def find_col(columns, ticker: str, keyword: str) -> str:
    """
    컬럼명이 약간 달라도 찾기 위한 함수.
    예:
    - 069500_direction
    - direction_069500
    - 069500_hsi_direction
    """
    candidates = [
        col for col in columns
        if ticker in col and keyword.lower() in col.lower()
    ]

    if len(candidates) == 0:
        raise ValueError(
            f"{ticker}와 {keyword}를 포함하는 컬럼을 찾지 못했습니다.\n"
            f"현재 컬럼 목록:\n{list(columns)}"
        )

    if len(candidates) > 1:
        print(f"[주의] {ticker}, {keyword} 후보 컬럼이 여러 개입니다: {candidates}")
        print(f"       첫 번째 컬럼을 사용합니다: {candidates[0]}")

    return candidates[0]


def get_signal_columns(df: pd.DataFrame) -> list[str]:
    """
    ETF별 signal 컬럼을 찾는다.
    conflict 판단 보조용이다.

    예:
    - 069500_signal
    - 114260_signal
    - 153130_signal
    """
    signal_cols = [
        col for col in df.columns
        if "signal" in col.lower()
    ]
    return signal_cols


def has_cross_asset_conflict(row: pd.Series, signal_cols: list[str]) -> bool:
    """
    여러 ETF 신호가 같은 달에 buy와 caution을 동시에 포함하면
    시장 내부 신호가 엇갈리는 것으로 보고 conflict 후보로 처리한다.
    """
    if len(signal_cols) == 0:
        return False

    labels = set()

    for col in signal_cols:
        val = row.get(col, np.nan)
        if pd.notna(val):
            labels.add(str(val).lower())

    return ("buy" in labels) and ("caution" in labels)


# ============================================================
# 3. HSI 5상태 분류 함수
# ============================================================

def classify_state5(
    direction: float,
    intensity: float,
    high_intensity_cutoff: float,
    accident_direction_cutoff: float,
    cross_asset_conflict: bool,
) -> tuple[str, str]:
    """
    HSI 5상태 분류.

    direction:
        양수 = 위험 악화 방향
        음수 = 위험 완화 방향

    intensity:
        신호 강도

    cross_asset_conflict:
        여러 ETF의 1차 signal이 buy와 caution으로 엇갈리는지 여부
    """

    if pd.isna(direction) or pd.isna(intensity):
        return "insufficient_data", "direction 또는 intensity 결측"

    # 1) 충돌 상태
    # 방향성은 약한데 강도는 높거나, ETF 간 신호가 서로 엇갈리면 conflict로 본다.
    if cross_asset_conflict:
        return "conflict", "ETF별 신호가 buy와 caution으로 동시에 나타남"

    if abs(direction) <= NEUTRAL_BAND and intensity >= high_intensity_cutoff:
        return "conflict", "방향성은 약하지만 신호 강도가 높음"

    # 2) 강한 위험 악화
    if direction >= accident_direction_cutoff and intensity >= high_intensity_cutoff:
        return "accident_zone", "위험 악화 방향성과 신호 강도가 모두 높음"

    # 3) 일반 위험 악화
    if direction > NEUTRAL_BAND:
        return "risk_warning", "위험 악화 방향 우세"

    # 4) 위험 완화
    if direction < -NEUTRAL_BAND:
        return "risk_relief", "위험 완화 방향 우세"

    # 5) 나머지는 관찰·중립
    return "neutral_watch", "방향성이 뚜렷하지 않아 관찰 상태"


# ============================================================
# 4. 상태별 overlay 비중 규칙
# ============================================================

def make_allocation_rule_table() -> pd.DataFrame:
    """
    HSI 5상태별 방어형 overlay 비중 규칙.

    모든 행의 비중 합계는 1.0이어야 한다.
    """
    rows = [
        {
            "hsi_state5": "risk_relief",
            "state_name_kr": "위험 완화 우세",
            "069500_weight": 1 / 3,
            "114260_weight": 1 / 3,
            "153130_weight": 1 / 3,
            "action": "기본 동일비중 유지",
        },
        {
            "hsi_state5": "neutral_watch",
            "state_name_kr": "관찰·중립",
            "069500_weight": 1 / 3,
            "114260_weight": 1 / 3,
            "153130_weight": 1 / 3,
            "action": "기본 동일비중 유지",
        },
        {
            "hsi_state5": "conflict",
            "state_name_kr": "충돌 상태",
            "069500_weight": 0.25,
            "114260_weight": 0.375,
            "153130_weight": 0.375,
            "action": "소폭 방어",
        },
        {
            "hsi_state5": "risk_warning",
            "state_name_kr": "위험 악화 우세",
            "069500_weight": 0.20,
            "114260_weight": 0.40,
            "153130_weight": 0.40,
            "action": "방어 강화",
        },
        {
            "hsi_state5": "accident_zone",
            "state_name_kr": "강한 위험 악화",
            "069500_weight": 0.10,
            "114260_weight": 0.45,
            "153130_weight": 0.45,
            "action": "강한 방어전환",
        },
        {
            "hsi_state5": "insufficient_data",
            "state_name_kr": "자료 부족",
            "069500_weight": 1 / 3,
            "114260_weight": 1 / 3,
            "153130_weight": 1 / 3,
            "action": "자료 부족 구간은 기본 동일비중",
        },
    ]

    rule = pd.DataFrame(rows)
    rule["weight_sum"] = (
        rule["069500_weight"]
        + rule["114260_weight"]
        + rule["153130_weight"]
    )

    # 부동소수점 오차를 감안하여 검사
    if not np.allclose(rule["weight_sum"], 1.0):
        raise ValueError("비중 합계가 1.0이 아닌 행이 있습니다.")

    return rule


def make_state_definition_table() -> pd.DataFrame:
    rows = [
        {
            "hsi_state5": "risk_relief",
            "state_name_kr": "위험 완화 우세",
            "meaning": "위험 완화 방향 신호가 우세한 상태",
            "portfolio_interpretation": "기본 비중을 유지한다.",
        },
        {
            "hsi_state5": "neutral_watch",
            "state_name_kr": "관찰·중립",
            "meaning": "방향성이 약하거나 뚜렷하지 않은 상태",
            "portfolio_interpretation": "무리한 비중 조정을 하지 않고 관찰한다.",
        },
        {
            "hsi_state5": "conflict",
            "state_name_kr": "충돌 상태",
            "meaning": "위험 악화와 위험 완화 신호가 동시에 나타나는 상태",
            "portfolio_interpretation": "소폭 방어적으로 조정한다.",
        },
        {
            "hsi_state5": "risk_warning",
            "state_name_kr": "위험 악화 우세",
            "meaning": "위험 악화 방향 신호가 우세한 상태",
            "portfolio_interpretation": "위험자산 비중을 줄이고 방어자산을 확대한다.",
        },
        {
            "hsi_state5": "accident_zone",
            "state_name_kr": "강한 위험 악화",
            "meaning": "위험 악화 방향성과 신호 강도가 모두 높은 상태",
            "portfolio_interpretation": "강한 방어전환 상태로 보고 위험자산을 크게 축소한다.",
        },
        {
            "hsi_state5": "insufficient_data",
            "state_name_kr": "자료 부족",
            "meaning": "rolling window 부족 등으로 HSI 판단이 어려운 상태",
            "portfolio_interpretation": "기본 동일비중을 유지한다.",
        },
    ]

    return pd.DataFrame(rows)


# ============================================================
# 5. 메인 처리 함수
# ============================================================

def build_state5_table(df: pd.DataFrame, method: str) -> pd.DataFrame:
    direction_col = find_col(df.columns, PRIMARY_RISK_TICKER, "direction")
    intensity_col = find_col(df.columns, PRIMARY_RISK_TICKER, "intensity")
    signal_cols = get_signal_columns(df)

    print(f"[{method}] direction_col: {direction_col}")
    print(f"[{method}] intensity_col: {intensity_col}")
    print(f"[{method}] signal_cols: {signal_cols}")

    result = df.copy()

    # 강한 신호 기준은 데이터 분포를 기준으로 잡는다.
    high_intensity_cutoff = result[intensity_col].quantile(HIGH_INTENSITY_QUANTILE)

    # accident_zone용 위험 악화 방향 cutoff는 양수 direction만 대상으로 계산한다.
    positive_direction = result.loc[result[direction_col] > 0, direction_col]

    if len(positive_direction) > 0:
        accident_direction_cutoff = positive_direction.quantile(ACCIDENT_DIRECTION_QUANTILE)
    else:
        accident_direction_cutoff = result[direction_col].quantile(ACCIDENT_DIRECTION_QUANTILE)

    print(f"[{method}] high_intensity_cutoff: {high_intensity_cutoff:.6f}")
    print(f"[{method}] accident_direction_cutoff: {accident_direction_cutoff:.6f}")

    state_rows = []

    for _, row in result.iterrows():
        cross_conflict = has_cross_asset_conflict(row, signal_cols)

        state, reason = classify_state5(
            direction=row[direction_col],
            intensity=row[intensity_col],
            high_intensity_cutoff=high_intensity_cutoff,
            accident_direction_cutoff=accident_direction_cutoff,
            cross_asset_conflict=cross_conflict,
        )

        state_rows.append(
            {
                "hsi_state5": state,
                "state_reason": reason,
                "cross_asset_conflict": cross_conflict,
            }
        )

    state_df = pd.DataFrame(state_rows)

    result["method"] = method
    result["primary_ticker"] = PRIMARY_RISK_TICKER
    result["primary_direction"] = result[direction_col]
    result["primary_intensity"] = result[intensity_col]
    result["hsi_state5"] = state_df["hsi_state5"]
    result["state_reason"] = state_df["state_reason"]
    result["cross_asset_conflict"] = state_df["cross_asset_conflict"]
    result["high_intensity_cutoff"] = high_intensity_cutoff
    result["accident_direction_cutoff"] = accident_direction_cutoff

    # 상태별 비중 붙이기
    rule = make_allocation_rule_table()

    result = result.merge(
        rule[
            [
                "hsi_state5",
                "state_name_kr",
                "069500_weight",
                "114260_weight",
                "153130_weight",
                "action",
                "weight_sum",
            ]
        ],
        on="hsi_state5",
        how="left",
    )

    # 최종 비중 합계 검증
    if not np.allclose(result["weight_sum"], 1.0):
        bad = result.loc[~np.isclose(result["weight_sum"], 1.0)]
        raise ValueError(f"비중 합계가 1.0이 아닌 행이 있습니다:\n{bad.head()}")

    return result


def make_distribution_table(rank_state5: pd.DataFrame, zscore_state5: pd.DataFrame) -> pd.DataFrame:
    all_state = pd.concat([rank_state5, zscore_state5], ignore_index=True)

    dist = (
        all_state
        .groupby(["method", "hsi_state5", "state_name_kr"], dropna=False)
        .size()
        .reset_index(name="months")
    )

    total = (
        all_state
        .groupby("method", dropna=False)
        .size()
        .reset_index(name="total_months")
    )

    dist = dist.merge(total, on="method", how="left")
    dist["ratio"] = dist["months"] / dist["total_months"]

    return dist.sort_values(["method", "hsi_state5"]).reset_index(drop=True)


# ============================================================
# 6. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("16_main_v2_build_hsi_state5_table.py 실행 시작")
    print("=" * 70)

    rank_df = read_csv_with_date(INPUT_RANK_PATH)
    zscore_df = read_csv_with_date(INPUT_ZSCORE_PATH)

    print("[로드 완료]")
    print(f"- rank_df: {rank_df.shape}")
    print(f"- zscore_df: {zscore_df.shape}")

    rank_state5 = build_state5_table(rank_df, method="rank")
    zscore_state5 = build_state5_table(zscore_df, method="zscore")

    definition = make_state_definition_table()
    allocation_rule = make_allocation_rule_table()
    distribution = make_distribution_table(rank_state5, zscore_state5)

    rank_state5.to_csv(OUTPUT_RANK_PATH, index=False, encoding="utf-8-sig")
    zscore_state5.to_csv(OUTPUT_ZSCORE_PATH, index=False, encoding="utf-8-sig")
    definition.to_csv(OUTPUT_DEFINITION_PATH, index=False, encoding="utf-8-sig")
    allocation_rule.to_csv(OUTPUT_ALLOCATION_RULE_PATH, index=False, encoding="utf-8-sig")
    distribution.to_csv(OUTPUT_DISTRIBUTION_PATH, index=False, encoding="utf-8-sig")

    print("\n[저장 완료]")
    print(f"- {OUTPUT_RANK_PATH}")
    print(f"- {OUTPUT_ZSCORE_PATH}")
    print(f"- {OUTPUT_DEFINITION_PATH}")
    print(f"- {OUTPUT_ALLOCATION_RULE_PATH}")
    print(f"- {OUTPUT_DISTRIBUTION_PATH}")

    print("\n[HSI 5상태 분포]")
    print(distribution)

    print("\n[비중 규칙]")
    print(allocation_rule)

    print("\n" + "=" * 70)
    print("16_main_v2_build_hsi_state5_table.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()