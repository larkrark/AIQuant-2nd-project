# -*- coding: utf-8 -*-
"""
common.py — 공통 엔진

핵심 규약 (v2 문서 고정 사항):
1) 타이밍: t월 말 신호로 산출한 목표비중 w*_t 는 t+1월 수익률에 적용된다.
   구현: 적용월 m의 비중 w_m = w_{m-1} + λ_dir · (w*_{signal=m-1} − w_{m-1}).
   λ_dir 판정에 쓰이는 정보는 전부 m-1월 말까지 관측 가능한 값이다. (look-ahead 방지)
2) 방향 판정: Δ_t = w*_{RISK,t} − w_{RISK,t-1} (직전 '실제' 비중 기준).
   Δ_t < 0 → de-risking → λ_down, Δ_t ≥ 0 → re-risking → λ_up.
   그 달 세 자산에 같은 λ_dir을 적용하므로 비중 합=1이 유지된다.
3) Turnover_m = Σ_i |w_{i,m} − w_{i,m-1}| / 2  (λ=1 최대 70% 재현 규약)
4) 비용: net_return_m = gross_return_m − Turnover_m × cost_rate (사후 차감, 민감도용)
5) 월간 모델이므로 월중 가격변동에 따른 비중 drift는 반영하지 않는다(문서 계산식 그대로).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config as C


# ------------------------------------------------------------
# 1. 데이터 로딩
# ------------------------------------------------------------

def load_monthly_returns(path=None) -> pd.DataFrame:
    """월수익률(decimal) 로딩. index=월말 Date, columns=TICKERS."""
    path = path or C.RETURNS_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"수익률 파일이 없습니다: {path}\n"
            f"Git의 main_final_monthly_return_decimal.csv 를 data/processed/ 에 두세요."
        )
    df = pd.read_csv(path, index_col=0, parse_dates=True).sort_index()
    missing = [t for t in C.TICKERS if t not in df.columns]
    if missing:
        raise ValueError(f"수익률 파일에 열이 없습니다: {missing} / 실제 열: {list(df.columns)}")
    df = df[C.TICKERS].astype(float)
    if df.abs().max().max() > 1.5:
        raise ValueError("수익률이 decimal 단위가 아닌 것 같습니다(% 단위 의심). 단위를 확인하세요.")
    return df


def load_target_weights(path=None) -> pd.DataFrame:
    """
    신호월별 목표비중 w* 로딩. index=신호월 Date(월말).

    허용 스키마 (둘 중 하나):
    (a) hsi_state 열 → STATE_TARGET_WEIGHTS 로 매핑
    (b) w_star_069500, w_star_114260, w_star_153130 열 직접 제공
    insufficient_data 는 NaN 으로 두고 백테스트에서 '직전 실제비중 유지'로 처리.
    """
    path = path or C.WEIGHTS_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"목표비중 파일이 없습니다: {path}\n"
            f"Git의 main_final_baseline_rebalance_weights.csv 를 data/processed/ 에 두세요."
        )
    df = pd.read_csv(path, index_col=0, parse_dates=True).sort_index()

    wcols = [f"w_star_{t}" for t in C.TICKERS]
    if all(c in df.columns for c in wcols):
        w = df[wcols].copy()
        w.columns = C.TICKERS
        state_col = next((c for c in df.columns
                          if c.lower() in ("hsi_state", "market_state", "state")), None)
        if state_col is not None:
            w["hsi_state"] = df[state_col].values
        return w
    else:
        state_col = next((c for c in df.columns
                          if c.lower() in ("hsi_state", "market_state", "state")), None)
        if state_col is None:
            raise ValueError(
                f"목표비중 파일에 {wcols} 또는 hsi_state 열이 필요합니다. 실제 열: {list(df.columns)}"
            )
        rows = []
        for s in df[state_col]:
            tw = C.STATE_TARGET_WEIGHTS.get(str(s), None)
            rows.append([np.nan] * 3 if tw is None else tw)
        w = pd.DataFrame(rows, index=df.index, columns=C.TICKERS)
        w["hsi_state"] = df[state_col].values
        return w

    return w


# ------------------------------------------------------------
# 2. 백테스트 엔진 (대칭·비대칭·동적 λ 공용)
# ------------------------------------------------------------

def run_lambda_backtest(
    returns: pd.DataFrame,
    target_w: pd.DataFrame,
    lambda_up: float,
    lambda_down: float,
    lambda_series: pd.Series | None = None,
    cost_rate: float = 0.0,
    min_months: int = 24,
) -> pd.DataFrame:
    """
    부분조정 백테스트.

    returns  : index=월말, columns=TICKERS, 해당 월 수익률(decimal)
    target_w : index=신호월(월말), columns=TICKERS, w*_t (NaN=insufficient → 유지)
    lambda_up / lambda_down : 비대칭 계수 (같으면 대칭)
    lambda_series : E30용. 신호월 index 의 λ_t. 주어지면 up/down 대신 사용하되
                    방향 분리와 결합하려면 lambda_up/down 에 시리즈 곱 확장(v2 규칙에선 미사용).
    cost_rate : Turnover×cost_rate 사후 차감 (예: 10bp → 0.001)

    반환: 적용월 index 의 DataFrame
      [w_069500.., strategy_return_gross, turnover, cost, strategy_return_net,
       lambda_used, direction]
    """
    tw = target_w[C.TICKERS]
    common_signal = tw.index.intersection(returns.index)
    if len(common_signal) < min_months:
        raise ValueError("신호월과 수익률 월의 교집합이 24개월 미만입니다. 날짜 정렬을 확인하세요.")

    # 첫 유효 신호월의 w* 를 초기비중 w_0 로 사용 (E28 λ=0 퇴화 방지)
    first_valid = tw.dropna().index.min()
    w_prev = tw.loc[first_valid].values.astype(float)
    ret_index = returns.index

    # E30 dynamic lambda용 안전 정렬
    # target_w는 신호월 index이고, lambda_series는 수익률월 index에서 만들어질 수 있다.
    # 따라서 신호월 index에 맞춰 재정렬하고, 값이 없는 초기월은 기본 λ=0.3으로 채운다.
    lambda_series_aligned = None
    if lambda_series is not None:
        lambda_series_aligned = lambda_series.reindex(tw.index)

        default_lambda = 0.3
        if hasattr(C, "E30_RULE_V1"):
            default_lambda = C.E30_RULE_V1.get("lambda_base", 0.3)

        lambda_series_aligned = lambda_series_aligned.fillna(default_lambda)

    records = []
    for sig_date in tw.loc[first_valid:].index:
        # 적용월 = 신호월 다음의 수익률 월
        pos = ret_index.searchsorted(sig_date, side="right")
        if pos >= len(ret_index):
            break
        apply_date = ret_index[pos]

        w_star = tw.loc[sig_date].values.astype(float)
        if np.isnan(w_star).any():
            w_star = w_prev.copy()  # insufficient_data: 직전 실제비중 유지

        # 방향 판정: Δ = w*_risk,t − w_risk,{t-1} (실제비중 기준)
        risk_i = C.TICKERS.index(C.RISK_TICKER)
        delta = w_star[risk_i] - w_prev[risk_i]
        if lambda_series_aligned is not None:
            lam = float(lambda_series_aligned.loc[sig_date])
            direction = "dynamic"
        elif delta < 0:
            lam, direction = lambda_down, "down"
        else:
            lam, direction = lambda_up, "up"

        w_new = w_prev + lam * (w_star - w_prev)
        # 수치 안전장치 (이론상 합=1 유지되지만 부동소수 보정)
        w_new = np.clip(w_new, 0.0, 1.0)
        w_new = w_new / w_new.sum()

        turnover = 0.5 * np.abs(w_new - w_prev).sum()
        r = returns.loc[apply_date, C.TICKERS].values.astype(float)
        gross = float(np.dot(w_new, r))
        cost = turnover * cost_rate
        records.append({
            "apply_date": apply_date, "signal_date": sig_date,
            **{f"w_{t}": w_new[i] for i, t in enumerate(C.TICKERS)},
            "lambda_used": lam, "direction": direction,
            "turnover": turnover, "cost": cost,
            "strategy_return_gross": gross,
            "strategy_return_net": gross - cost,
        })
        w_prev = w_new

    out = pd.DataFrame(records).set_index("apply_date")
    return out


def run_fixed_weight_backtest(returns: pd.DataFrame, weights, start=None) -> pd.Series:
    """Fixed BM / EW: 매월 고정비중 리밸런싱 가정(월간 모델, Turnover=0 규약)."""
    w = np.array(weights, dtype=float)
    r = returns[C.TICKERS]
    if start is not None:
        r = r.loc[start:]
    return pd.Series(r.values @ w, index=r.index, name="return")


# ------------------------------------------------------------
# 3. 성과지표
# ------------------------------------------------------------

def perf_metrics(monthly_returns: pd.Series,
                 turnover: pd.Series | None = None,
                 label: str = "") -> dict:
    r = monthly_returns.dropna()
    n = len(r)
    if n == 0:
        raise ValueError("빈 수익률 시리즈")
    idx = (1 + r).cumprod()
    years = n / C.PERIODS_PER_YEAR
    cagr = idx.iloc[-1] ** (1 / years) - 1
    vol = r.std(ddof=1) * np.sqrt(C.PERIODS_PER_YEAR)
    dd = idx / idx.cummax() - 1
    mdd = dd.min()
    # Sharpe 규약 두 가지 모두 산출 (게이트 ①에서 기존 표와 대조해 확정)
    sharpe_arith = (r.mean() * C.PERIODS_PER_YEAR) / vol if vol > 0 else np.nan
    sharpe_geom = cagr / vol if vol > 0 else np.nan
    downside = r[r < 0].std(ddof=1) * np.sqrt(C.PERIODS_PER_YEAR)
    sortino = (r.mean() * C.PERIODS_PER_YEAR) / downside if downside and downside > 0 else np.nan
    calmar = cagr / abs(mdd) if mdd < 0 else np.nan
    out = {
        "strategy": label, "months": n,
        "cagr_pct": cagr * 100, "ann_vol_pct": vol * 100, "mdd_pct": mdd * 100,
        "sharpe": sharpe_arith, "sharpe_geom": sharpe_geom,
        "sortino": sortino, "calmar": calmar,
        "win_rate_pct": (r > 0).mean() * 100,
    }
    if turnover is not None:
        t = turnover.reindex(r.index).dropna()
        out["avg_turnover_pct"] = t.mean() * 100
        out["max_turnover_pct"] = t.max() * 100
    else:
        out["avg_turnover_pct"] = 0.0
        out["max_turnover_pct"] = 0.0
    return out


def apply_cost_grid(bt: pd.DataFrame, label: str) -> pd.DataFrame:
    """0/5/10/20bp 비용 민감도 표 (게이트 ③)."""
    rows = []
    for bps in C.COST_BPS_GRID:
        net = bt["strategy_return_gross"] - bt["turnover"] * (bps / 10000.0)
        m = perf_metrics(net, bt["turnover"], f"{label}@{bps}bp")
        m["cost_bps"] = bps
        rows.append(m)
    return pd.DataFrame(rows)


def tail_month_defense(strategy_r: pd.Series, risk_r: pd.Series, q: float = 0.10) -> dict:
    """069500 하위 10% 손실월에서의 방어력 (게이트 ④ tail-month)."""
    joined = pd.concat([strategy_r, risk_r], axis=1, keys=["strat", "risk"]).dropna()
    thresh = joined["risk"].quantile(q)
    tail = joined[joined["risk"] <= thresh]
    return {
        "tail_months": len(tail),
        "risk_avg_pct": tail["risk"].mean() * 100,
        "strategy_avg_pct": tail["strat"].mean() * 100,
        "capture_ratio": (tail["strat"].mean() / tail["risk"].mean()
                          if tail["risk"].mean() != 0 else np.nan),
    }
