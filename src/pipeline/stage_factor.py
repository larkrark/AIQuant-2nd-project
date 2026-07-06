"""
Stage Factor (RA 요구사항: 팩터 분석·팩터 로딩).

기존 전략(lambda=0.1/0.3, baseline, BM 등)이 무엇에 노출됐는지 회귀형으로 설명하는
정적 + rolling 팩터 로딩. 전략을 바꾸지 않는 사후 분석이므로 안전하다.
의존성: numpy/pandas만 사용(statsmodels 불필요).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from common.io_utils import save_table
from common.paths import PROCESSED_DIR, TABLE_DIR
from pipeline.config import (
    FACTOR_CORR_THRESHOLD,
    FACTOR_LAG,
    FACTOR_MIN_PERIODS,
    FACTOR_ROLLING_WINDOW,
    FACTOR_VIF_THRESHOLD,
)
from pipeline.stage_ra_inputs import DEFAULT_CANDIDATE_TIMESERIES, load_candidate_return_matrix


def expanding_zscore(s: pd.Series, min_periods: int = FACTOR_MIN_PERIODS) -> pd.Series:
    """expanding z-score: (x_t - mean_1..t) / std_1..t. 룩어헤드 없음."""
    mean = s.expanding(min_periods=min_periods).mean()
    std = s.expanding(min_periods=min_periods).std(ddof=1)
    return (s - mean) / std.replace(0, np.nan)


def build_factor_matrix(factors_raw, *, factor_cols=None, standardize=True, lags=None):
    """팩터 원자료(Date + 팩터열) -> 표준화(expanding z)·시차(lag) 적용 행렬."""
    lags = FACTOR_LAG if lags is None else lags
    df = factors_raw.sort_values("Date").reset_index(drop=True).copy()
    cols = factor_cols or [c for c in df.columns if c != "Date"]
    out = df[["Date"]].copy()
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce")
        if standardize:
            s = expanding_zscore(s)
        lag = int(lags.get(c, 0))
        if lag:
            s = s.shift(lag)
        out[c] = s
    return out


def _ols(y, X):
    """X는 절편 포함 설계행렬(n x k). 반환 dict: beta, se, tstat, r2, n, k, dof."""
    n, k = X.shape
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = n - k
    ssr = float(resid @ resid)
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ssr / sst if sst > 0 else np.nan
    if dof > 0:
        sigma2 = ssr / dof
        xtx_inv = np.linalg.pinv(X.T @ X)
        se = np.sqrt(np.maximum(np.diag(sigma2 * xtx_inv), 0.0))
        with np.errstate(divide="ignore", invalid="ignore"):
            tstat = np.where(se > 0, beta / se, np.nan)
    else:
        se = np.full(k, np.nan)
        tstat = np.full(k, np.nan)
    return {"beta": beta, "se": se, "tstat": tstat, "r2": r2, "n": n, "k": k, "dof": dof}


def _design(Xf):
    return np.column_stack([np.ones(len(Xf)), Xf])


def full_period_loading(excess_returns, factor_matrix, *, factor_cols=None):
    """(R_strategy - R_BM) ~ factors OLS. 반환 dict(loadings, alpha, r2, n)."""
    cols = factor_cols or [c for c in factor_matrix.columns if c != "Date"]
    df = factor_matrix.copy()
    df["_y"] = pd.Series(excess_returns).values if len(excess_returns) == len(df) else np.nan
    df = df.dropna(subset=cols + ["_y"]).reset_index(drop=True)
    if len(df) <= len(cols) + 1:
        raise ValueError("유효 관측이 팩터 수보다 적어 회귀 불가.")
    y = df["_y"].to_numpy(dtype=float)
    Xf = df[cols].to_numpy(dtype=float)
    res = _ols(y, _design(Xf))
    loadings = pd.DataFrame({
        "factor": cols,
        "beta": res["beta"][1:],
        "se": res["se"][1:],
        "tstat": res["tstat"][1:],
    })
    return {"loadings": loadings, "alpha": float(res["beta"][0]),
            "alpha_tstat": float(res["tstat"][0]), "r2": res["r2"], "n": res["n"]}


def compute_vif(factor_matrix, factor_cols=None):
    """각 팩터 VIF = 1/(1-R2_j)."""
    cols = factor_cols or [c for c in factor_matrix.columns if c != "Date"]
    df = factor_matrix[cols].dropna().reset_index(drop=True)
    vifs = {}
    for c in cols:
        others = [x for x in cols if x != c]
        if not others:
            vifs[c] = np.nan
            continue
        y = df[c].to_numpy(dtype=float)
        X = _design(df[others].to_numpy(dtype=float))
        r2 = _ols(y, X)["r2"]
        vifs[c] = 1.0 / (1.0 - r2) if (r2 is not None and r2 < 1) else np.inf
    return pd.Series(vifs, name="VIF")


def screen_factors(factor_matrix, *, factor_cols=None,
                   corr_threshold=FACTOR_CORR_THRESHOLD, vif_threshold=FACTOR_VIF_THRESHOLD):
    """상관·VIF로 중복 팩터 경고."""
    cols = factor_cols or [c for c in factor_matrix.columns if c != "Date"]
    corr = factor_matrix[cols].dropna().corr()
    vif = compute_vif(factor_matrix, cols)
    high_pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr.iloc[i, j]
            if pd.notna(r) and abs(r) >= corr_threshold:
                high_pairs.append((cols[i], cols[j], round(float(r), 3)))
    flagged = sorted(set(
        [c for c in cols if pd.notna(vif[c]) and vif[c] >= vif_threshold]
        + [p[1] for p in high_pairs]
    ))
    return {"corr": corr, "vif": vif, "high_corr_pairs": high_pairs, "flagged": flagged}


def rolling_loading(excess_returns, factor_matrix, *, factor_cols=None, window=FACTOR_ROLLING_WINDOW):
    """window개월 rolling OLS -> 팩터 로딩 시계열."""
    cols = factor_cols or [c for c in factor_matrix.columns if c != "Date"]
    df = factor_matrix.copy()
    df["_y"] = pd.Series(excess_returns).values if len(excess_returns) == len(df) else np.nan
    df = df.dropna(subset=cols + ["_y"]).reset_index(drop=True)
    rows = []
    for end in range(window - 1, len(df)):
        w = df.iloc[end - window + 1: end + 1]
        res = _ols(w["_y"].to_numpy(dtype=float), _design(w[cols].to_numpy(dtype=float)))
        row = {"Date": df.loc[end, "Date"], "r2": res["r2"]}
        for i, c in enumerate(cols):
            row[f"{c}_beta"] = res["beta"][1 + i]
        rows.append(row)
    return pd.DataFrame(rows)


def analyze_strategies(strategy_returns, bm_returns, factor_matrix, *, strategy_cols=None, factor_cols=None):
    """여러 전략에 대해 전체기간 로딩 요약 + rolling 시계열."""
    scols = strategy_cols or [c for c in strategy_returns.columns if c != "Date"]
    fcols = factor_cols or [c for c in factor_matrix.columns if c != "Date"]
    bm = pd.Series(bm_returns).reset_index(drop=True)
    summ_rows, ts_frames = [], []
    for s in scols:
        excess = strategy_returns[s].reset_index(drop=True) - bm
        res = full_period_loading(excess, factor_matrix, factor_cols=fcols)
        for _, r in res["loadings"].iterrows():
            summ_rows.append({"strategy": s, "factor": r["factor"],
                              "beta": r["beta"], "tstat": r["tstat"], "r2": res["r2"]})
        summ_rows.append({"strategy": s, "factor": "alpha",
                          "beta": res["alpha"], "tstat": res["alpha_tstat"], "r2": res["r2"]})
        roll = rolling_loading(excess, factor_matrix, factor_cols=fcols)
        roll.insert(1, "strategy", s)
        ts_frames.append(roll)
    summary = pd.DataFrame(summ_rows)
    timeseries = pd.concat(ts_frames, ignore_index=True) if ts_frames else pd.DataFrame()
    return summary, timeseries


def save_outputs(summary, timeseries):
    save_table(summary, TABLE_DIR / "factor_loading_summary.csv")
    save_table(timeseries, TABLE_DIR / "factor_loading_timeseries.csv")


def _run_from_files_stub():
    """data/factors/monthly_factors.csv + 전략 수익률 연결점(데이터 인제스트 후 구현)."""
    factor_path = PROCESSED_DIR / "factors" / "monthly_factors.csv"
    if not factor_path.exists():
        raise FileNotFoundError(
            f"팩터 원자료가 없습니다: {factor_path}. ECOS/KRX 인제스트로 먼저 생성하세요."
        )
    raise NotImplementedError(
        "run_from_files: 전략 수익률 소스 확정 후 analyze_strategies 로 연결."
    )


def run_from_files(
    *,
    factor_path=None,
    candidate_path=None,
    bm_strategy="EW",
    strategy_cols=None,
    factor_cols=None,
    save=True,
):
    """Load monthly factor and candidate-return CSVs, then run factor loading."""
    factor_path = Path(factor_path or (PROCESSED_DIR / "factors" / "monthly_factors.csv"))
    candidate_path = Path(candidate_path or DEFAULT_CANDIDATE_TIMESERIES)
    if not factor_path.exists():
        raise FileNotFoundError(
            f"factor source is missing: {factor_path}. "
            "Run pipeline.factor_ingest.build_monthly_factors() first."
        )
    if not candidate_path.exists():
        raise FileNotFoundError(f"candidate timeseries file is missing: {candidate_path}")

    factors_raw = pd.read_csv(factor_path)
    if "Date" not in factors_raw.columns:
        raise ValueError(f"factor source needs Date column: {factor_path}")
    factors_raw["Date"] = pd.to_datetime(factors_raw["Date"])
    factor_matrix = build_factor_matrix(factors_raw, factor_cols=factor_cols)

    returns = load_candidate_return_matrix(candidate_path)
    df = returns.merge(factor_matrix, on="Date", how="inner")
    if df.empty:
        raise ValueError("candidate returns and factor matrix have no overlapping Date rows.")
    if bm_strategy not in df.columns:
        raise ValueError(f"benchmark strategy is missing from candidate returns: {bm_strategy}")

    factor_cols = factor_cols or [c for c in factor_matrix.columns if c != "Date"]
    strategy_cols = strategy_cols or [c for c in returns.columns if c not in ["Date", bm_strategy]]
    summary, timeseries = analyze_strategies(
        df[["Date"] + strategy_cols],
        df[bm_strategy],
        df[["Date"] + factor_cols],
        strategy_cols=strategy_cols,
        factor_cols=factor_cols,
    )
    if save:
        save_outputs(summary, timeseries)
        vif = compute_vif(df[["Date"] + factor_cols], factor_cols).reset_index()
        vif.columns = ["factor", "VIF"]
        save_table(vif, TABLE_DIR / "factor_vif.csv")
    return summary, timeseries


if __name__ == "__main__":
    print("stage_factor: analyze_strategies(strategy_returns, bm, factor_matrix) 사용.")
