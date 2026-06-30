"""
14_flex_backtest_ew_hsi_preliminary.py

목적
----
예비 ETF 3종 기준으로 EW 전략과 EW+HSI overlay 전략을 계산한다.

이 파일은 최종 전략 성과를 확정하는 코드가 아니다.
현재 확보된 예비 산출물을 이용해 다음 흐름이 실제로 연결되는지 확인한다.

월말 HSI 상태
→ 다음 달 월간 수익률
→ HSI overlay 비중
→ 전략 월간 수익률
→ 누적수익률

입력 파일
---------
output/tables/flex_hsi_return_alignment_rank.csv
output/tables/flex_hsi_return_alignment_zscore.csv

출력 파일
---------
output/tables/flex_strategy_weights_rank.csv
output/tables/flex_strategy_weights_zscore.csv
output/tables/flex_backtest_timeseries_rank.csv
output/tables/flex_backtest_timeseries_zscore.csv
output/tables/flex_backtest_rule_summary.csv
"""

from pathlib import Path

import pandas as pd


# ============================================================
# 1. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = PROJECT_ROOT / "output"
TABLE_DIR = OUTPUT_DIR / "tables"

TABLE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. 입력 파일 경로
# ============================================================

ALIGN_RANK_PATH = TABLE_DIR / "flex_hsi_return_alignment_rank.csv"
ALIGN_ZSCORE_PATH = TABLE_DIR / "flex_hsi_return_alignment_zscore.csv"


# ============================================================
# 3. 출력 파일 경로
# ============================================================

WEIGHTS_RANK_PATH = TABLE_DIR / "flex_strategy_weights_rank.csv"
WEIGHTS_ZSCORE_PATH = TABLE_DIR / "flex_strategy_weights_zscore.csv"

BACKTEST_RANK_PATH = TABLE_DIR / "flex_backtest_timeseries_rank.csv"
BACKTEST_ZSCORE_PATH = TABLE_DIR / "flex_backtest_timeseries_zscore.csv"

RULE_SUMMARY_PATH = TABLE_DIR / "flex_backtest_rule_summary.csv"


# ============================================================
# 4. 예비 전략 설정
# ============================================================

"""
예비 ETF 3종 기준 역할

069500: KODEX 200, 주식형 위험자산 역할
114260: KODEX 국고채3년, 채권형 방어자산 역할
153130: KODEX 단기채권PLUS, 현금성/단기채권 방어자산 역할

현재 flex 백테스트에서는 가장 단순한 v0 규칙을 사용한다.

기본 EW:
- 069500: 1/3
- 114260: 1/3
- 153130: 1/3

EW + HSI overlay:
- 069500_signal == "buy"
  → 위험자산 비중을 0.50으로 확대
  → 114260, 153130은 각각 0.25

- 069500_signal == "watch"
  → 기본 EW 유지
  → 각각 1/3

- 069500_signal == "caution"
  → 위험자산 비중을 0.15로 축소
  → 줄인 비중을 114260, 153130에 균등 배분
  → 114260, 153130은 각각 0.425

주의:
이 규칙은 최종 전략 규칙이 아니라, HSI 신호가 월간 수익률 계산에
연결되는지 확인하기 위한 예비 overlay 규칙이다.
"""

RISK_ASSET = "069500"
DEFENSIVE_ASSETS = ["114260", "153130"]
ALL_ASSETS = [RISK_ASSET] + DEFENSIVE_ASSETS

BASE_EW_WEIGHT = 1.0 / len(ALL_ASSETS)

OVERLAY_RULE = {
    "buy": {
        RISK_ASSET: 0.50,
        "defensive_each": 0.25,
        "description": "위험자산 비중 확대",
    },
    "watch": {
        RISK_ASSET: BASE_EW_WEIGHT,
        "defensive_each": BASE_EW_WEIGHT,
        "description": "기본 동일비중 유지",
    },
    "caution": {
        RISK_ASSET: 0.15,
        "defensive_each": (1.0 - 0.15) / len(DEFENSIVE_ASSETS),
        "description": "위험자산 비중 축소",
    },
}


# ============================================================
# 5. 공통 함수
# ============================================================

def read_alignment(path: Path) -> pd.DataFrame:
    """
    HSI와 다음 달 수익률이 정렬된 CSV를 읽는다.
    """
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    df = pd.read_csv(path)

    if "Date" not in df.columns:
        raise ValueError(f"Date 컬럼이 없습니다: {path}")

    if "signal_date" not in df.columns:
        raise ValueError(f"signal_date 컬럼이 없습니다: {path}")

    df["Date"] = pd.to_datetime(df["Date"])
    df["signal_date"] = pd.to_datetime(df["signal_date"])

    df = df.sort_values("Date").reset_index(drop=True)

    return df


def make_ew_weights(aligned: pd.DataFrame, method_name: str) -> pd.DataFrame:
    """
    동일비중 전략의 월별 비중표를 만든다.
    """
    weights = aligned[["Date", "signal_date"]].copy()
    weights["method"] = method_name
    weights["strategy"] = "EW"

    for asset in ALL_ASSETS:
        weights[f"{asset}_weight"] = BASE_EW_WEIGHT

    weights["rule_signal"] = "none"
    weights["rule_description"] = "기본 동일비중"

    return weights


def make_hsi_overlay_weights(aligned: pd.DataFrame, method_name: str) -> pd.DataFrame:
    """
    069500_signal을 기준으로 EW+HSI overlay 비중표를 만든다.

    현재는 예비 v0 규칙이다.
    최종 상태 분류와 자산군 분류가 확정되면 이 규칙은 교체될 수 있다.
    """
    signal_col = f"{RISK_ASSET}_signal"

    if signal_col not in aligned.columns:
        raise ValueError(f"{signal_col} 컬럼이 없습니다.")

    rows = []

    for _, row in aligned.iterrows():
        signal = row[signal_col]

        if signal not in OVERLAY_RULE:
            # 예상하지 못한 신호가 나오면 watch처럼 처리한다.
            signal = "watch"

        rule = OVERLAY_RULE[signal]

        output = {
            "Date": row["Date"],
            "signal_date": row["signal_date"],
            "method": method_name,
            "strategy": "EW_HSI_overlay",
            "rule_signal": signal,
            "rule_description": rule["description"],
        }

        output[f"{RISK_ASSET}_weight"] = rule[RISK_ASSET]

        for asset in DEFENSIVE_ASSETS:
            output[f"{asset}_weight"] = rule["defensive_each"]

        rows.append(output)

    return pd.DataFrame(rows)


def calculate_strategy_return(
    aligned: pd.DataFrame,
    weights: pd.DataFrame,
) -> pd.DataFrame:
    """
    월별 전략 수익률과 누적수익률을 계산한다.
    """
    result = weights.copy()

    monthly_return = pd.Series(0.0, index=result.index)

    for asset in ALL_ASSETS:
        return_col = f"{asset}_return"
        weight_col = f"{asset}_weight"

        if return_col not in aligned.columns:
            raise ValueError(f"{return_col} 컬럼이 없습니다.")

        if weight_col not in result.columns:
            raise ValueError(f"{weight_col} 컬럼이 없습니다.")

        monthly_return += result[weight_col] * aligned[return_col].values

    result["strategy_return"] = monthly_return
    result["cumulative_return"] = (1.0 + result["strategy_return"]).cumprod() - 1.0
    result["portfolio_value"] = (1.0 + result["strategy_return"]).cumprod()

    return result


def make_backtest_timeseries(aligned: pd.DataFrame, method_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    EW와 EW+HSI overlay 전략의 백테스트 시계열과 비중표를 만든다.
    """
    ew_weights = make_ew_weights(aligned, method_name)
    hsi_weights = make_hsi_overlay_weights(aligned, method_name)

    ew_result = calculate_strategy_return(aligned, ew_weights)
    hsi_result = calculate_strategy_return(aligned, hsi_weights)

    backtest = pd.concat([ew_result, hsi_result], ignore_index=True)
    weights = pd.concat([ew_weights, hsi_weights], ignore_index=True)

    return backtest, weights


def make_rule_summary() -> pd.DataFrame:
    """
    현재 예비 overlay 규칙을 표로 저장한다.
    """
    rows = []

    for signal, rule in OVERLAY_RULE.items():
        row = {
            "rule_signal": signal,
            "description": rule["description"],
            f"{RISK_ASSET}_weight": rule[RISK_ASSET],
        }

        for asset in DEFENSIVE_ASSETS:
            row[f"{asset}_weight"] = rule["defensive_each"]

        row["note"] = "예비 flex overlay 규칙이며, 최종 상태 분류 확정 후 변경 가능"

        rows.append(row)

    return pd.DataFrame(rows)


def summarize_backtest(backtest: pd.DataFrame) -> pd.DataFrame:
    """
    콘솔 확인용 간단 요약.
    최종 성과표는 15번 파일에서 별도로 계산한다.
    """
    rows = []

    grouped = backtest.groupby(["method", "strategy"])

    for (method, strategy), group in grouped:
        rows.append({
            "method": method,
            "strategy": strategy,
            "months": group.shape[0],
            "start_date": group["Date"].min(),
            "end_date": group["Date"].max(),
            "final_cumulative_return": group["cumulative_return"].iloc[-1],
            "final_portfolio_value": group["portfolio_value"].iloc[-1],
            "mean_monthly_return": group["strategy_return"].mean(),
            "min_monthly_return": group["strategy_return"].min(),
            "max_monthly_return": group["strategy_return"].max(),
        })

    return pd.DataFrame(rows)


# ============================================================
# 6. 메인 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("14_flex_backtest_ew_hsi_preliminary.py 실행 시작")
    print("=" * 70)

    # --------------------------------------------------------
    # 데이터 읽기
    # --------------------------------------------------------
    aligned_rank = read_alignment(ALIGN_RANK_PATH)
    aligned_zscore = read_alignment(ALIGN_ZSCORE_PATH)

    print("[로드 완료]")
    print(f"- aligned_rank: {aligned_rank.shape}")
    print(f"- aligned_zscore: {aligned_zscore.shape}")

    # --------------------------------------------------------
    # 백테스트 계산
    # --------------------------------------------------------
    backtest_rank, weights_rank = make_backtest_timeseries(
        aligned=aligned_rank,
        method_name="rank",
    )

    backtest_zscore, weights_zscore = make_backtest_timeseries(
        aligned=aligned_zscore,
        method_name="zscore",
    )

    rule_summary = make_rule_summary()

    print()
    print("[백테스트 계산 완료]")
    print(f"- backtest_rank: {backtest_rank.shape}")
    print(f"- backtest_zscore: {backtest_zscore.shape}")
    print(f"- weights_rank: {weights_rank.shape}")
    print(f"- weights_zscore: {weights_zscore.shape}")

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------
    weights_rank.to_csv(
        WEIGHTS_RANK_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    weights_zscore.to_csv(
        WEIGHTS_ZSCORE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    backtest_rank.to_csv(
        BACKTEST_RANK_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    backtest_zscore.to_csv(
        BACKTEST_ZSCORE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    rule_summary.to_csv(
        RULE_SUMMARY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("[저장 완료]")
    print(f"- {WEIGHTS_RANK_PATH}")
    print(f"- {WEIGHTS_ZSCORE_PATH}")
    print(f"- {BACKTEST_RANK_PATH}")
    print(f"- {BACKTEST_ZSCORE_PATH}")
    print(f"- {RULE_SUMMARY_PATH}")

    # --------------------------------------------------------
    # 콘솔 요약
    # --------------------------------------------------------
    summary = pd.concat([
        summarize_backtest(backtest_rank),
        summarize_backtest(backtest_zscore),
    ], ignore_index=True)

    print()
    print("[예비 백테스트 요약]")
    print(summary)

    print()
    print("[예비 overlay 규칙]")
    print(rule_summary)

    print()
    print("=" * 70)
    print("14_flex_backtest_ew_hsi_preliminary.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()