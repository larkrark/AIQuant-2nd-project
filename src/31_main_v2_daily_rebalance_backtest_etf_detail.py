"""
25_main_v2_daily_rebalance_backtest_etf_detail.py

목적
----
기존 월별 백테스트(legacy/17_main_v2_backtest_hsi_state5_overlay.py)를
일별 리밸런싱 방식으로 확장한 새 스크립트.
기존 파일은 수정하지 않고, 산출물도 모두 새 이름으로 저장한다.

원본(17번) 대비 수정사항 요약
----------------------------
[수정 1] 수익률 입력 변경
    - 원본: data/processed/monthly_returns.csv (월간 수익률)
    - 변경: data/processed/korea_etf_price_clean.csv (일별 가격) → 일별 수익률 계산

[수정 2] 리밸런싱 주기 변경 (월별 → 일별)
    - 원본: 월말 비중을 다음 달 "월간 수익률" 1개에 적용 (월 1회 리밸런싱)
    - 변경: 월말 비중을 다음 달의 "모든 거래일"에 적용하고,
            매 거래일 종가 기준으로 목표 비중으로 재조정(일별 리밸런싱)
    - look-ahead 방어 원칙(Date=t 신호 → t+1월 수익률 적용)은 그대로 유지

[수정 3] Turnover 계산 변경
    - 원본: 월별 목표 비중 변화량 기준 turnover = 0.5 * sum|w_t - w_{t-1}|
    - 변경: 일별 리밸런싱 기준 turnover
            = 0.5 * sum|당일 목표비중 - 전일 종가 기준 drift 비중|
            (drift 비중 = w * (1+r_i) / (1+r_p), 월 경계의 비중 변경도 자동 포함)

[수정 4] ETF 수익 상세 표 신규 출력
    - 일별 상세: ETF별 비중·일수익률·기여도·누적수익률
    - 월별 상세: ETF별 월수익률·평균 비중·월 기여도 + 전략 월수익률 (콘솔 출력 포함)
    - ETF 요약: ETF별 누적수익률·CAGR·변동성·MDD·승률·평균비중·총기여도

[수정 5] 성과지표 연율화 기준 변경 (12개월 → 252거래일)

입력
----
output/tables/main_v2_hsi_state5_table_rank.csv
output/tables/main_v2_hsi_state5_table_zscore.csv
data/processed/korea_etf_price_clean.csv

출력 (모두 신규 파일, 기존 산출물 덮어쓰지 않음)
----
output/tables/main_v2_daily_backtest_timeseries_{method}.csv
output/tables/main_v2_daily_etf_detail_daily_{method}.csv
output/tables/main_v2_daily_etf_detail_monthly_{method}.csv
output/tables/main_v2_daily_etf_summary_{method}.csv
output/tables/main_v2_daily_performance_summary.csv
output/tables/main_v2_daily_alignment_check.csv
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Windows 콘솔(cp949)에서 한글/특수문자 출력 오류 방지
if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

STATE5_RANK_PATH = TABLE_DIR / "main_v2_hsi_state5_table_rank.csv"
STATE5_ZSCORE_PATH = TABLE_DIR / "main_v2_hsi_state5_table_zscore.csv"

# [수정 1] 월간 수익률 파일 대신 일별 가격 파일을 입력으로 사용
DAILY_PRICE_PATH = PROCESSED_DIR / "korea_etf_price_clean.csv"

OUTPUT_BACKTEST_PATH = TABLE_DIR / "main_v2_daily_backtest_timeseries_{method}.csv"
OUTPUT_ETF_DAILY_PATH = TABLE_DIR / "main_v2_daily_etf_detail_daily_{method}.csv"
OUTPUT_ETF_MONTHLY_PATH = TABLE_DIR / "main_v2_daily_etf_detail_monthly_{method}.csv"
OUTPUT_ETF_SUMMARY_PATH = TABLE_DIR / "main_v2_daily_etf_summary_{method}.csv"
OUTPUT_PERFORMANCE_PATH = TABLE_DIR / "main_v2_daily_performance_summary.csv"
OUTPUT_ALIGNMENT_CHECK_PATH = TABLE_DIR / "main_v2_daily_alignment_check.csv"


# ============================================================
# 1. 실험 설정
# ============================================================

ASSETS = ["069500", "114260", "153130"]

ETF_NAMES = {
    "069500": "KODEX 200 (주식)",
    "114260": "KODEX 국고채3년 (채권)",
    "153130": "KODEX 단기채권 (현금성)",
}

WEIGHT_COLS = {asset: f"{asset}_weight" for asset in ASSETS}

INITIAL_CAPITAL = 1.0

# [수정 5] 연율화 기준: 월별(12) → 일별(252 거래일)
TRADING_DAYS_PER_YEAR = 252

STRATEGIES = ["EW", "HSI_state5_overlay"]


# ============================================================
# 2. 데이터 로드
# ============================================================

def load_state5(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])

    required = ["Date", "hsi_state5"] + list(WEIGHT_COLS.values())
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"state5에 필요한 컬럼이 없습니다: {missing}")

    weight_sum = df[list(WEIGHT_COLS.values())].sum(axis=1)
    if not np.allclose(weight_sum, 1.0):
        raise ValueError("비중 합계가 1.0이 아닌 행이 있습니다.")

    return df.sort_values("Date").reset_index(drop=True)


def load_daily_returns() -> pd.DataFrame:
    """
    [수정 1] 일별 가격 → 일별 수익률 계산.
    """
    if not DAILY_PRICE_PATH.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {DAILY_PRICE_PATH}")

    prices = pd.read_csv(DAILY_PRICE_PATH, index_col=0, parse_dates=True)

    missing = [asset for asset in ASSETS if asset not in prices.columns]
    if missing:
        raise ValueError(f"일별 가격에 필요한 ETF 컬럼이 없습니다: {missing}")

    prices = prices[ASSETS].dropna().sort_index()
    daily_returns = prices.pct_change().dropna()
    daily_returns.index.name = "Date"

    return daily_returns


# ============================================================
# 3. 월말 HSI 신호 → 다음 달 "모든 거래일"에 정렬
# ============================================================

def build_daily_target_weights(state5: pd.DataFrame, daily_returns: pd.DataFrame) -> pd.DataFrame:
    """
    [수정 2] 원본은 Date=t 신호를 t+1월의 월간 수익률 1개에 붙였다.
    여기서는 Date=t(월말) 신호의 비중을 t+1월의 모든 거래일에 목표 비중으로 매핑한다.
    look-ahead 방어(신호는 항상 다음 달에만 적용)는 동일하게 유지된다.
    """
    signal = state5.copy()
    signal["signal_month"] = signal["Date"].dt.to_period("M")
    # 신호 월 + 1 = 수익률 적용 월
    signal["apply_month"] = signal["signal_month"] + 1

    daily = daily_returns.reset_index()
    daily["apply_month"] = daily["Date"].dt.to_period("M")

    keep_cols = (
        ["apply_month", "hsi_state5"]
        + [c for c in ["state_name_kr", "state_reason", "action"] if c in signal.columns]
        + list(WEIGHT_COLS.values())
    )
    signal_slim = signal[["Date"] + keep_cols].rename(columns={"Date": "signal_date"})

    merged = daily.merge(signal_slim, on="apply_month", how="inner")
    merged = merged.sort_values("Date").reset_index(drop=True)

    return merged


def make_alignment_check(aligned: pd.DataFrame, method: str) -> dict:
    return {
        "method": method,
        "trading_days": len(aligned),
        "first_signal_date": aligned["signal_date"].min(),
        "last_signal_date": aligned["signal_date"].max(),
        "first_return_date": aligned["Date"].min(),
        "last_return_date": aligned["Date"].max(),
        "missing_return_cells": int(aligned[ASSETS].isna().sum().sum()),
        "alignment_rule": "월말 signal_date의 HSI 비중을 다음 달 모든 거래일의 일별 수익률에 적용",
        "alignment_flag": "OK",
    }


# ============================================================
# 4. 일별 리밸런싱 백테스트
# ============================================================

def get_target_weights(aligned: pd.DataFrame, strategy: str) -> np.ndarray:
    if strategy == "EW":
        return np.full((len(aligned), len(ASSETS)), 1.0 / len(ASSETS))

    if strategy == "HSI_state5_overlay":
        return aligned[[WEIGHT_COLS[a] for a in ASSETS]].to_numpy()

    raise ValueError(f"알 수 없는 전략입니다: {strategy}")


def calculate_daily_turnover(target: np.ndarray, returns: np.ndarray, port_ret: np.ndarray) -> np.ndarray:
    """
    [수정 3] 일별 리밸런싱 turnover.
    전일 목표 비중이 하루 수익률로 drift한 비중과 당일 목표 비중의 차이를 거래량으로 본다.
        drift_w = w * (1 + r_i) / (1 + r_p)
        turnover_t = 0.5 * sum|target_t - drift_{t-1}|
    첫날은 0으로 둔다(원본의 '첫 달 0' 규칙과 동일).
    """
    drift = target * (1.0 + returns) / (1.0 + port_ret)[:, None]
    turnover = np.zeros(len(target))
    diff = np.abs(target[1:] - drift[:-1])
    turnover[1:] = 0.5 * diff.sum(axis=1)
    return turnover


def build_daily_backtest(aligned: pd.DataFrame, method: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    [수정 2] 일별 리밸런싱: 매 거래일 목표 비중으로 재조정하므로
    일별 전략수익률 = sum(목표비중 × 당일 ETF 수익률).
    반환: (전략 일별 시계열, ETF 일별 상세)
    """
    returns = aligned[ASSETS].to_numpy()

    backtest_parts = []
    detail_parts = []

    for strategy in STRATEGIES:
        target = get_target_weights(aligned, strategy)
        port_ret = (target * returns).sum(axis=1)
        turnover = calculate_daily_turnover(target, returns, port_ret)

        cumulative = np.cumprod(1.0 + port_ret) * INITIAL_CAPITAL
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative / running_max - 1.0

        ts = pd.DataFrame({
            "method": method,
            "strategy": strategy,
            "signal_date": aligned["signal_date"].values,
            "Date": aligned["Date"].values,
            "hsi_state5": aligned["hsi_state5"].values,
            "state_name_kr": aligned.get("state_name_kr", pd.Series(np.nan, index=aligned.index)).values,
            "action": aligned.get("action", pd.Series(np.nan, index=aligned.index)).values,
            "daily_return": port_ret,
            "turnover": turnover,
            "cumulative_return": cumulative,
            "running_max": running_max,
            "drawdown": drawdown,
        })
        backtest_parts.append(ts)

        # [수정 4] ETF 일별 상세: 비중·일수익률·기여도·ETF 자체 누적수익률
        detail = pd.DataFrame({
            "method": method,
            "strategy": strategy,
            "Date": aligned["Date"].values,
            "hsi_state5": aligned["hsi_state5"].values,
        })
        for i, asset in enumerate(ASSETS):
            detail[f"{asset}_weight"] = target[:, i]
            detail[f"{asset}_daily_return"] = returns[:, i]
            detail[f"{asset}_contribution"] = target[:, i] * returns[:, i]
            detail[f"{asset}_cum_return"] = np.cumprod(1.0 + returns[:, i])
        detail["strategy_daily_return"] = port_ret
        detail_parts.append(detail)

    return (
        pd.concat(backtest_parts, ignore_index=True),
        pd.concat(detail_parts, ignore_index=True),
    )


# ============================================================
# 5. ETF 수익 상세 표 (월별 집계 + 전체 요약)
# ============================================================

def build_etf_monthly_detail(etf_daily: pd.DataFrame) -> pd.DataFrame:
    """
    [수정 4] ETF 수익 상세 표(월별).
    ETF별 월수익률(일별 복리), 평균 비중, 월 기여도 합, 전략 월수익률.
    """
    df = etf_daily.copy()
    df["year_month"] = pd.to_datetime(df["Date"]).dt.to_period("M").astype(str)

    rows = []
    for (method, strategy, ym), g in df.groupby(["method", "strategy", "year_month"]):
        row = {
            "method": method,
            "strategy": strategy,
            "year_month": ym,
            "trading_days": len(g),
            "hsi_state5": g["hsi_state5"].iloc[0],
        }
        for asset in ASSETS:
            row[f"{asset}_month_return_pct"] = ((1.0 + g[f"{asset}_daily_return"]).prod() - 1.0) * 100
            row[f"{asset}_avg_weight_pct"] = g[f"{asset}_weight"].mean() * 100
            row[f"{asset}_contribution_pct"] = g[f"{asset}_contribution"].sum() * 100
        row["strategy_month_return_pct"] = ((1.0 + g["strategy_daily_return"]).prod() - 1.0) * 100
        rows.append(row)

    out = pd.DataFrame(rows)
    return out.sort_values(["method", "strategy", "year_month"]).reset_index(drop=True)


def calc_mdd(returns: pd.Series) -> float:
    cumulative = (1.0 + returns).cumprod()
    return float((cumulative / cumulative.cummax() - 1.0).min())


def build_etf_summary(etf_daily: pd.DataFrame) -> pd.DataFrame:
    """
    [수정 4] ETF 전체 기간 요약: 누적수익률·CAGR·변동성·MDD·승률·평균비중·총기여도.
    """
    rows = []
    for (method, strategy), g in etf_daily.groupby(["method", "strategy"]):
        n_days = len(g)
        for asset in ASSETS:
            r = g[f"{asset}_daily_return"]
            final_cum = float((1.0 + r).prod())
            cagr = final_cum ** (TRADING_DAYS_PER_YEAR / n_days) - 1.0
            ann_vol = r.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
            rows.append({
                "method": method,
                "strategy": strategy,
                "ticker": asset,
                "etf_name": ETF_NAMES[asset],
                "trading_days": n_days,
                "final_cumulative_return": final_cum,
                "CAGR_pct": cagr * 100,
                "annual_volatility_pct": ann_vol * 100,
                "MDD_pct": calc_mdd(r) * 100,
                "WinRate_pct": (r > 0).mean() * 100,
                "avg_weight_pct": g[f"{asset}_weight"].mean() * 100,
                "total_contribution_pct": g[f"{asset}_contribution"].sum() * 100,
            })
    return pd.DataFrame(rows)


def build_performance_summary(backtest: pd.DataFrame) -> pd.DataFrame:
    """
    전략 단위 성과 요약. [수정 5] 일별 수익률 기준 연율화(252일).
    """
    rows = []
    for (method, strategy), g in backtest.groupby(["method", "strategy"]):
        r = g["daily_return"]
        n_days = len(g)
        final_cum = float(g["cumulative_return"].iloc[-1])
        cagr = final_cum ** (TRADING_DAYS_PER_YEAR / n_days) - 1.0
        ann_vol = r.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
        ann_mean = r.mean() * TRADING_DAYS_PER_YEAR
        sharpe = ann_mean / ann_vol if ann_vol > 0 else np.nan
        mdd = float(g["drawdown"].min())
        rows.append({
            "method": method,
            "strategy": strategy,
            "rebalance": "daily",
            "trading_days": n_days,
            "final_cumulative_return": final_cum,
            "CAGR_pct": cagr * 100,
            "annual_volatility_pct": ann_vol * 100,
            "MDD_pct": mdd * 100,
            "Sharpe": sharpe,
            "Calmar": cagr / abs(mdd) if mdd < 0 else np.nan,
            "WinRate_pct": (r > 0).mean() * 100,
            "avg_daily_turnover_pct": g["turnover"].mean() * 100,
            "total_turnover_pct": g["turnover"].sum() * 100,
        })
    return pd.DataFrame(rows)


# ============================================================
# 6. 저장/출력 유틸
# ============================================================

def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"- 저장: {path}")


# ============================================================
# 7. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("25_main_v2_daily_rebalance_backtest_etf_detail.py 실행 시작")
    print("(월별 리밸런싱 → 일별 리밸런싱 / ETF 수익 상세 표 출력)")
    print("=" * 70)

    daily_returns = load_daily_returns()
    print(f"[일별 수익률] {daily_returns.shape[0]}거래일 "
          f"({daily_returns.index.min().date()} ~ {daily_returns.index.max().date()})")

    alignment_rows = []
    performance_parts = []

    for method, state5_path in [("rank", STATE5_RANK_PATH), ("zscore", STATE5_ZSCORE_PATH)]:
        print(f"\n[{method}] 처리 시작")

        state5 = load_state5(state5_path)
        aligned = build_daily_target_weights(state5, daily_returns)
        alignment_rows.append(make_alignment_check(aligned, method))
        print(f"- 신호-수익률 정렬: {len(aligned)}거래일 "
              f"({aligned['Date'].min().date()} ~ {aligned['Date'].max().date()})")

        backtest, etf_daily = build_daily_backtest(aligned, method)
        etf_monthly = build_etf_monthly_detail(etf_daily)
        etf_summary = build_etf_summary(etf_daily)
        performance_parts.append(build_performance_summary(backtest))

        save_csv(backtest, Path(str(OUTPUT_BACKTEST_PATH).format(method=method)))
        save_csv(etf_daily, Path(str(OUTPUT_ETF_DAILY_PATH).format(method=method)))
        save_csv(etf_monthly, Path(str(OUTPUT_ETF_MONTHLY_PATH).format(method=method)))
        save_csv(etf_summary, Path(str(OUTPUT_ETF_SUMMARY_PATH).format(method=method)))

        # [수정 4] ETF 수익 상세 표 콘솔 출력
        overlay_monthly = etf_monthly[etf_monthly["strategy"] == "HSI_state5_overlay"]
        print(f"\n[{method}] ETF 수익 상세 표 - HSI overlay 최근 12개월 (월별, %)")
        show_cols = (
            ["year_month", "hsi_state5"]
            + [f"{a}_month_return_pct" for a in ASSETS]
            + [f"{a}_avg_weight_pct" for a in ASSETS]
            + [f"{a}_contribution_pct" for a in ASSETS]
            + ["strategy_month_return_pct"]
        )
        print(overlay_monthly[show_cols].tail(12).round(3).to_string(index=False))

        print(f"\n[{method}] ETF 전체 기간 요약")
        print(etf_summary.round(3).to_string(index=False))

    alignment_check = pd.DataFrame(alignment_rows)
    performance_summary = pd.concat(performance_parts, ignore_index=True)

    print("\n[공통 산출물]")
    save_csv(alignment_check, OUTPUT_ALIGNMENT_CHECK_PATH)
    save_csv(performance_summary, OUTPUT_PERFORMANCE_PATH)

    print("\n[전략 성과 요약 - 일별 리밸런싱, 연율화 252일 기준]")
    print(performance_summary.round(3).to_string(index=False))

    print("\n" + "=" * 70)
    print("25_main_v2_daily_rebalance_backtest_etf_detail.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()
