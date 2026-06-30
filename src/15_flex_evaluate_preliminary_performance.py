"""
15_flex_evaluate_preliminary_performance.py

목적
----
14번 flex 예비 백테스트 결과를 이용해 성과지표를 계산한다.

이 파일은 최종 전략 성과를 확정하는 코드가 아니다.
예비 ETF 3종 기준으로 EW와 EW+HSI overlay 전략이
성과평가 단계까지 연결되는지 확인하기 위한 flex 파이프라인 코드이다.

입력 파일
---------
output/tables/flex_backtest_timeseries_rank.csv
output/tables/flex_backtest_timeseries_zscore.csv

출력 파일
---------
output/tables/flex_performance_summary.csv
output/tables/flex_drawdown_timeseries.csv
output/tables/flex_cumulative_return_timeseries.csv
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

BACKTEST_RANK_PATH = TABLE_DIR / "flex_backtest_timeseries_rank.csv"
BACKTEST_ZSCORE_PATH = TABLE_DIR / "flex_backtest_timeseries_zscore.csv"


# ============================================================
# 3. 출력 파일 경로
# ============================================================

PERFORMANCE_SUMMARY_PATH = TABLE_DIR / "flex_performance_summary.csv"
DRAWDOWN_TIMESERIES_PATH = TABLE_DIR / "flex_drawdown_timeseries.csv"
CUMULATIVE_RETURN_TIMESERIES_PATH = TABLE_DIR / "flex_cumulative_return_timeseries.csv"


# ============================================================
# 4. 공통 함수
# ============================================================

def read_backtest(path: Path) -> pd.DataFrame:
    """
    14번 flex 백테스트 결과 파일을 읽는다.
    """
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    df = pd.read_csv(path)

    required_cols = [
        "Date",
        "signal_date",
        "method",
        "strategy",
        "strategy_return",
        "cumulative_return",
        "portfolio_value",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_cols}")

    df["Date"] = pd.to_datetime(df["Date"])
    df["signal_date"] = pd.to_datetime(df["signal_date"])

    df = df.sort_values(["method", "strategy", "Date"]).reset_index(drop=True)

    return df


def calculate_drawdown(group: pd.DataFrame) -> pd.DataFrame:
    """
    전략별 Drawdown 시계열을 계산한다.

    Drawdown = 현재 포트폴리오 가치 / 과거 최고 포트폴리오 가치 - 1
    """
    result = group.copy()

    result["running_max"] = result["portfolio_value"].cummax()
    result["drawdown"] = result["portfolio_value"] / result["running_max"] - 1.0

    return result


def calculate_performance_metrics(group: pd.DataFrame) -> dict:
    """
    전략별 성과지표를 계산한다.

    월간 수익률 기준이며, 연율화는 12개월 기준으로 계산한다.
    """
    group = group.sort_values("Date").copy()

    returns = group["strategy_return"].dropna()
    portfolio_value = group["portfolio_value"].dropna()

    months = returns.shape[0]

    if months == 0:
        return {
            "months": 0,
            "start_date": None,
            "end_date": None,
            "total_return": None,
            "cagr": None,
            "annual_volatility": None,
            "sharpe": None,
            "mdd": None,
            "calmar": None,
            "win_rate": None,
            "mean_monthly_return": None,
            "std_monthly_return": None,
            "min_monthly_return": None,
            "max_monthly_return": None,
        }

    start_date = group["Date"].min()
    end_date = group["Date"].max()

    final_value = portfolio_value.iloc[-1]
    total_return = final_value - 1.0

    years = months / 12.0
    cagr = final_value ** (1.0 / years) - 1.0 if years > 0 and final_value > 0 else None

    monthly_mean = returns.mean()
    monthly_std = returns.std()

    annual_volatility = monthly_std * (12 ** 0.5) if monthly_std is not None else None

    # 무위험수익률은 예비 평가에서는 0으로 둔다.
    # 최종 평가에서는 현금성 ETF 또는 기준 금리를 반영할 수 있다.
    if monthly_std and monthly_std != 0:
        sharpe = (monthly_mean / monthly_std) * (12 ** 0.5)
    else:
        sharpe = None

    drawdown_df = calculate_drawdown(group)
    mdd = drawdown_df["drawdown"].min()

    if mdd is not None and mdd < 0 and cagr is not None:
        calmar = cagr / abs(mdd)
    else:
        calmar = None

    win_rate = (returns > 0).mean()

    return {
        "months": months,
        "start_date": start_date,
        "end_date": end_date,
        "total_return": total_return,
        "cagr": cagr,
        "annual_volatility": annual_volatility,
        "sharpe": sharpe,
        "mdd": mdd,
        "calmar": calmar,
        "win_rate": win_rate,
        "mean_monthly_return": monthly_mean,
        "std_monthly_return": monthly_std,
        "min_monthly_return": returns.min(),
        "max_monthly_return": returns.max(),
    }


def make_performance_summary(backtest: pd.DataFrame) -> pd.DataFrame:
    """
    method, strategy별 성과 요약표를 만든다.
    """
    rows = []

    grouped = backtest.groupby(["method", "strategy"], dropna=False)

    for (method, strategy), group in grouped:
        metrics = calculate_performance_metrics(group)

        row = {
            "method": method,
            "strategy": strategy,
        }
        row.update(metrics)

        rows.append(row)

    return pd.DataFrame(rows)


def make_drawdown_timeseries(backtest: pd.DataFrame) -> pd.DataFrame:
    """
    전체 전략의 Drawdown 시계열을 만든다.
    """
    result = (
        backtest
        .groupby(["method", "strategy"], group_keys=False)
        .apply(calculate_drawdown, include_groups=False)
        .reset_index()
    )

    return result


def make_cumulative_return_timeseries(backtest: pd.DataFrame) -> pd.DataFrame:
    """
    발표용 누적수익률 시계열을 따로 만든다.

    긴 형식(long format)으로 저장한다.
    """
    cols = [
        "Date",
        "signal_date",
        "method",
        "strategy",
        "strategy_return",
        "cumulative_return",
        "portfolio_value",
    ]

    available_cols = [col for col in cols if col in backtest.columns]

    return backtest[available_cols].copy()


def add_comparison_columns(summary: pd.DataFrame) -> pd.DataFrame:
    """
    EW 대비 EW_HSI_overlay의 차이를 보기 위한 비교용 컬럼을 추가한다.

    같은 method 안에서 EW를 기준으로 비교한다.
    """
    result = summary.copy()

    metric_cols = [
        "total_return",
        "cagr",
        "annual_volatility",
        "sharpe",
        "mdd",
        "calmar",
        "win_rate",
        "mean_monthly_return",
    ]

    for col in metric_cols:
        result[f"{col}_diff_vs_ew"] = None

    for method in result["method"].unique():
        method_mask = result["method"] == method
        method_df = result[method_mask]

        ew_row = method_df[method_df["strategy"] == "EW"]

        if ew_row.empty:
            continue

        ew_values = ew_row.iloc[0]

        for idx in method_df.index:
            for col in metric_cols:
                if col in result.columns and pd.notna(result.loc[idx, col]) and pd.notna(ew_values[col]):
                    result.loc[idx, f"{col}_diff_vs_ew"] = result.loc[idx, col] - ew_values[col]

    return result


# ============================================================
# 5. 메인 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("15_flex_evaluate_preliminary_performance.py 실행 시작")
    print("=" * 70)

    # --------------------------------------------------------
    # 데이터 읽기
    # --------------------------------------------------------
    backtest_rank = read_backtest(BACKTEST_RANK_PATH)
    backtest_zscore = read_backtest(BACKTEST_ZSCORE_PATH)

    backtest_all = pd.concat(
        [backtest_rank, backtest_zscore],
        ignore_index=True,
    )

    print("[로드 완료]")
    print(f"- backtest_rank: {backtest_rank.shape}")
    print(f"- backtest_zscore: {backtest_zscore.shape}")
    print(f"- backtest_all: {backtest_all.shape}")

    # --------------------------------------------------------
    # 성과 계산
    # --------------------------------------------------------
    performance_summary = make_performance_summary(backtest_all)
    performance_summary = add_comparison_columns(performance_summary)

    drawdown_timeseries = make_drawdown_timeseries(backtest_all)
    cumulative_return_timeseries = make_cumulative_return_timeseries(backtest_all)

    print()
    print("[성과 계산 완료]")
    print(f"- performance_summary: {performance_summary.shape}")
    print(f"- drawdown_timeseries: {drawdown_timeseries.shape}")
    print(f"- cumulative_return_timeseries: {cumulative_return_timeseries.shape}")

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------
    performance_summary.to_csv(
        PERFORMANCE_SUMMARY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    drawdown_timeseries.to_csv(
        DRAWDOWN_TIMESERIES_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    cumulative_return_timeseries.to_csv(
        CUMULATIVE_RETURN_TIMESERIES_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("[저장 완료]")
    print(f"- {PERFORMANCE_SUMMARY_PATH}")
    print(f"- {DRAWDOWN_TIMESERIES_PATH}")
    print(f"- {CUMULATIVE_RETURN_TIMESERIES_PATH}")

    print()
    print("[예비 성과 요약]")
    print(performance_summary)

    print()
    print("=" * 70)
    print("15_flex_evaluate_preliminary_performance.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()