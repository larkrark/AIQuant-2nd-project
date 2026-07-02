from pathlib import Path

import numpy as np
import pandas as pd

from common.backtest import (
    align_state_with_next_returns,
    calculate_turnover,
    make_alignment_check,
    make_turnover_summary,
)
from common.config import ASSETS, INITIAL_CAPITAL
from common.io_utils import read_csv_with_date as _read_csv
from common.paths import PROCESSED_DIR, TABLE_DIR


"""
19_main_v2b_backtest_state5_overlay_relaxed.py

목적
----
main_v2 HSI 5상태 체계는 유지하되,
conflict 상태를 방어 신호가 아니라 관찰 상태로 처리하는 완화형 overlay를 백테스트한다.

main_v2와의 차이
---------------
main_v2:
    conflict -> 069500 0.25, 114260 0.375, 153130 0.375

main_v2b:
    conflict -> 069500 1/3, 114260 1/3, 153130 1/3

즉, conflict는 위험 악화 확정이 아니라 신호 혼조 상태로 보고
기본 동일비중을 유지한다.

입력
----
output/tables/main_v2_hsi_state5_table_rank.csv
output/tables/main_v2_hsi_state5_table_zscore.csv
data/processed/monthly_returns.csv

출력
----
output/tables/main_v2b_backtest_timeseries_rank.csv
output/tables/main_v2b_backtest_timeseries_zscore.csv
output/tables/main_v2b_strategy_weights_rank.csv
output/tables/main_v2b_strategy_weights_zscore.csv
output/tables/main_v2b_allocation_rule_table.csv
output/tables/main_v2b_signal_return_alignment_check.csv
output/tables/main_v2b_turnover_summary.csv
"""


# ============================================================
# 0. 경로 설정 (common.paths 사용)
# ============================================================

STATE5_RANK_PATH = TABLE_DIR / "main_v2_hsi_state5_table_rank.csv"
STATE5_ZSCORE_PATH = TABLE_DIR / "main_v2_hsi_state5_table_zscore.csv"
MONTHLY_RETURNS_PATH = PROCESSED_DIR / "monthly_returns.csv"

OUTPUT_BACKTEST_RANK_PATH = TABLE_DIR / "main_v2b_backtest_timeseries_rank.csv"
OUTPUT_BACKTEST_ZSCORE_PATH = TABLE_DIR / "main_v2b_backtest_timeseries_zscore.csv"
OUTPUT_WEIGHTS_RANK_PATH = TABLE_DIR / "main_v2b_strategy_weights_rank.csv"
OUTPUT_WEIGHTS_ZSCORE_PATH = TABLE_DIR / "main_v2b_strategy_weights_zscore.csv"
OUTPUT_ALLOCATION_RULE_PATH = TABLE_DIR / "main_v2b_allocation_rule_table.csv"
OUTPUT_ALIGNMENT_CHECK_PATH = TABLE_DIR / "main_v2b_signal_return_alignment_check.csv"
OUTPUT_TURNOVER_SUMMARY_PATH = TABLE_DIR / "main_v2b_turnover_summary.csv"


# ============================================================
# 1. 실험 설정 (ASSETS/INITIAL_CAPITAL → common.config)
# ============================================================


# ============================================================
# 2. 데이터 로드 (read_csv_with_date → common, 엄격형 동작 유지)
# ============================================================

def read_csv_with_date(path: Path) -> pd.DataFrame:
    """기존 엄격형 로더 동작(Date 필수, signal_date 미파싱)을 common으로 위임."""
    return _read_csv(path, require_date=True, parse_signal_date=False)


# ============================================================
# 3. main_v2b 완화형 비중 규칙
# ============================================================

def make_v2b_allocation_rule_table() -> pd.DataFrame:
    """
    HSI 5상태 완화형 overlay 비중 규칙.

    핵심:
    - conflict는 소폭 방어하지 않고 기본 동일비중 유지
    - risk_warning과 accident_zone에서만 방어
    """

    rows = [
        {
            "hsi_state5": "risk_relief",
            "state_name_kr": "위험 완화 우세",
            "069500_weight": 1 / 3,
            "114260_weight": 1 / 3,
            "153130_weight": 1 / 3,
            "action": "기본 동일비중 유지",
            "rule_note": "위험 완화 우세 상태에서는 추가 공격 없이 기본 비중 유지",
        },
        {
            "hsi_state5": "neutral_watch",
            "state_name_kr": "관찰·중립",
            "069500_weight": 1 / 3,
            "114260_weight": 1 / 3,
            "153130_weight": 1 / 3,
            "action": "기본 동일비중 유지",
            "rule_note": "방향성이 약한 상태이므로 기본 비중 유지",
        },
        {
            "hsi_state5": "conflict",
            "state_name_kr": "충돌 상태",
            "069500_weight": 1 / 3,
            "114260_weight": 1 / 3,
            "153130_weight": 1 / 3,
            "action": "충돌은 관찰로 처리",
            "rule_note": "위험 악화 확정이 아니므로 방어 전환하지 않음",
        },
        {
            "hsi_state5": "risk_warning",
            "state_name_kr": "위험 악화 우세",
            "069500_weight": 0.20,
            "114260_weight": 0.40,
            "153130_weight": 0.40,
            "action": "방어 강화",
            "rule_note": "위험 악화 우세 상태에서 위험자산 축소",
        },
        {
            "hsi_state5": "accident_zone",
            "state_name_kr": "강한 위험 악화",
            "069500_weight": 0.10,
            "114260_weight": 0.45,
            "153130_weight": 0.45,
            "action": "강한 방어전환",
            "rule_note": "위험 악화 방향성과 강도가 모두 높은 상태에서 강한 방어",
        },
        {
            "hsi_state5": "insufficient_data",
            "state_name_kr": "자료 부족",
            "069500_weight": 1 / 3,
            "114260_weight": 1 / 3,
            "153130_weight": 1 / 3,
            "action": "자료 부족 구간은 기본 동일비중",
            "rule_note": "판단 근거 부족 시 기본 비중 유지",
        },
    ]

    rule = pd.DataFrame(rows)
    rule["weight_sum"] = rule[["069500_weight", "114260_weight", "153130_weight"]].sum(axis=1)

    if not np.allclose(rule["weight_sum"], 1.0):
        raise ValueError("비중 합계가 1.0이 아닌 규칙이 있습니다.")

    return rule


def apply_v2b_weights(state5: pd.DataFrame, method: str) -> pd.DataFrame:
    """
    16번에서 만든 state5 표에 main_v2b 비중 규칙을 다시 붙인다.
    기존 main_v2 비중 컬럼이 있어도 덮어쓴다.
    """

    rule = make_v2b_allocation_rule_table()

    keep_cols = [
        col for col in state5.columns
        if col not in [
            "069500_weight",
            "114260_weight",
            "153130_weight",
            "action",
            "weight_sum",
            "rule_note",
        ]
    ]

    result = state5[keep_cols].copy()

    result = result.merge(
        rule[
            [
                "hsi_state5",
                "069500_weight",
                "114260_weight",
                "153130_weight",
                "action",
                "rule_note",
                "weight_sum",
            ]
        ],
        on="hsi_state5",
        how="left",
    )

    if result[["069500_weight", "114260_weight", "153130_weight"]].isna().any().any():
        bad = result[result[["069500_weight", "114260_weight", "153130_weight"]].isna().any(axis=1)]
        raise ValueError(f"[{method}] 비중이 붙지 않은 상태가 있습니다:\n{bad[['Date', 'hsi_state5']].head()}")

    if not np.allclose(result["weight_sum"], 1.0):
        bad = result.loc[~np.isclose(result["weight_sum"], 1.0)]
        raise ValueError(f"[{method}] 비중 합계가 1.0이 아닌 행이 있습니다:\n{bad.head()}")

    result["method"] = method
    result["overlay_rule"] = "main_v2b_conflict_as_watch"

    return result


# ============================================================
# 4. 월말 HSI → 다음 달 수익률 정렬
#    align_state_with_next_returns → common.backtest
# ============================================================


# ============================================================
# 5. 백테스트 계산
# ============================================================

def calculate_strategy_return(row: pd.Series, strategy: str) -> tuple[float, dict]:
    if strategy == "EW":
        weights = {asset: 1 / len(ASSETS) for asset in ASSETS}

    elif strategy == "HSI_state5_overlay_v2b":
        weights = {
            "069500": row["069500_weight"],
            "114260": row["114260_weight"],
            "153130": row["153130_weight"],
        }

    else:
        raise ValueError(f"알 수 없는 전략입니다: {strategy}")

    monthly_return = sum(
        weights[asset] * row[f"{asset}_next_return"]
        for asset in ASSETS
    )

    return monthly_return, weights


def build_backtest_for_method(aligned: pd.DataFrame, method: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    backtest_rows = []
    weight_rows = []

    strategies = ["EW", "HSI_state5_overlay_v2b"]

    for _, row in aligned.iterrows():
        for strategy in strategies:
            monthly_return, weights = calculate_strategy_return(row, strategy)

            backtest_rows.append(
                {
                    "method": method,
                    "strategy": strategy,
                    "overlay_rule": "main_v2b_conflict_as_watch",
                    "signal_date": row["Date"],
                    "Date": row["next_return_date"],
                    "hsi_state5": row.get("hsi_state5", np.nan),
                    "state_name_kr": row.get("state_name_kr", np.nan),
                    "state_reason": row.get("state_reason", np.nan),
                    "action": row.get("action", np.nan),
                    "monthly_return": monthly_return,
                }
            )

            weight_row = {
                "method": method,
                "strategy": strategy,
                "overlay_rule": "main_v2b_conflict_as_watch",
                "signal_date": row["Date"],
                "Date": row["next_return_date"],
                "hsi_state5": row.get("hsi_state5", np.nan),
                "state_name_kr": row.get("state_name_kr", np.nan),
                "action": row.get("action", np.nan),
            }

            for asset in ASSETS:
                weight_row[f"{asset}_weight"] = weights[asset]

            weight_rows.append(weight_row)

    backtest = pd.DataFrame(backtest_rows)
    weights = pd.DataFrame(weight_rows)

    backtest = backtest.sort_values(["method", "strategy", "Date"]).reset_index(drop=True)

    backtest["cumulative_return"] = (
        backtest
        .groupby(["method", "strategy"])["monthly_return"]
        .transform(lambda x: (1 + x).cumprod() * INITIAL_CAPITAL)
    )

    backtest["running_max"] = (
        backtest
        .groupby(["method", "strategy"])["cumulative_return"]
        .transform("cummax")
    )

    backtest["drawdown"] = backtest["cumulative_return"] / backtest["running_max"] - 1

    return backtest, weights


# ============================================================
# 6. Turnover 계산 · 7. 정렬 점검표
#    calculate_turnover / make_turnover_summary / make_alignment_check
#    → common.backtest
# ============================================================


# ============================================================
# 8. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("19_main_v2b_backtest_state5_overlay_relaxed.py 실행 시작")
    print("=" * 70)

    state5_rank = read_csv_with_date(STATE5_RANK_PATH)
    state5_zscore = read_csv_with_date(STATE5_ZSCORE_PATH)
    monthly_returns = read_csv_with_date(MONTHLY_RETURNS_PATH)

    print("[로드 완료]")
    print(f"- state5_rank: {state5_rank.shape}")
    print(f"- state5_zscore: {state5_zscore.shape}")
    print(f"- monthly_returns: {monthly_returns.shape}")

    allocation_rule = make_v2b_allocation_rule_table()

    state5_rank_v2b = apply_v2b_weights(state5_rank, method="rank")
    state5_zscore_v2b = apply_v2b_weights(state5_zscore, method="zscore")

    aligned_rank = align_state_with_next_returns(state5_rank_v2b, monthly_returns, method="rank")
    aligned_zscore = align_state_with_next_returns(state5_zscore_v2b, monthly_returns, method="zscore")

    print("\n[정렬 완료]")
    print(f"- aligned_rank: {aligned_rank.shape}")
    print(f"- aligned_zscore: {aligned_zscore.shape}")

    backtest_rank, weights_rank = build_backtest_for_method(aligned_rank, method="rank")
    backtest_zscore, weights_zscore = build_backtest_for_method(aligned_zscore, method="zscore")

    turnover_rank = calculate_turnover(weights_rank)
    turnover_zscore = calculate_turnover(weights_zscore)
    turnover_all = pd.concat([turnover_rank, turnover_zscore], ignore_index=True)
    turnover_summary = make_turnover_summary(turnover_all)

    alignment_check = make_alignment_check(aligned_rank, aligned_zscore)

    backtest_rank.to_csv(OUTPUT_BACKTEST_RANK_PATH, index=False, encoding="utf-8-sig")
    backtest_zscore.to_csv(OUTPUT_BACKTEST_ZSCORE_PATH, index=False, encoding="utf-8-sig")
    weights_rank.to_csv(OUTPUT_WEIGHTS_RANK_PATH, index=False, encoding="utf-8-sig")
    weights_zscore.to_csv(OUTPUT_WEIGHTS_ZSCORE_PATH, index=False, encoding="utf-8-sig")
    allocation_rule.to_csv(OUTPUT_ALLOCATION_RULE_PATH, index=False, encoding="utf-8-sig")
    alignment_check.to_csv(OUTPUT_ALIGNMENT_CHECK_PATH, index=False, encoding="utf-8-sig")
    turnover_summary.to_csv(OUTPUT_TURNOVER_SUMMARY_PATH, index=False, encoding="utf-8-sig")

    print("\n[저장 완료]")
    print(f"- {OUTPUT_BACKTEST_RANK_PATH}")
    print(f"- {OUTPUT_BACKTEST_ZSCORE_PATH}")
    print(f"- {OUTPUT_WEIGHTS_RANK_PATH}")
    print(f"- {OUTPUT_WEIGHTS_ZSCORE_PATH}")
    print(f"- {OUTPUT_ALLOCATION_RULE_PATH}")
    print(f"- {OUTPUT_ALIGNMENT_CHECK_PATH}")
    print(f"- {OUTPUT_TURNOVER_SUMMARY_PATH}")

    print("\n[main_v2b 비중 규칙]")
    print(allocation_rule)

    print("\n[정렬 점검]")
    print(alignment_check)

    print("\n[Turnover 요약]")
    print(turnover_summary)

    print("\n[월간 수익률 요약]")
    summary = (
        pd.concat([backtest_rank, backtest_zscore], ignore_index=True)
        .groupby(["method", "strategy"], dropna=False)
        .agg(
            months=("monthly_return", "count"),
            mean_monthly_return=("monthly_return", "mean"),
            min_monthly_return=("monthly_return", "min"),
            max_monthly_return=("monthly_return", "max"),
            final_cumulative_return=("cumulative_return", "last"),
            mdd=("drawdown", "min"),
        )
        .reset_index()
    )
    print(summary)

    print("\n" + "=" * 70)
    print("19_main_v2b_backtest_state5_overlay_relaxed.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()
