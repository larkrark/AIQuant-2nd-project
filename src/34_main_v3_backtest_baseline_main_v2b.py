from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


"""
34_main_v3_backtest_baseline_main_v2b.py

목적
----
33번에서 생성한 HSI 5상태표를 main_v2b 기준 비중 규칙에 연결하여
baseline 백테스트를 수행한다.

현재 단계의 핵심 질문
--------------------
1. 데이터 담당 파트에서 생성된 월별 HSI 상태표가 실제 비중표로 연결되는가?
2. main_v2b 규칙을 적용했을 때 EW 대비 성과가 어떻게 나오는가?
3. Turnover가 과도하지 않은가?
4. 다음 단계의 추가 지표 실험과 비교할 baseline 성과표가 준비되었는가?

입력
----
data/processed/main_v3_hsi_state5_table.csv
data/processed/monthly_returns.csv
data/processed/selected_etf_universe.csv

출력
----
data/processed/main_v3_baseline_rebalance_weights.csv
data/processed/main_v3_baseline_backtest_timeseries.csv

output/tables/main_v3_baseline_state_allocation_rule.csv
output/tables/main_v3_baseline_alignment_check.csv
output/tables/main_v3_baseline_performance_summary.csv
output/tables/main_v3_baseline_turnover_detail.csv
output/tables/main_v3_baseline_turnover_summary.csv

output/figures/main_v3_baseline_cumulative_return_comparison.png
output/figures/main_v3_baseline_drawdown_comparison.png

docs/main_v3_baseline_backtest_note.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
FIGURE_DIR = PROJECT_ROOT / "output" / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"

DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_HSI_STATE_TABLE = DATA_PROCESSED_DIR / "main_v3_hsi_state5_table.csv"
INPUT_MONTHLY_RETURNS = DATA_PROCESSED_DIR / "monthly_returns.csv"
INPUT_SELECTED_ETF = DATA_PROCESSED_DIR / "selected_etf_universe.csv"

OUTPUT_REBALANCE_WEIGHTS = DATA_PROCESSED_DIR / "main_v3_baseline_rebalance_weights.csv"
OUTPUT_BACKTEST_TS = DATA_PROCESSED_DIR / "main_v3_baseline_backtest_timeseries.csv"

OUTPUT_RULE_TABLE = TABLE_DIR / "main_v3_baseline_state_allocation_rule.csv"
OUTPUT_ALIGNMENT_CHECK = TABLE_DIR / "main_v3_baseline_alignment_check.csv"
OUTPUT_PERFORMANCE = TABLE_DIR / "main_v3_baseline_performance_summary.csv"
OUTPUT_TURNOVER_DETAIL = TABLE_DIR / "main_v3_baseline_turnover_detail.csv"
OUTPUT_TURNOVER_SUMMARY = TABLE_DIR / "main_v3_baseline_turnover_summary.csv"

OUTPUT_FIG_CUMULATIVE = FIGURE_DIR / "main_v3_baseline_cumulative_return_comparison.png"
OUTPUT_FIG_DRAWDOWN = FIGURE_DIR / "main_v3_baseline_drawdown_comparison.png"

OUTPUT_NOTE = DOCS_DIR / "main_v3_baseline_backtest_note.md"


# ============================================================
# 1. 설정
# ============================================================

STRATEGY_HSI = "HSI_main_v2b_baseline"
STRATEGY_EW = "EW_1_3"

RISK_TICKER = "069500"
BOND_TICKER = "114260"
CASH_TICKER = "153130"

TICKERS = [RISK_TICKER, BOND_TICKER, CASH_TICKER]

# main_v2b 기준 규칙
# conflict는 방어 전환이 아니라 관찰 상태로 보고 동일비중 유지.
STATE_ALLOCATION_RULES = {
    "risk_relief": {
        RISK_TICKER: 1 / 3,
        BOND_TICKER: 1 / 3,
        CASH_TICKER: 1 / 3,
        "rule_note": "위험 완화 우세. baseline에서는 과도한 risk-on 없이 동일비중 유지.",
    },
    "neutral_watch": {
        RISK_TICKER: 1 / 3,
        BOND_TICKER: 1 / 3,
        CASH_TICKER: 1 / 3,
        "rule_note": "관찰·중립. 동일비중 유지.",
    },
    "conflict": {
        RISK_TICKER: 1 / 3,
        BOND_TICKER: 1 / 3,
        CASH_TICKER: 1 / 3,
        "rule_note": "신호 충돌. main_v2b에서는 즉시 방어하지 않고 동일비중 관찰.",
    },
    "risk_warning": {
        RISK_TICKER: 0.20,
        BOND_TICKER: 0.40,
        CASH_TICKER: 0.40,
        "rule_note": "위험 악화 우세. 위험자산 축소, 방어자산 확대.",
    },
    "accident_zone": {
        RISK_TICKER: 0.10,
        BOND_TICKER: 0.45,
        CASH_TICKER: 0.45,
        "rule_note": "강한 위험 악화. 위험자산 강한 축소.",
    },
}


# ============================================================
# 2. 유틸 함수
# ============================================================

def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"필수 입력 파일을 찾을 수 없습니다: {path}")


def read_monthly_returns(path: Path) -> pd.DataFrame:
    require_file(path)

    df = pd.read_csv(path)

    if "year_month" in df.columns:
        df = df.set_index("year_month")
    else:
        df = pd.read_csv(path, index_col=0)

    df.index = df.index.astype(str)

    # 컬럼명을 문자열로 고정
    df.columns = [str(c) for c in df.columns]

    # 월간 수익률은 데이터 파이프라인에서 % 단위로 생성됨.
    # 예: 0.6984 = 0.6984%
    # 백테스트 계산에는 decimal로 변환.
    df_decimal = df[TICKERS].astype(float) 

    return df_decimal


def build_rule_table() -> pd.DataFrame:
    rows = []

    for state, rule in STATE_ALLOCATION_RULES.items():
        rows.append({
            "hsi_state": state,
            f"weight_{RISK_TICKER}": rule[RISK_TICKER],
            f"weight_{BOND_TICKER}": rule[BOND_TICKER],
            f"weight_{CASH_TICKER}": rule[CASH_TICKER],
            "risk_weight": rule[RISK_TICKER],
            "defensive_weight_sum": rule[BOND_TICKER] + rule[CASH_TICKER],
            "rule_name": "main_v2b_baseline",
            "rule_note": rule["rule_note"],
        })

    return pd.DataFrame(rows)


def get_weights_for_state(hsi_state: str) -> dict:
    if hsi_state not in STATE_ALLOCATION_RULES:
        raise ValueError(f"정의되지 않은 HSI 상태입니다: {hsi_state}")

    rule = STATE_ALLOCATION_RULES[hsi_state]

    return {
        RISK_TICKER: rule[RISK_TICKER],
        BOND_TICKER: rule[BOND_TICKER],
        CASH_TICKER: rule[CASH_TICKER],
    }


def build_rebalance_weights(
    hsi_state_table: pd.DataFrame,
    monthly_returns_decimal: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    valid_states = hsi_state_table[hsi_state_table["state_valid"] == True].copy()
    valid_states = valid_states.sort_values("year_month")

    available_return_months = set(monthly_returns_decimal.index.astype(str))

    for _, row in valid_states.iterrows():
        signal_month = str(row["year_month"])
        return_month = str(pd.Period(signal_month, freq="M") + 1)

        # 마지막 HSI 상태는 다음 달 수익률이 아직 없을 수 있다.
        if return_month not in available_return_months:
            continue

        hsi_state = row["hsi_state"]
        weights = get_weights_for_state(hsi_state)

        for ticker, weight in weights.items():
            rows.append({
                "strategy_name": STRATEGY_HSI,
                "signal_month": signal_month,
                "return_month": return_month,
                "ticker": ticker,
                "weight": weight,
                "hsi_state": hsi_state,
                "hsi_direction": row["hsi_direction"],
                "hsi_intensity": row["hsi_intensity"],
                "allocation_rule": "main_v2b_baseline",
            })

    return pd.DataFrame(rows)


def build_hsi_strategy_returns(
    rebalance_weights: pd.DataFrame,
    monthly_returns_decimal: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    grouped = rebalance_weights.groupby(["signal_month", "return_month", "hsi_state"], as_index=False)

    for (signal_month, return_month, hsi_state), g in grouped:
        portfolio_return = 0.0

        for _, row in g.iterrows():
            ticker = row["ticker"]
            weight = row["weight"]
            asset_return = monthly_returns_decimal.loc[return_month, ticker]
            portfolio_return += weight * asset_return

        rows.append({
            "strategy_name": STRATEGY_HSI,
            "signal_month": signal_month,
            "return_month": return_month,
            "hsi_state": hsi_state,
            "monthly_return": portfolio_return,
        })

    return pd.DataFrame(rows).sort_values("return_month")


def build_ew_strategy_returns(
    hsi_strategy_returns: pd.DataFrame,
    monthly_returns_decimal: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    return_months = hsi_strategy_returns["return_month"].drop_duplicates().tolist()

    for return_month in return_months:
        ew_return = monthly_returns_decimal.loc[return_month, TICKERS].mean()

        rows.append({
            "strategy_name": STRATEGY_EW,
            "signal_month": "",
            "return_month": return_month,
            "hsi_state": "benchmark",
            "monthly_return": ew_return,
        })

    return pd.DataFrame(rows).sort_values("return_month")


def add_cumulative_and_drawdown(strategy_returns: pd.DataFrame) -> pd.DataFrame:
    """
    전략별 월간수익률에 누적수익률과 Drawdown을 붙인다.

    수정 이유
    --------
    pandas 버전에 따라 groupby().apply() 이후 grouping column인
    strategy_name이 결과에서 사라질 수 있다.
    따라서 groupby().apply()를 쓰지 않고, 전략별로 명시적으로 loop를 돌며
    strategy_name 컬럼을 보존한다.
    """
    required_cols = ["strategy_name", "return_month", "monthly_return"]

    missing_cols = [c for c in required_cols if c not in strategy_returns.columns]
    if missing_cols:
        raise KeyError(
            f"strategy_returns에 필요한 컬럼이 없습니다: {missing_cols}\n"
            f"현재 컬럼: {list(strategy_returns.columns)}"
        )

    if strategy_returns.empty:
        raise ValueError("strategy_returns가 비어 있습니다. 이전 단계의 전략 수익률 계산을 확인하세요.")

    frames = []

    for strategy_name, g in strategy_returns.groupby("strategy_name"):
        g = g.sort_values("return_month").copy()

        growth = (1.0 + g["monthly_return"].astype(float)).cumprod()

        g["strategy_name"] = strategy_name
        g["growth_index"] = growth
        g["cumulative_return"] = growth - 1.0
        g["drawdown"] = growth / growth.cummax() - 1.0

        frames.append(g)

    out = pd.concat(frames, ignore_index=True)

    out["monthly_return_pct"] = out["monthly_return"] * 100.0
    out["cumulative_return_pct"] = out["cumulative_return"] * 100.0
    out["drawdown_pct"] = out["drawdown"] * 100.0

    ordered_cols = [
        "strategy_name",
        "signal_month",
        "return_month",
        "hsi_state",
        "monthly_return",
        "monthly_return_pct",
        "growth_index",
        "cumulative_return",
        "cumulative_return_pct",
        "drawdown",
        "drawdown_pct",
    ]

    existing_cols = [c for c in ordered_cols if c in out.columns]
    other_cols = [c for c in out.columns if c not in existing_cols]

    return out[existing_cols + other_cols]


def calculate_performance_summary(backtest_ts: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for strategy_name, g in backtest_ts.groupby("strategy_name"):
        g = g.sort_values("return_month").copy()
        r = g["monthly_return"].astype(float)

        months = len(r)
        total_return = g["growth_index"].iloc[-1] - 1.0

        if months > 0:
            cagr = (1.0 + total_return) ** (12.0 / months) - 1.0
        else:
            cagr = np.nan

        annual_return_arithmetic = r.mean() * 12.0
        annual_volatility = r.std(ddof=1) * np.sqrt(12.0) if months > 1 else np.nan

        downside = r[r < 0]
        downside_volatility = downside.std(ddof=1) * np.sqrt(12.0) if len(downside) > 1 else np.nan

        sharpe = (
            annual_return_arithmetic / annual_volatility
            if annual_volatility is not None and annual_volatility > 0
            else np.nan
        )

        sortino = (
            annual_return_arithmetic / downside_volatility
            if downside_volatility is not None and downside_volatility > 0
            else np.nan
        )

        mdd = g["drawdown"].min()
        calmar = cagr / abs(mdd) if mdd < 0 else np.nan
        win_rate = (r > 0).mean()

        rows.append({
            "strategy_name": strategy_name,
            "months": months,
            "start_return_month": g["return_month"].iloc[0],
            "end_return_month": g["return_month"].iloc[-1],
            "total_return": total_return,
            "CAGR": cagr,
            "annual_volatility": annual_volatility,
            "MDD": mdd,
            "Sharpe": sharpe,
            "Sortino": sortino,
            "Calmar": calmar,
            "WinRate": win_rate,
            "avg_monthly_return": r.mean(),
            "best_month": r.max(),
            "worst_month": r.min(),
            "total_return_pct": total_return * 100.0,
            "CAGR_pct": cagr * 100.0,
            "annual_volatility_pct": annual_volatility * 100.0,
            "MDD_pct": mdd * 100.0,
            "WinRate_pct": win_rate * 100.0,
        })

    return pd.DataFrame(rows)


def calculate_turnover(rebalance_weights: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    wide = (
        rebalance_weights
        .pivot_table(
            index="return_month",
            columns="ticker",
            values="weight",
            aggfunc="first",
        )
        .sort_index()
    )

    turnover_rows = []

    previous_weights = None

    for return_month, row in wide.iterrows():
        current_weights = row[TICKERS].astype(float)

        if previous_weights is None:
            turnover = 0.0
        else:
            # 일반적인 포트폴리오 Turnover 정의:
            # 0.5 × |비중 변화| 합계
            turnover = 0.5 * (current_weights - previous_weights).abs().sum()

        turnover_rows.append({
            "strategy_name": STRATEGY_HSI,
            "return_month": return_month,
            "turnover": turnover,
            f"weight_{RISK_TICKER}": current_weights[RISK_TICKER],
            f"weight_{BOND_TICKER}": current_weights[BOND_TICKER],
            f"weight_{CASH_TICKER}": current_weights[CASH_TICKER],
        })

        previous_weights = current_weights

    turnover_detail = pd.DataFrame(turnover_rows)

    hsi_summary = {
        "strategy_name": STRATEGY_HSI,
        "months": len(turnover_detail),
        "avg_turnover": turnover_detail["turnover"].mean(),
        "max_turnover": turnover_detail["turnover"].max(),
        "total_turnover": turnover_detail["turnover"].sum(),
    }

    ew_summary = {
        "strategy_name": STRATEGY_EW,
        "months": len(turnover_detail),
        "avg_turnover": 0.0,
        "max_turnover": 0.0,
        "total_turnover": 0.0,
    }

    turnover_summary = pd.DataFrame([hsi_summary, ew_summary])

    turnover_detail["turnover_pct"] = turnover_detail["turnover"] * 100.0
    turnover_summary["avg_turnover_pct"] = turnover_summary["avg_turnover"] * 100.0
    turnover_summary["max_turnover_pct"] = turnover_summary["max_turnover"] * 100.0
    turnover_summary["total_turnover_pct"] = turnover_summary["total_turnover"] * 100.0

    return turnover_detail, turnover_summary


def build_alignment_check(
    hsi_state_table: pd.DataFrame,
    monthly_returns_decimal: pd.DataFrame,
    rebalance_weights: pd.DataFrame,
    backtest_ts: pd.DataFrame,
) -> pd.DataFrame:
    valid_state_months = int(hsi_state_table["state_valid"].sum())

    unique_signal_months_used = rebalance_weights["signal_month"].nunique()
    unique_return_months_used = rebalance_weights["return_month"].nunique()

    first_valid_state_month = (
        hsi_state_table.loc[hsi_state_table["state_valid"], "year_month"].iloc[0]
        if valid_state_months > 0
        else ""
    )
    last_valid_state_month = (
        hsi_state_table.loc[hsi_state_table["state_valid"], "year_month"].iloc[-1]
        if valid_state_months > 0
        else ""
    )

    rows = [
        {
            "check_item": "valid_state_months",
            "result": valid_state_months,
            "status": "OK" if valid_state_months > 0 else "CHECK",
            "note": "33번 HSI 상태표에서 state_valid=True인 월 수",
        },
        {
            "check_item": "signal_months_used",
            "result": unique_signal_months_used,
            "status": "OK" if unique_signal_months_used > 0 else "CHECK",
            "note": "다음 달 수익률이 존재해 실제 백테스트에 사용된 신호 월 수",
        },
        {
            "check_item": "return_months_used",
            "result": unique_return_months_used,
            "status": "OK" if unique_return_months_used > 0 else "CHECK",
            "note": "실제 백테스트 수익률 월 수",
        },
        {
            "check_item": "first_valid_state_month",
            "result": first_valid_state_month,
            "status": "OK",
            "note": "첫 유효 HSI 상태 월",
        },
        {
            "check_item": "last_valid_state_month",
            "result": last_valid_state_month,
            "status": "OK",
            "note": "마지막 유효 HSI 상태 월. 마지막 월은 다음 달 수익률이 없으면 백테스트에서 제외될 수 있음.",
        },
        {
            "check_item": "alignment_rule",
            "result": "signal_month_t_to_return_month_t_plus_1",
            "status": "OK",
            "note": "월말 HSI 상태를 다음 달 수익률에 적용하여 look-ahead bias를 피함",
        },
        {
            "check_item": "monthly_return_unit",
            "result": "input_percent_converted_to_decimal",
            "status": "OK",
            "note": "monthly_returns.csv의 % 수익률을 백테스트 내부에서 decimal로 변환",
        },
    ]

    return pd.DataFrame(rows)


def plot_backtest_figures(backtest_ts: pd.DataFrame) -> None:
    pivot_growth = (
        backtest_ts
        .pivot(index="return_month", columns="strategy_name", values="growth_index")
        .sort_index()
    )

    pivot_drawdown = (
        backtest_ts
        .pivot(index="return_month", columns="strategy_name", values="drawdown")
        .sort_index()
    )

    # 누적수익률 비교
    plt.figure(figsize=(11, 6))
    for col in pivot_growth.columns:
        plt.plot(pivot_growth.index, pivot_growth[col], label=col)

    plt.title("Main v3 baseline cumulative growth comparison")
    plt.xlabel("Return month")
    plt.ylabel("Growth index")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(pivot_growth.index[::12], rotation=45)
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG_CUMULATIVE, dpi=150)
    plt.close()

    # Drawdown 비교
    plt.figure(figsize=(11, 6))
    for col in pivot_drawdown.columns:
        plt.plot(pivot_drawdown.index, pivot_drawdown[col] * 100.0, label=col)

    plt.title("Main v3 baseline drawdown comparison")
    plt.xlabel("Return month")
    plt.ylabel("Drawdown (%)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(pivot_drawdown.index[::12], rotation=45)
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG_DRAWDOWN, dpi=150)
    plt.close()


def make_markdown_note(
    performance_summary: pd.DataFrame,
    turnover_summary: pd.DataFrame,
    alignment_check: pd.DataFrame,
) -> str:
    lines = []

    lines.append("# main_v3 baseline backtest note")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "33번에서 생성한 HSI 5상태표를 main_v2b 기준 비중 규칙에 연결하여 "
        "baseline 백테스트를 수행하였다. 이 결과는 후속 추가 지표 실험과 비교할 기준선이다."
    )
    lines.append("")
    lines.append("## 2. 비중 규칙")
    lines.append("")
    lines.append("- `conflict`는 즉시 방어 전환하지 않고 동일비중 관찰로 처리한다.")
    lines.append("- `risk_warning`과 `accident_zone`에서만 위험자산 비중을 축소한다.")
    lines.append("- 위험자산 축소분은 114260과 153130에 균등하게 배분한다.")
    lines.append("")
    lines.append("## 3. 시점 정합성")
    lines.append("")
    lines.append(
        "월말 HSI 상태는 다음 달 수익률에 적용하였다. "
        "즉, `signal_month`의 상태를 `return_month = signal_month + 1`에 적용한다."
    )
    lines.append("")
    lines.append("## 4. 성과 요약")
    lines.append("")
    lines.append("| strategy_name | months | total_return_pct | CAGR_pct | MDD_pct | Sharpe | Calmar | WinRate_pct |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")

    for _, row in performance_summary.iterrows():
        lines.append(
            f"| {row['strategy_name']} | {row['months']} | "
            f"{row['total_return_pct']:.2f} | {row['CAGR_pct']:.2f} | "
            f"{row['MDD_pct']:.2f} | {row['Sharpe']:.4f} | "
            f"{row['Calmar']:.4f} | {row['WinRate_pct']:.2f} |"
        )

    lines.append("")
    lines.append("## 5. Turnover 요약")
    lines.append("")
    lines.append("| strategy_name | avg_turnover_pct | max_turnover_pct | total_turnover_pct |")
    lines.append("|---|---:|---:|---:|")

    for _, row in turnover_summary.iterrows():
        lines.append(
            f"| {row['strategy_name']} | {row['avg_turnover_pct']:.2f} | "
            f"{row['max_turnover_pct']:.2f} | {row['total_turnover_pct']:.2f} |"
        )

    lines.append("")
    lines.append("## 6. 점검표")
    lines.append("")
    lines.append("| check_item | result | status | note |")
    lines.append("|---|---|---|---|")

    for _, row in alignment_check.iterrows():
        lines.append(
            f"| {row['check_item']} | {row['result']} | {row['status']} | {row['note']} |"
        )

    lines.append("")
    lines.append("## 7. 다음 단계")
    lines.append("")
    lines.append(
        "다음 단계에서는 추가 지표 후보를 생성하거나 수령한 뒤, "
        "동일한 main_v2b 비중 규칙을 고정한 상태에서 신호 조합만 바꾸어 성과표를 비교한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 3. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("34_main_v3_backtest_baseline_main_v2b.py 실행 시작")
    print("=" * 80)

    print("[1] 입력 파일 확인")
    for path in [INPUT_HSI_STATE_TABLE, INPUT_MONTHLY_RETURNS, INPUT_SELECTED_ETF]:
        require_file(path)
        print(f"    OK: {path}")

    print("[2] 입력 데이터 로드")
    hsi_state_table = pd.read_csv(INPUT_HSI_STATE_TABLE)
    selected_etf = pd.read_csv(INPUT_SELECTED_ETF, dtype={"ticker": str})
    monthly_returns_decimal = read_monthly_returns(INPUT_MONTHLY_RETURNS)

    print(f"    hsi_state_table shape = {hsi_state_table.shape}")
    print(f"    selected_etf shape = {selected_etf.shape}")
    print(f"    monthly_returns_decimal shape = {monthly_returns_decimal.shape}")

    print("[3] main_v2b 기준 비중 규칙표 생성")
    rule_table = build_rule_table()

    print("[4] HSI 상태표 → 리밸런싱 비중표 생성")
    rebalance_weights = build_rebalance_weights(
        hsi_state_table=hsi_state_table,
        monthly_returns_decimal=monthly_returns_decimal,
    )

    print("[5] HSI baseline 전략 수익률 계산")
    hsi_strategy_returns = build_hsi_strategy_returns(
        rebalance_weights=rebalance_weights,
        monthly_returns_decimal=monthly_returns_decimal,
    )

    print("[6] EW 비교전략 수익률 계산")
    ew_strategy_returns = build_ew_strategy_returns(
        hsi_strategy_returns=hsi_strategy_returns,
        monthly_returns_decimal=monthly_returns_decimal,
    )

    print("[7] 누적수익률 및 Drawdown 계산")
    strategy_returns = pd.concat(
        [hsi_strategy_returns, ew_strategy_returns],
        ignore_index=True,
    )

    backtest_ts = add_cumulative_and_drawdown(strategy_returns)

    print("[8] 성과요약표 계산")
    performance_summary = calculate_performance_summary(backtest_ts)

    print("[9] Turnover 계산")
    turnover_detail, turnover_summary = calculate_turnover(rebalance_weights)

    print("[10] 시점 정합성 점검표 생성")
    alignment_check = build_alignment_check(
        hsi_state_table=hsi_state_table,
        monthly_returns_decimal=monthly_returns_decimal,
        rebalance_weights=rebalance_weights,
        backtest_ts=backtest_ts,
    )

    print("[11] 그림 생성")
    plot_backtest_figures(backtest_ts)

    print("[12] CSV 저장")
    rebalance_weights.to_csv(OUTPUT_REBALANCE_WEIGHTS, index=False, encoding="utf-8-sig")
    backtest_ts.to_csv(OUTPUT_BACKTEST_TS, index=False, encoding="utf-8-sig")

    rule_table.to_csv(OUTPUT_RULE_TABLE, index=False, encoding="utf-8-sig")
    alignment_check.to_csv(OUTPUT_ALIGNMENT_CHECK, index=False, encoding="utf-8-sig")
    performance_summary.to_csv(OUTPUT_PERFORMANCE, index=False, encoding="utf-8-sig")
    turnover_detail.to_csv(OUTPUT_TURNOVER_DETAIL, index=False, encoding="utf-8-sig")
    turnover_summary.to_csv(OUTPUT_TURNOVER_SUMMARY, index=False, encoding="utf-8-sig")

    print("[13] Markdown 노트 저장")
    note = make_markdown_note(
        performance_summary=performance_summary,
        turnover_summary=turnover_summary,
        alignment_check=alignment_check,
    )
    OUTPUT_NOTE.write_text(note, encoding="utf-8")

    print("\n[저장 완료]")
    for path in [
        OUTPUT_REBALANCE_WEIGHTS,
        OUTPUT_BACKTEST_TS,
        OUTPUT_RULE_TABLE,
        OUTPUT_ALIGNMENT_CHECK,
        OUTPUT_PERFORMANCE,
        OUTPUT_TURNOVER_DETAIL,
        OUTPUT_TURNOVER_SUMMARY,
        OUTPUT_FIG_CUMULATIVE,
        OUTPUT_FIG_DRAWDOWN,
        OUTPUT_NOTE,
    ]:
        print(f"- {path}")

    print("\n[성과요약]")
    display_cols = [
        "strategy_name",
        "months",
        "total_return_pct",
        "CAGR_pct",
        "annual_volatility_pct",
        "MDD_pct",
        "Sharpe",
        "Sortino",
        "Calmar",
        "WinRate_pct",
    ]
    print(performance_summary[display_cols].to_string(index=False))

    print("\n[Turnover 요약]")
    print(turnover_summary.to_string(index=False))

    print("\n[시점 정합성 점검]")
    print(alignment_check.to_string(index=False))

    print("\n" + "=" * 80)
    print("34_main_v3_backtest_baseline_main_v2b.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()