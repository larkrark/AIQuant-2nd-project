from pathlib import Path

import numpy as np
import pandas as pd

from common.backtest import (
    align_state_with_next_returns,
    calculate_turnover,
    make_alignment_check,
    make_turnover_summary,
)
from common.config import ASSETS, INITIAL_CAPITAL, WEIGHT_COLS
from common.io_utils import read_csv_with_date as _read_csv
from common.paths import PROCESSED_DIR, TABLE_DIR


"""
17_main_v2_backtest_hsi_state5_overlay.py

목적
----
16번에서 만든 HSI 5상태표와 상태별 overlay 비중을 이용해
EW 전략과 HSI 5상태 overlay 전략을 백테스트한다.

핵심 원칙
--------
월말 HSI 상태는 다음 달 월간 수익률에 적용한다.
즉, Date=t의 HSI 상태와 비중은 Date=t+1의 월간 수익률에 적용된다.

입력
----
output/tables/main_v2_hsi_state5_table_rank.csv
output/tables/main_v2_hsi_state5_table_zscore.csv
data/processed/monthly_returns.csv

출력
----
output/tables/main_v2_backtest_timeseries_rank.csv
output/tables/main_v2_backtest_timeseries_zscore.csv
output/tables/main_v2_strategy_weights_rank.csv
output/tables/main_v2_strategy_weights_zscore.csv
output/tables/main_v2_signal_return_alignment_check.csv
output/tables/main_v2_turnover_summary.csv
"""


# ============================================================
# 0. 경로 설정 (common.paths 사용)
# ============================================================

STATE5_RANK_PATH = TABLE_DIR / "main_v2_hsi_state5_table_rank.csv"
STATE5_ZSCORE_PATH = TABLE_DIR / "main_v2_hsi_state5_table_zscore.csv"
MONTHLY_RETURNS_PATH = PROCESSED_DIR / "monthly_returns.csv"

OUTPUT_BACKTEST_RANK_PATH = TABLE_DIR / "main_v2_backtest_timeseries_rank.csv"
OUTPUT_BACKTEST_ZSCORE_PATH = TABLE_DIR / "main_v2_backtest_timeseries_zscore.csv"
OUTPUT_WEIGHTS_RANK_PATH = TABLE_DIR / "main_v2_strategy_weights_rank.csv"
OUTPUT_WEIGHTS_ZSCORE_PATH = TABLE_DIR / "main_v2_strategy_weights_zscore.csv"
OUTPUT_ALIGNMENT_CHECK_PATH = TABLE_DIR / "main_v2_signal_return_alignment_check.csv"
OUTPUT_TURNOVER_SUMMARY_PATH = TABLE_DIR / "main_v2_turnover_summary.csv"


# ============================================================
# 1. 실험 설정 (ASSETS/WEIGHT_COLS/INITIAL_CAPITAL → common.config)
# ============================================================


# ============================================================
# 2. 데이터 로드 (read_csv_with_date → common, 엄격형 동작 유지)
# ============================================================

def read_csv_with_date(path: Path) -> pd.DataFrame:
    """기존 엄격형 로더 동작(Date 필수, signal_date 미파싱)을 common으로 위임."""
    return _read_csv(path, require_date=True, parse_signal_date=False)


def validate_inputs(state5: pd.DataFrame, monthly_returns: pd.DataFrame, method: str) -> None:
    required_state_cols = ["Date", "hsi_state5"] + list(WEIGHT_COLS.values())

    missing_state_cols = [col for col in required_state_cols if col not in state5.columns]
    if missing_state_cols:
        raise ValueError(f"[{method}] state5에 필요한 컬럼이 없습니다: {missing_state_cols}")

    missing_return_cols = [col for col in ASSETS if col not in monthly_returns.columns]
    if missing_return_cols:
        raise ValueError(f"monthly_returns에 필요한 ETF 수익률 컬럼이 없습니다: {missing_return_cols}")

    weight_sum = state5[list(WEIGHT_COLS.values())].sum(axis=1)
    if not np.allclose(weight_sum, 1.0):
        bad = state5.loc[~np.isclose(weight_sum, 1.0), ["Date", "hsi_state5"] + list(WEIGHT_COLS.values())]
        raise ValueError(f"[{method}] 비중 합계가 1.0이 아닌 행이 있습니다:\n{bad.head()}")


# ============================================================
# 3. 월말 HSI → 다음 달 수익률 정렬
#    align_state_with_next_returns → common.backtest
# ============================================================


# ============================================================
# 4. 백테스트 계산
# ============================================================

def calculate_strategy_return(row: pd.Series, strategy: str) -> tuple[float, dict]:
    """
    한 달의 전략 수익률과 사용 비중을 계산한다.
    """

    if strategy == "EW":
        weights = {asset: 1 / len(ASSETS) for asset in ASSETS}

    elif strategy == "HSI_state5_overlay":
        weights = {
            asset: row[weight_col]
            for asset, weight_col in WEIGHT_COLS.items()
        }

    else:
        raise ValueError(f"알 수 없는 전략입니다: {strategy}")

    monthly_return = 0.0

    for asset in ASSETS:
        monthly_return += weights[asset] * row[f"{asset}_next_return"]

    return monthly_return, weights


def build_backtest_for_method(aligned: pd.DataFrame, method: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    backtest_rows = []
    weight_rows = []

    strategies = ["EW", "HSI_state5_overlay"]

    for _, row in aligned.iterrows():
        for strategy in strategies:
            monthly_return, weights = calculate_strategy_return(row, strategy)

            backtest_rows.append(
                {
                    "method": method,
                    "strategy": strategy,
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
# 5. Turnover 계산 · 6. 정렬 점검표
#    calculate_turnover / make_turnover_summary / make_alignment_check
#    → common.backtest
# ============================================================


# ============================================================
# 7. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("17_main_v2_backtest_hsi_state5_overlay.py 실행 시작")
    print("=" * 70)

    state5_rank = read_csv_with_date(STATE5_RANK_PATH)
    state5_zscore = read_csv_with_date(STATE5_ZSCORE_PATH)
    monthly_returns = read_csv_with_date(MONTHLY_RETURNS_PATH)

    print("[로드 완료]")
    print(f"- state5_rank: {state5_rank.shape}")
    print(f"- state5_zscore: {state5_zscore.shape}")
    print(f"- monthly_returns: {monthly_returns.shape}")

    validate_inputs(state5_rank, monthly_returns, method="rank")
    validate_inputs(state5_zscore, monthly_returns, method="zscore")

    aligned_rank = align_state_with_next_returns(state5_rank, monthly_returns, method="rank")
    aligned_zscore = align_state_with_next_returns(state5_zscore, monthly_returns, method="zscore")

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
    alignment_check.to_csv(OUTPUT_ALIGNMENT_CHECK_PATH, index=False, encoding="utf-8-sig")
    turnover_summary.to_csv(OUTPUT_TURNOVER_SUMMARY_PATH, index=False, encoding="utf-8-sig")

    print("\n[저장 완료]")
    print(f"- {OUTPUT_BACKTEST_RANK_PATH}")
    print(f"- {OUTPUT_BACKTEST_ZSCORE_PATH}")
    print(f"- {OUTPUT_WEIGHTS_RANK_PATH}")
    print(f"- {OUTPUT_WEIGHTS_ZSCORE_PATH}")
    print(f"- {OUTPUT_ALIGNMENT_CHECK_PATH}")
    print(f"- {OUTPUT_TURNOVER_SUMMARY_PATH}")

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
    print("17_main_v2_backtest_hsi_state5_overlay.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()
