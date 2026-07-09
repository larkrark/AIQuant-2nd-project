"""
Stage B (리포트 02~05): HSI 신호·5상태 분류·baseline 목표비중.

가격 기반 신호 → HSI 5상태 → 상태별 위험/방어 목표비중(baseline_rebalance_weights).
baseline(즉시비중)은 Stage D lambda=1.0 에 해당한다.

이식 원본:
- legacy/10_build_hsi_signal_inputs.py        : 5개 지표 → direction/intensity/signal
- legacy/12_flex_prepare_monthly_hsi_state.py : 일간 → 월말 변환
- legacy/16_main_v2_build_hsi_state5_table.py : 5상태 분류·상태별 비중 규칙

컷오프/파라미터는 pipeline.config 에서 관리한다:
HSI_PARAMS, HSI_NEUTRAL_BAND, HSI_HIGH_INTENSITY_QUANTILE,
HSI_ACCIDENT_DIRECTION_QUANTILE, STATE5_ALLOCATION
"""

import numpy as np
import pandas as pd

from common.config import ASSETS, PRIMARY_RISK_TICKER
from pipeline.config import (
    HSI_ACCIDENT_DIRECTION_QUANTILE,
    HSI_HIGH_INTENSITY_QUANTILE,
    HSI_NEUTRAL_BAND,
    HSI_PARAMS,
    STATE5_ALLOCATION,
)

STATE5_ORDER = [
    "risk_relief",
    "neutral_watch",
    "conflict",
    "risk_warning",
    "accident_zone",
    "insufficient_data",
]


# ============================================================
# 1. 개별 지표 (부호 규칙: 음수=양호, 양수=위험)
# ============================================================

def _sign_flip(df):
    """양호 신호(양수)를 음수로 반전해 '위험 방향=양수' 기준으로 통일."""
    return -df


def calc_return(prices, window=20):
    """최근 수익률 (높을수록 양호 → 부호 반전)."""
    return _sign_flip(prices.pct_change(window))


def calc_ma_position(prices, windows=None):
    """이동평균 대비 위치 (여러 MA 평균, 가격이 MA 위=양호 → 부호 반전)."""
    if windows is None:
        windows = [20, 60, 120]
    signals = []
    for w in windows:
        ma = prices.rolling(w, min_periods=w).mean()
        signals.append((prices / ma) - 1)
    combined = pd.concat(signals).groupby(level=0).mean()
    return _sign_flip(combined)


def calc_momentum(prices, windows=None):
    """모멘텀 = n일 수익률 여러 기간 평균 (양수=양호 → 부호 반전)."""
    if windows is None:
        windows = [21, 63, 126]
    signals = [prices.pct_change(w) for w in windows]
    combined = pd.concat(signals).groupby(level=0).mean()
    return _sign_flip(combined)


def calc_volatility(prices, window=20, annualize=True):
    """변동성 (높을수록 위험=양수 → 반전 없음)."""
    vol = prices.pct_change().rolling(window, min_periods=window).std()
    if annualize:
        vol = vol * np.sqrt(252)
    return vol


def calc_relative_strength(prices, benchmark, window=21):
    """상대강도 = 종목 수익률 - 벤치마크 수익률 (강하면 양호 → 부호 반전)."""
    if benchmark not in prices.columns:
        raise ValueError(
            f"benchmark 티커 '{benchmark}'가 prices 컬럼에 없습니다: {list(prices.columns)}"
        )
    ret = prices.pct_change(window)
    rs = ret.subtract(ret[[benchmark]].values, axis=0)
    return _sign_flip(rs)


# ============================================================
# 2. 표준화 → -10~+10 점수
# ============================================================

def standardize_zscore(signal, window=252, min_periods=60):
    """Rolling z-score (미래 데이터 누출 방지)."""
    roll_mean = signal.rolling(window, min_periods=min_periods).mean()
    roll_std = signal.rolling(window, min_periods=min_periods).std()
    return (signal - roll_mean) / roll_std.replace(0, np.nan)


def standardize_rank(signal, window=252, min_periods=60):
    """Rolling 분위수 표준화 (0~1 → -1~+1, 0.5=중립=0)."""

    def _rank_pct(x):
        arr = pd.Series(x)
        if arr.isna().all():
            return np.nan
        return float(arr.rank(pct=True).iloc[-1])

    ranked = signal.rolling(window, min_periods=min_periods).apply(_rank_pct, raw=False)
    return (ranked - 0.5) * 2


def clip_to_score(standardized, clip_z=2.5, scale=10.0):
    """표준화 지표를 [-clip_z, +clip_z]로 자른 뒤 -scale~+scale로 선형 변환."""
    return (standardized.clip(-clip_z, clip_z) / clip_z) * scale


# ============================================================
# 3. HSI direction / intensity / signal
# ============================================================

def compute_hsi(prices, params=None, benchmark=PRIMARY_RISK_TICKER):
    """
    일간 종가 → 티커별 HSI 신호 (일간).

    Returns 컬럼:
      {ticker}_direction : -1~+1 (양수=위험 악화)
      {ticker}_intensity :  0~+1 (신호 강도)
      {ticker}_signal    : buy | watch | caution
    """
    if params is None:
        params = HSI_PARAMS

    raw_signals = {
        "return": calc_return(prices, window=params["return_window"]),
        "ma_pos": calc_ma_position(prices, windows=params["ma_windows"]),
        "momentum": calc_momentum(prices, windows=params["momentum_windows"]),
        "vol": calc_volatility(prices, window=params["vol_window"]),
        "rs": calc_relative_strength(prices, benchmark=benchmark, window=params["rs_window"]),
    }

    scored_signals = {}
    for name, sig in raw_signals.items():
        if params["standardize"] == "zscore":
            std_sig = standardize_zscore(
                sig, window=params["std_window"], min_periods=params["std_min_periods"]
            )
            scored_signals[name] = clip_to_score(std_sig, clip_z=params["clip_z"], scale=10.0)
        elif params["standardize"] == "rank":
            std_sig = standardize_rank(
                sig, window=params["std_window"], min_periods=params["std_min_periods"]
            )
            scored_signals[name] = clip_to_score(
                std_sig, clip_z=params.get("rank_clip", 1.0), scale=10.0
            )
        else:
            raise ValueError(f"지원하지 않는 standardize 방식입니다: {params['standardize']}")

    # 안내서 6절 공식: M = 지표 수 × 10
    m_total = len(scored_signals) * 10.0
    threshold = params["direction_threshold"]

    results = {}
    for ticker in prices.columns:
        ticker_scores = pd.DataFrame(
            {k: v[ticker] for k, v in scored_signals.items() if ticker in v.columns}
        )
        v_plus = ticker_scores.clip(lower=0).sum(axis=1)
        v_minus = ticker_scores.clip(upper=0).abs().sum(axis=1)

        direction = (v_plus - v_minus) / m_total
        intensity = (v_plus + v_minus) / m_total

        signal = pd.Series("watch", index=direction.index, dtype=str)
        signal[direction < -threshold] = "buy"
        signal[direction > threshold] = "caution"

        results[f"{ticker}_direction"] = direction
        results[f"{ticker}_intensity"] = intensity
        results[f"{ticker}_signal"] = signal

    return pd.DataFrame(results)


def build_signal_inputs(prices, params=None, benchmark=PRIMARY_RISK_TICKER):
    """
    일간 종가 → 월말 HSI 신호 입력 테이블 (classify_hsi_states 입력).

    Returns: Date 컬럼 + {ticker}_direction/_intensity/_signal (월말 기준).
    """
    daily_hsi = compute_hsi(prices, params=params, benchmark=benchmark)
    try:
        monthly = daily_hsi.resample("ME").last()
    except ValueError:  # 구버전 pandas
        monthly = daily_hsi.resample("M").last()
    out = monthly.reset_index()
    out = out.rename(columns={out.columns[0]: "Date"})
    return out


# ============================================================
# 4. 5상태 분류
# ============================================================

def _find_col(columns, ticker, keyword):
    """컬럼명이 약간 달라도 {ticker}×{keyword} 컬럼을 찾는다."""
    candidates = [c for c in columns if ticker in c and keyword.lower() in c.lower()]
    if not candidates:
        raise ValueError(
            f"{ticker}와 {keyword}를 포함하는 컬럼을 찾지 못했습니다: {list(columns)}"
        )
    return candidates[0]


def classify_state5_row(direction, intensity,
                        high_intensity_cutoff, accident_direction_cutoff,
                        cross_asset_conflict, neutral_band=HSI_NEUTRAL_BAND):
    """
    단일 시점 5상태 분류 (legacy/16 classify_state5와 동일 규칙, 판정 순서 유지).

    1) conflict      : ETF 간 buy·caution 동시 발생, 또는 |direction|<=밴드 & intensity>=고강도
    2) accident_zone : direction>=accident 컷오프 & intensity>=고강도 컷오프
    3) risk_warning  : direction > 밴드
    4) risk_relief   : direction < -밴드
    5) neutral_watch : 나머지
    """
    if pd.isna(direction) or pd.isna(intensity):
        return "insufficient_data", "direction 또는 intensity 결측"

    if cross_asset_conflict:
        return "conflict", "ETF별 신호가 buy와 caution으로 동시에 나타남"

    if abs(direction) <= neutral_band and intensity >= high_intensity_cutoff:
        return "conflict", "방향성은 약하지만 신호 강도가 높음"

    if direction >= accident_direction_cutoff and intensity >= high_intensity_cutoff:
        return "accident_zone", "위험 악화 방향성과 신호 강도가 모두 높음"

    if direction > neutral_band:
        return "risk_warning", "위험 악화 방향 우세"

    if direction < -neutral_band:
        return "risk_relief", "위험 완화 방향 우세"

    return "neutral_watch", "방향성이 뚜렷하지 않아 관찰 상태"


def classify_hsi_states(signal_inputs,
                        primary_ticker=PRIMARY_RISK_TICKER,
                        neutral_band=HSI_NEUTRAL_BAND,
                        high_intensity_quantile=HSI_HIGH_INTENSITY_QUANTILE,
                        accident_direction_quantile=HSI_ACCIDENT_DIRECTION_QUANTILE):
    """
    월말 HSI 신호 → 5상태 테이블.

    컷오프는 표본 분포 기준으로 계산한다:
    - high_intensity_cutoff     = intensity의 high_intensity_quantile 분위수
    - accident_direction_cutoff = 양수 direction의 accident_direction_quantile 분위수

    Returns: 입력 + primary_direction / primary_intensity / hsi_state5 /
             state_reason / cross_asset_conflict / 컷오프 2종 컬럼.
    """
    direction_col = _find_col(signal_inputs.columns, primary_ticker, "direction")
    intensity_col = _find_col(signal_inputs.columns, primary_ticker, "intensity")
    signal_cols = [c for c in signal_inputs.columns if "signal" in c.lower()]

    result = signal_inputs.copy()

    high_intensity_cutoff = result[intensity_col].quantile(high_intensity_quantile)

    positive_direction = result.loc[result[direction_col] > 0, direction_col]
    if len(positive_direction) > 0:
        accident_direction_cutoff = positive_direction.quantile(accident_direction_quantile)
    else:
        accident_direction_cutoff = result[direction_col].quantile(accident_direction_quantile)

    # ETF 간 신호 충돌: 같은 시점에 buy와 caution이 동시에 존재
    if signal_cols:
        labels = result[signal_cols].astype(str).apply(lambda col: col.str.lower())
        cross_conflict = labels.eq("buy").any(axis=1) & labels.eq("caution").any(axis=1)
    else:
        cross_conflict = pd.Series(False, index=result.index)

    states, reasons = [], []
    for i in result.index:
        state, reason = classify_state5_row(
            direction=result.at[i, direction_col],
            intensity=result.at[i, intensity_col],
            high_intensity_cutoff=high_intensity_cutoff,
            accident_direction_cutoff=accident_direction_cutoff,
            cross_asset_conflict=bool(cross_conflict.at[i]),
            neutral_band=neutral_band,
        )
        states.append(state)
        reasons.append(reason)

    result["primary_ticker"] = primary_ticker
    result["primary_direction"] = result[direction_col]
    result["primary_intensity"] = result[intensity_col]
    result["hsi_state5"] = states
    result["state_reason"] = reasons
    result["cross_asset_conflict"] = cross_conflict.values
    result["high_intensity_cutoff"] = high_intensity_cutoff
    result["accident_direction_cutoff"] = accident_direction_cutoff
    return result


# ============================================================
# 5. 상태별 baseline 목표비중
# ============================================================

def allocation_rule_table():
    """STATE5_ALLOCATION → 규칙 테이블 (비중 합계 1.0 검증 포함)."""
    rows = []
    for state, spec in STATE5_ALLOCATION.items():
        row = {
            "hsi_state5": state,
            "state_name_kr": spec["state_name_kr"],
            "action": spec["action"],
        }
        for a in ASSETS:
            row[f"{a}_weight"] = spec[a]
        rows.append(row)
    rule = pd.DataFrame(rows)
    rule["weight_sum"] = sum(rule[f"{a}_weight"] for a in ASSETS)
    if not np.allclose(rule["weight_sum"], 1.0):
        raise ValueError("STATE5_ALLOCATION 비중 합계가 1.0이 아닌 상태가 있습니다.")
    return rule


def baseline_target_weights(states):
    """HSI 상태 → 위험/방어 목표비중(Date + *_weight, 합 1.0). Stage D lambda 입력."""
    if "hsi_state5" not in states.columns:
        raise ValueError("states에 hsi_state5 컬럼이 없습니다. classify_hsi_states 출력을 사용하세요.")

    unknown = set(states["hsi_state5"].unique()) - set(STATE5_ALLOCATION)
    if unknown:
        raise ValueError(f"STATE5_ALLOCATION에 정의되지 않은 상태: {sorted(unknown)}")

    rule = allocation_rule_table().set_index("hsi_state5")
    out = states[["Date"]].copy()
    for a in ASSETS:
        out[f"{a}_weight"] = states["hsi_state5"].map(rule[f"{a}_weight"]).values

    weight_sum = sum(out[f"{a}_weight"] for a in ASSETS)
    if not np.allclose(weight_sum, 1.0):
        raise ValueError("baseline 목표비중 합계가 1.0이 아닌 행이 있습니다.")
    return out
