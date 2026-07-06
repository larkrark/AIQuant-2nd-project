"""
Stage Factor (RA 요구사항: 팩터 분석·팩터 로딩).

기존 전략(λ=0.1/0.3, baseline, BM 등)이 *무엇에 노출됐는지* 회귀형으로 설명하는
정적 + rolling 팩터 로딩. 전략을 바꾸지 않는 사후 분석이므로 안전하다.

의존성: numpy/pandas만 사용(statsmodels 불필요). t-stat는 OLS 표준오차로 직접 계산.

핵심 설계
--------
- build_factor_matrix : expanding z-score 표준화 + 발표시차 lag (룩어헤드 차단)
- compute_vif / screen_factors : 상관·VIF로 중복 팩터 경고 (팀검토 반영)
- full_period_loading : (R_strategy - R_BM) ~ factors OLS → beta, t-stat, R2
- rolling_loading : window(기본 36개월) rolling OLS → 로딩 시계열

주의: 실제 실행에는 팩터 원자료(data/factors/monthly_factors.csv)와 전략 수익률이 필요.
아래 함수는 DataFrame/Series를 인자로 받으므로 합성 데이터로 단위 검증 가능.
"""

from __future__ import annotations

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


# ------------------------------------------------------------
# 1. 팩터 행렬 구성 (표준화 + 시차)
# ------------------------------------------------------------

def expanding_zscore(s: pd.Series, min_periods: int = FACTOR_MIN_PERIODS) -> pd.Series:
    """
    expanding z-score: (x_t - mean(x_1..t)) / std(x_1..t).
    전체표본 평균/표준편차를 쓰지 않으므로 룩어헤드가 없다.
    """
    mean = s.expanding(min_periods=min_periods).mean()
    std = s.expanding(min_periods=min_periods).std(ddof=1)
    return (s - mean) / std.replace(0, np.nan)


def build_factor_matrix(
    factors_raw: pd.DataFrame,
    *,
    factor_cols: list[str] | None = None,
    standardize: bool = True,
    lags: dict | None = None,
) -> pd.DataFrame:
    """
    팩터 원자료(Date + 팩터열) → 표준화·시차 적용된 팩터 행렬.

    - standardize: expanding z-score 적용(룩어헤드 차단).
    - lags: 팩터별 lag(개월). 기본은 config.FACTOR_LAG. 발표 시차/룩어헤드 차단용.
    """
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


# ------------------------------------------------------------
# 2. OLS (numpy) + t-stat
# ------------------------------------------------------------

def _ols(y: np.ndarray, X: np.ndarray) -> dict:
    """
    X는 절편 포함 설계행렬(n×k). 반환: beta, se, tstat, r2, n, k, dof.
    """
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


def _design(X_factors: np.ndarray) -> np.ndarray:
    """절편 컬럼을 앞에 붙인 설계행렬."""
    return np.column_stack([np.ones(len(X_factors)), X_factors])


# ------------------------------------------------------------
# 3. 전체기간 팩터 로딩
# ------------------------------------------------------------

def full_period_loading(
    excess_returns: pd.Series,
    factor_matrix: pd.DataFrame,
    *,
    factor_cols: list[str] | None = None,
) -> dict:
    """
    (R_strategy - R_BM) ~ factors OLS.
    반환: {'loadings': DataFrame(factor, beta, se, tstat), 'alpha':..., 'r2':..., 'n':...}
    """
    cols = factor_cols or [c for c in factor_matrix.columns if c != "Date"]
    df = factor_matrix.copy()
    df["_y"] = pd.Series(excess_returns).values if len(excess_returns) == len(df) else np.nan
    df = df.dropna(subset=cols + ["_y"]).reset_index(drop=True)

    if len(df) <= len(cols) + 1:
        raise ValueError("유효 관측이 팩터 수보다 적어 회귀 불가(표준화 warmup·lag로 표본 감소).")

    y = df["_y"].to_numpy(dtype=float)
    Xf = df[cols].to_numpy(dtype=float)
    res = _ols(y, _design(Xf))

    loadings = pd.DataFrame({
        "factor": cols,
        "beta": res["beta"][1:],
        "se": res["se"][1:],
        "tstat": res["tstat"][1:],
    })
    return {
        "loadings": loadings,
        "alpha": float(res["beta"][0]),
        "alpha_tstat": float(res["tstat"][0]),
        "r2": res["r2"],
        "n": res["n"],
    }


# ------------------------------------------------------------
# 4. 상관 / VIF 스크리닝
# ------------------------------------------------------------

def compute_vif(factor_matrix: pd.DataFrame, factor_cols: list[str] | None = None) -> pd.Series:
    """
    각 팩터의 VIF = 1/(1-R2_j). R2_j는 팩터 j를 나머지 팩터로 회귀한 결정계수.
    VIF>threshold면 다중공선성 경고.
    """
    cols = factor_cols or [c for c in factor_matrix.columns if c != "Date"]
    df = factor_matrix[cols].dropna().reset_index(drop=True)
    vifs = {}
    for j, c in enumerate(cols):
        others = [x for x in cols if x != c]
        if not others:
            vifs[c] = np.nan
            continue
        y = df[c].to_numpy(dtype=float)
        X = _design(df[others].to_numpy(dtype=float))
        r2 = _ols(y, X)["r2"]
        vifs[c] = 1.0 / (1.0 - r2) if (r2 is not None and r2 < 1) else np.inf
    return pd.Series(vifs, name="VIF")


def screen_factors(
    factor_matrix: pd.DataFrame,
    *,
    factor_cols: list[str] | None = None,
    corr_threshold: float = FACTOR_CORR_THRESHOLD,
    vif_threshold: float = FACTOR_VIF_THRESHOLD,
) -> dict:
    """
    상관행렬·VIF를 계산하고 중복 후보를 경고한다(팀검토 반영: VKOSPI↔실현변동성 등).
    반환: {'corr': DataFrame, 'vif': Series, 'high_corr_pairs': [...], 'flagged': [...]}
    """
    cols = factor_cols or [c for c in factor_matrix.columns if c != "Date"]
    sub = factor_matrix[cols].dropna()
    corr = sub.corr()
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


# ------------------------------------------------------------
# 5. Rolling 팩터 로딩
# ------------------------------------------------------------

def rolling_loading(
    excess_returns: pd.Series,
    factor_matrix: pd.DataFrame,
    *,
    factor_cols: list[str] | None = None,
    window: int = FACTOR_ROLLING_WINDOW,
) -> pd.DataFrame:
    """
    window개월 rolling OLS → 각 시점의 팩터 로딩(beta) 시계열.
    반환: Date + <factor>_beta 컬럼 + r2.
    """
    cols = factor_cols or [c for c in factor_matrix.columns if c != "Date"]
    df = factor_matrix.copy()
    df["_y"] = pd.Series(excess_returns).values if len(excess_returns) == len(df) else np.nan
    df = df.dropna(subset=cols + ["_y"]).reset_index(drop=True)

    rows = []
    for end in range(window - 1, len(df)):
        w = df.iloc[end - window + 1: end + 1]
        y = w["_y"].to_numpy(dtype=float)
        Xf = w[cols].to_numpy(dtype=float)
        res = _ols(y, _design(Xf))
        row = {"Date": df.loc[end, "Date"], "r2": res["r2"]}
        for i, c in enumerate(cols):
            row[f"{c}_beta"] = res["beta"][1 + i]
        rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------
# 6. 오케스트레이션
# ------------------------------------------------------------

def analyze_strategies(
    strategy_returns: pd.DataFrame,
    bm_returns: pd.Series,
    factor_matrix: pd.DataFrame,
    *,
    strategy_cols: list[str] | None = None,
    factor_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    여러 전략에 대해 전체기간 로딩 요약표 + rolling 로딩 시계열을 만든다.

    strategy_returns: Date + 전략별 월수익률 컬럼.
    bm_returns: BM 월수익률(길이 동일 또는 Date 정렬 가정).
    반환: (summary_df, timeseries_df)
    """
    scols = strategy_cols or [c for c in strategy_returns.columns if c != "Date"]
    fcols = factor_cols or [c for c in factor_matrix.columns if c != "Date"]
    bm = pd.Series(bm_returns).reset_index(drop=True)

    summ_rows, ts_frames = [], []
    for s in scols:
        excess = strategy_returns[s].reset_index(drop=True) - bm
        res = full_period_loading(excess, factor_matrix, factor_cols=fcols)
        for _, r in res["loadings"].iterrows():
            summ_rows.append({
                "strategy": s, "factor": r["factor"],
                "beta": r["beta"], "tstat": r["tstat"], "r2": res["r2"],
            })
        summ_rows.append({
            "strategy": s, "factor": "alpha",
            "beta": res["alpha"], "tstat": res["alpha_tstat"], "r2": res["r2"],
        })
        roll = rolling_loading(excess, factor_matrix, factor_cols=fcols)
        roll.insert(1, "strategy", s)
        ts_frames.append(roll)

    summary = pd.DataFrame(summ_rows)
    timeseries = pd.concat(ts_frames, ignore_index=True) if ts_frames else pd.DataFrame()
    return summary, timeseries


def run_from_files() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    data/factors/monthly_factors.csv (팩터 원자료) + 전략 수익률을 읽어
    로딩 요약/시계열을 output/tables에 저장. (파일이 없으면 안내와 함께 예외)
    """
    factor_path = PROCESSED_DIR / "factors" / "monthly_factors.csv"
    if not factor_path.exists():
        raise FileNotFoundError(
            f"팩터 원자료가 없습니다: {factor_path}. "
            "ECOS/KRX 인제스트(0단계)로 monthly_factors.csv 를 먼저 생성하세요."
        )
    # 전략 수익률 소스는 프로젝트 확정 후 연결(예: main_final_lambda_backtest_timeseries).
    raise NotImplementedError(
        "run_from_files: 전략 수익률 소스 확정 후 analyze_strategies 로 연결. "
        f"산출 예정: {TABLE_DIR / 'factor_loading_summary.csv'}, "
        f"{TABLE_DIR / 'factor_loading_timeseries.csv'}"
    )


def save_outputs(summary: pd.DataFrame, timeseries: pd.DataFrame) -> None:
    save_table(summary, TABLE_DIR / "factor_loading_summary.csv")
    save_table(timeseries, TABLE_DIR / "factor_loading_timeseries.csv")


if __name__ == "__main__":
    print("stage_factor: 팩터 로딩 모듈. analyze_strategies(strategy_returns, bm, factor_matrix) 사용.")
