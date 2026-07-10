# -*- coding: utf-8 -*-
"""
15_lambda_macro_overlay_sensitivity.py

Lambda 0.1/0.3 후보 위에 macro companion 약한 보정을 얹어 비교한다.
기본 조합은 2 x 4 = 8개이며, 24개를 넘으면 중단한다.
GDP는 직접 위험 조건에서 제외한다. rate_z, fx_z, rate_fx_departure가 있으면
금리·환율 기반 no-GDP signal을 만들고, 없으면 기존 macro_defense_addon fallback을 사용하되
결과표에 경고 표기를 남긴다.
"""

from __future__ import annotations

from pathlib import Path
import warnings
import numpy as np
import pandas as pd

# ============================================================
# 0. 설정
# ============================================================
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
DOCS = ROOT / "docs"

INPUT_TARGET = DATA / "main_final_baseline_rebalance_weights.csv"
INPUT_MACRO = DATA / "main_final_hsi_macro_companion_joined_monthly.csv"
INPUT_RET = DATA / "main_final_monthly_return_decimal.csv"

OUT_TS = DATA / "main_final_lambda_macro_overlay_sensitivity_timeseries.csv"
OUT_SUMMARY = TABLES / "main_final_lambda_macro_overlay_sensitivity_summary.csv"
OUT_RANKED = TABLES / "main_final_lambda_macro_overlay_sensitivity_ranked.csv"
OUT_DASHBOARD = TABLES / "main_final_lambda_macro_overlay_sensitivity_dashboard_rows.csv"
OUT_NOTE = DOCS / "main_final_lambda_macro_overlay_sensitivity_note.md"

RISK = "069500"
BOND = "114260"
CASH = "153130"

LAMBDAS = [0.1, 0.3]
MACRO_SCALES = [0.0, 0.25, 0.50, 0.75]
MAX_COMBINATIONS = 24

DEPARTURE_CUTOFF = 0.70
RATE_FX_STRESS_ADDON = 0.025
MAX_DELTA = 0.030
TO_BOND = 0.30
TO_CASH = 0.70
PERIODS_PER_YEAR = 12
COST_BPS = 20


def ensure_dirs():
    for p in [DATA, TABLES, DOCS]:
        p.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"입력 파일을 찾지 못했습니다: {path}")
    for enc in ["utf-8-sig", "utf-8", "cp949"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            pass
    return pd.read_csv(path)


def to_month(s: pd.Series) -> pd.Series:
    x = pd.to_datetime(s, errors="coerce")
    if x.notna().mean() < 0.5:
        x = pd.to_datetime(s.astype(str) + "-01", errors="coerce")
    return x.dt.to_period("M").dt.to_timestamp("M")


def first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def find_date_col(df: pd.DataFrame) -> str:
    candidates = [
        "return_year_month", "year_month", "Date", "date", "month", "Month",
        "YearMonth", "rebalance_date", "signal_date", "return_date", "Unnamed: 0",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        if pd.to_datetime(df[c], errors="coerce").notna().mean() > 0.8:
            return c
    raise ValueError(f"날짜 컬럼을 찾지 못했습니다: {list(df.columns)}")


def add_month_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "year_month" in out.columns:
        out["signal_month"] = to_month(out["year_month"])
    else:
        out["signal_month"] = to_month(out[find_date_col(out)])
    if "return_year_month" in out.columns:
        out["return_month"] = to_month(out["return_year_month"])
    else:
        out["return_month"] = out["signal_month"]
    return out


def find_weight_col(df: pd.DataFrame, ticker: str) -> str:
    candidates = [
        ticker, f"{ticker}_weight", f"weight_{ticker}", f"base_weight_{ticker}",
        f"target_weight_{ticker}", f"w_{ticker}", f"{ticker}.KS",
    ]
    c = first_existing(df, candidates)
    if c:
        return c
    hits = [
        c for c in df.columns
        if ticker in str(c) and "return" not in str(c).lower() and "ret" not in str(c).lower()
    ]
    if hits:
        return hits[0]
    raise ValueError(f"{ticker} 비중 컬럼을 찾지 못했습니다: {list(df.columns)}")


def find_return_col(df: pd.DataFrame, ticker: str) -> str:
    candidates = [
        ticker, f"{ticker}_return", f"return_{ticker}", f"ret_{ticker}",
        f"monthly_return_{ticker}", f"{ticker}.KS",
    ]
    c = first_existing(df, candidates)
    if c:
        return c
    hits = [c for c in df.columns if ticker in str(c)]
    if hits:
        return hits[0]
    raise ValueError(f"{ticker} 수익률 컬럼을 찾지 못했습니다: {list(df.columns)}")


def find_state_col(df: pd.DataFrame) -> str | None:
    return first_existing(df, ["hsi_state", "hsi_state5", "state5", "state", "regime", "hsi_regime"])


def maybe_percent_to_decimal(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    mx = out[cols].abs().max().max()
    if pd.notna(mx) and mx > 1.5:
        out[cols] = out[cols] / 100.0
    return out


def maybe_return_percent_to_decimal(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    mx = out[cols].abs().max().max()
    if pd.notna(mx) and mx > 1.0:
        out[cols] = out[cols] / 100.0
    return out


def boolish(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.fillna(False)
    return s.astype(str).str.lower().str.strip().isin(["1", "1.0", "true", "t", "yes", "y"])


def normalize_addon(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce").fillna(0.0)
    if x.abs().max() > 1.0:
        x = x / 100.0
    return x.clip(lower=0.0, upper=MAX_DELTA)


# ============================================================
# 1. 입력 로드
# ============================================================
def load_target_weights() -> pd.DataFrame:
    df = add_month_keys(read_csv(INPUT_TARGET))
    wc = [find_weight_col(df, t) for t in [RISK, BOND, CASH]]
    state_col = find_state_col(df)
    keep = ["signal_month", "return_month"] + wc
    if state_col:
        keep.append(state_col)
    out = df[keep].copy()
    out = out.rename(columns={wc[0]: "target_w_069500", wc[1]: "target_w_114260", wc[2]: "target_w_153130"})
    if state_col:
        out = out.rename(columns={state_col: "hsi_state"})
    else:
        out["hsi_state"] = "unknown"
    out = maybe_percent_to_decimal(out, ["target_w_069500", "target_w_114260", "target_w_153130"])
    return out.dropna(subset=["signal_month", "return_month"]).drop_duplicates("signal_month").sort_values("signal_month").reset_index(drop=True)


def load_returns() -> pd.DataFrame:
    df = read_csv(INPUT_RET)
    df["return_month"] = to_month(df[find_date_col(df)])
    rc = [find_return_col(df, t) for t in [RISK, BOND, CASH]]
    out = df[["return_month"] + rc].copy()
    out = out.rename(columns={rc[0]: "ret_069500", rc[1]: "ret_114260", rc[2]: "ret_153130"})
    out = maybe_return_percent_to_decimal(out, ["ret_069500", "ret_114260", "ret_153130"])
    return out.dropna(subset=["return_month"]).drop_duplicates("return_month").sort_values("return_month").reset_index(drop=True)


def load_macro() -> pd.DataFrame:
    df = add_month_keys(read_csv(INPUT_MACRO))
    state_col = find_state_col(df)
    if state_col and state_col != "hsi_state":
        df = df.rename(columns={state_col: "hsi_state"})
    if "hsi_state" not in df.columns:
        df["hsi_state"] = "unknown"
    if "hsi_risk_flag" in df.columns:
        df["hsi_risk_flag"] = boolish(df["hsi_risk_flag"])
    else:
        df["hsi_risk_flag"] = df["hsi_state"].isin(["risk_warning", "accident_zone"])
    if "macro_data_available" in df.columns:
        df["macro_data_available"] = boolish(df["macro_data_available"])
    else:
        macro_cols = [c for c in ["rate_z", "fx_z", "rate_fx_departure", "macro_defense_addon"] if c in df.columns]
        df["macro_data_available"] = df[macro_cols].notna().any(axis=1) if macro_cols else True
    return df.dropna(subset=["signal_month"]).drop_duplicates("signal_month").sort_values("signal_month").reset_index(drop=True)


# ============================================================
# 2. GDP 제외 macro bridge
# ============================================================
def build_macro_bridge() -> pd.DataFrame:
    m = load_macro()
    rate_col = first_existing(m, ["rate_z", "interest_rate_z", "rate_change_z", "rp_rate_z"])
    fx_col = first_existing(m, ["fx_z", "usdkrw_z", "fx_change_z", "usdkrw_change_z"])
    dep_col = first_existing(m, ["rate_fx_departure", "rate_fx_departure_score", "macro_rate_fx_departure", "rate_fx_same_direction_score"])

    if rate_col and fx_col and dep_col:
        m["rate_z_used"] = pd.to_numeric(m[rate_col], errors="coerce")
        m["fx_z_used"] = pd.to_numeric(m[fx_col], errors="coerce")
        m["rate_fx_departure_used"] = pd.to_numeric(m[dep_col], errors="coerce")
        m["macro_risk_flag_no_gdp"] = (
            m["macro_data_available"]
            & (m["rate_z_used"] > 0)
            & (m["fx_z_used"] > 0)
            & (m["rate_fx_departure_used"] >= DEPARTURE_CUTOFF)
        )
        m["macro_defense_addon_no_gdp"] = np.where(m["macro_risk_flag_no_gdp"], RATE_FX_STRESS_ADDON, 0.0)
        m["macro_signal_version"] = "no_gdp_rate_fx_verified"
        m["macro_risk_source"] = np.where(m["macro_risk_flag_no_gdp"], "rate_up_fx_up_departure_high", "none")
    else:
        if "macro_defense_addon" not in m.columns or "macro_risk_flag" not in m.columns:
            raise ValueError("no-GDP signal용 rate_z/fx_z/departure도 없고 fallback용 macro_defense_addon/macro_risk_flag도 없습니다.")
        warnings.warn("rate/fx/departure 컬럼을 모두 찾지 못해 기존 macro_defense_addon을 fallback 사용합니다. GDP 조건이 포함될 수 있습니다.")
        m["macro_risk_flag_no_gdp"] = boolish(m["macro_risk_flag"])
        m["macro_defense_addon_no_gdp"] = normalize_addon(m["macro_defense_addon"])
        m["macro_signal_version"] = "fallback_existing_macro_may_include_gdp"
        m["macro_risk_source"] = np.where(m["macro_risk_flag_no_gdp"], "fallback_existing_macro_defense_addon", "none")

    def overlap(row):
        hsi = bool(row["hsi_risk_flag"])
        mac = bool(row["macro_risk_flag_no_gdp"])
        state = str(row.get("hsi_state", ""))
        if hsi and mac:
            return "both_hsi_and_macro_risk"
        if hsi and not mac:
            return "hsi_risk_only"
        if (not hsi) and mac:
            if state == "risk_relief":
                return "macro_risk_only_risk_relief"
            if state == "neutral_watch":
                return "macro_risk_only_neutral"
            if state == "conflict":
                return "macro_risk_only_conflict"
            return "macro_risk_only_other"
        return "both_relief_or_neutral"

    m["macro_hsi_overlap_type_no_gdp"] = m.apply(overlap, axis=1)

    strength_map = {
        "both_hsi_and_macro_risk": 1.00,
        "macro_risk_only_risk_relief": 0.25,
        "macro_risk_only_neutral": 0.50,
        "macro_risk_only_conflict": 0.50,
        "macro_risk_only_other": 0.50,
    }
    m["overlay_strength_no_gdp"] = m["macro_hsi_overlap_type_no_gdp"].map(strength_map).fillna(0.0)
    m["macro_delta_base_no_gdp"] = (normalize_addon(m["macro_defense_addon_no_gdp"]) * m["overlay_strength_no_gdp"]).clip(0, MAX_DELTA)

    keep = [
        "signal_month", "hsi_state", "hsi_risk_flag", "macro_data_available", "macro_signal_version",
        "macro_risk_flag_no_gdp", "macro_defense_addon_no_gdp", "macro_risk_source",
        "macro_hsi_overlap_type_no_gdp", "overlay_strength_no_gdp", "macro_delta_base_no_gdp",
    ]
    for c in ["rate_z_used", "fx_z_used", "rate_fx_departure_used"]:
        if c in m.columns:
            keep.append(c)
    return m[keep].copy()


# ============================================================
# 3. Lambda + macro 적용
# ============================================================
def apply_lambda(target: pd.DataFrame, lam: float) -> pd.DataFrame:
    df = target.sort_values("signal_month").reset_index(drop=True).copy()
    tcols = ["target_w_069500", "target_w_114260", "target_w_153130"]
    actual = []
    for i, row in df.iterrows():
        target_w = row[tcols].astype(float).to_numpy()
        if i == 0:
            w = target_w
        else:
            w = actual[-1] + lam * (target_w - actual[-1])
        w = np.clip(w, 0, 1)
        w = w / w.sum()
        actual.append(w)
    arr = np.vstack(actual)
    df[["lambda_w_069500", "lambda_w_114260", "lambda_w_153130"]] = arr
    return df


def turnover(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    x = 0.5 * df[cols].diff().abs().sum(axis=1)
    x.iloc[0] = 0.0
    return x.fillna(0.0)


def run_one(target: pd.DataFrame, macro: pd.DataFrame, rets: pd.DataFrame, lam: float, scale: float) -> pd.DataFrame:
    df = apply_lambda(target, lam).merge(macro, on="signal_month", how="left")
    df["macro_delta_base_no_gdp"] = pd.to_numeric(df["macro_delta_base_no_gdp"], errors="coerce").fillna(0.0)
    df["macro_scale"] = scale
    df["macro_overlay_delta"] = (df["macro_delta_base_no_gdp"] * scale).clip(0, MAX_DELTA)
    df["macro_overlay_delta"] = np.minimum(df["macro_overlay_delta"], df["lambda_w_069500"])
    df["weight_069500"] = df["lambda_w_069500"] - df["macro_overlay_delta"]
    df["weight_114260"] = df["lambda_w_114260"] + df["macro_overlay_delta"] * TO_BOND
    df["weight_153130"] = df["lambda_w_153130"] + df["macro_overlay_delta"] * TO_CASH
    wcols = ["weight_069500", "weight_114260", "weight_153130"]
    df[wcols] = df[wcols].div(df[wcols].sum(axis=1), axis=0)
    df = df.merge(rets, on="return_month", how="inner").sort_values("return_month").reset_index(drop=True)
    df["strategy_return"] = df["weight_069500"] * df["ret_069500"] + df["weight_114260"] * df["ret_114260"] + df["weight_153130"] * df["ret_153130"]
    df["turnover"] = turnover(df, wcols)
    df["cum_return"] = (1 + df["strategy_return"]).cumprod()
    df["drawdown"] = df["cum_return"] / df["cum_return"].cummax() - 1
    df["lambda_value"] = lam
    df["strategy_id"] = f"lambda_{lam:.1f}_macro_{scale:.2f}"
    return df


# ============================================================
# 4. 성과 계산
# ============================================================
def safe_div(a, b):
    return np.nan if b == 0 or pd.isna(b) else a / b


def cagr(cum_end: float, dates: pd.Series) -> float:
    years = (pd.to_datetime(dates.iloc[-1]) - pd.to_datetime(dates.iloc[0])).days / 365.25
    if years <= 0:
        years = len(dates) / PERIODS_PER_YEAR
    return cum_end ** (1 / years) - 1


def metrics(ts: pd.DataFrame, cost_bps: int = 0) -> dict:
    r = pd.to_numeric(ts["strategy_return"], errors="coerce").fillna(0.0)
    tv = pd.to_numeric(ts["turnover"], errors="coerce").fillna(0.0)
    if cost_bps:
        r = r - tv * (cost_bps / 10000)
    cum = (1 + r).cumprod()
    dd = cum / cum.cummax() - 1
    cg = cagr(float(cum.iloc[-1]), ts["return_month"])
    vol = r.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR)
    downside = r[r < 0]
    downvol = downside.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR)
    mdd = float(dd.min())
    return {
        "months": len(r),
        "final_cumulative_return": float(cum.iloc[-1]),
        "CAGR_pct": cg * 100,
        "annual_volatility_pct": vol * 100,
        "MDD_pct": mdd * 100,
        "abs_MDD_pct": abs(mdd) * 100,
        "Sharpe": safe_div(r.mean() * PERIODS_PER_YEAR, vol),
        "Sortino": safe_div(r.mean() * PERIODS_PER_YEAR, downvol),
        "Calmar": safe_div(cg, abs(mdd)),
        "WinRate_pct": (r > 0).mean() * 100,
        "avg_monthly_return_pct": r.mean() * 100,
        "best_month_pct": r.max() * 100,
        "worst_month_pct": r.min() * 100,
        "avg_turnover_pct": tv.mean() * 100,
        "max_turnover_pct": tv.max() * 100,
    }


def build_summary(all_ts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sid, sub in all_ts.groupby("strategy_id"):
        lam = float(sub["lambda_value"].iloc[0])
        scale = float(sub["macro_scale"].iloc[0])
        gross = metrics(sub, 0)
        cost = metrics(sub, COST_BPS)
        version = sub["macro_signal_version"].dropna().astype(str).mode()
        rows.append({
            "strategy_id": sid,
            "lambda_value": lam,
            "macro_scale": scale,
            **gross,
            "CAGR_pct_20bp_cost": cost["CAGR_pct"],
            "cost_drag_20bp": gross["CAGR_pct"] - cost["CAGR_pct"],
            "macro_signal_version": version.iloc[0] if len(version) else "unknown",
            "adjusted_months": int((sub["macro_overlay_delta"] > 0).sum()),
            "avg_macro_overlay_delta_pctp": sub["macro_overlay_delta"].mean() * 100,
            "max_macro_overlay_delta_pctp": sub["macro_overlay_delta"].max() * 100,
        })
    s = pd.DataFrame(rows).sort_values(["lambda_value", "macro_scale"]).reset_index(drop=True)
    for lam in s["lambda_value"].unique():
        mask = s["lambda_value"] == lam
        base = s[mask & (s["macro_scale"] == 0.0)].iloc[0]
        for col in ["CAGR_pct", "MDD_pct", "abs_MDD_pct", "Sharpe", "Calmar", "avg_turnover_pct", "cost_drag_20bp"]:
            s.loc[mask, f"{col}_diff_vs_lambda_base"] = s.loc[mask, col] - base[col]
    s["candidate_decision"] = "diagnostic"
    s.loc[s["macro_scale"] == 0, "candidate_decision"] = "lambda_base"
    ok = (
        (s["macro_scale"] > 0)
        & (s["CAGR_pct_diff_vs_lambda_base"] >= -0.30)
        & (s["avg_turnover_pct_diff_vs_lambda_base"] <= 1.00)
        & ((s["abs_MDD_pct_diff_vs_lambda_base"] <= -0.30) | (s["Calmar_diff_vs_lambda_base"] >= 0))
    )
    s.loc[ok, "candidate_decision"] = "macro_candidate"
    return s


def ranked(summary: pd.DataFrame) -> pd.DataFrame:
    out = summary.copy()
    def norm(x, higher=True):
        x = pd.to_numeric(x, errors="coerce")
        if x.notna().sum() <= 1:
            return pd.Series(0.5, index=x.index)
        mn, mx = x.min(skipna=True), x.max(skipna=True)
        if pd.isna(mn) or pd.isna(mx) or mx == mn:
            return pd.Series(0.5, index=x.index)
        z = (x - mn) / (mx - mn)
        return z if higher else 1 - z
    out["selection_score"] = (
        norm(out["CAGR_pct"], True) * 2.0
        + norm(out["abs_MDD_pct"], False) * 3.0
        + norm(out["Sharpe"], True) * 1.5
        + norm(out["Calmar"], True) * 2.5
        + norm(out["avg_turnover_pct"], False) * 3.0
        + norm(out["cost_drag_20bp"], False) * 2.0
    ) / 14.0
    return out.sort_values("selection_score", ascending=False).reset_index(drop=True)


def dashboard_rows(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in summary.iterrows():
        lam, scale = float(r["lambda_value"]), float(r["macro_scale"])
        if scale == 0:
            model_id = f"Lambda {lam:.1f}"
            family = "lambda"
            decision = "final_candidate"
            relation = "HSI 상태별 목표비중으로 이동하되 λ 부분조정만 적용한 기준 후보입니다."
            interp = "macro overlay를 얹지 않은 Lambda 기준 후보입니다."
        else:
            model_id = f"Lambda {lam:.1f} + Macro {scale:.2f}"
            family = "lambda_macro_overlay"
            decision = r["candidate_decision"]
            relation = "Lambda 부분조정 후보 위에 GDP를 제외한 금리·환율 macro companion 보조값을 약하게 반영한 후보입니다."
            interp = "macro_scale은 최적화 계수가 아니라 macro 보조 신호의 방어 강도 민감도 계수입니다."
        rows.append({
            "model_id": model_id,
            "family": family,
            "stage": "current",
            "decision": decision,
            "cagr": round(float(r["CAGR_pct"]), 4),
            "mdd": round(float(r["MDD_pct"]), 4),
            "abs_mdd": round(float(r["abs_MDD_pct"]), 4),
            "sharpe": round(float(r["Sharpe"]), 6),
            "calmar": round(float(r["Calmar"]), 6),
            "avg_turnover": round(float(r["avg_turnover_pct"]), 4),
            "max_turnover": round(float(r["max_turnover_pct"]), 4),
            "cost_drag_20bp": round(float(r["cost_drag_20bp"]), 6),
            "hsi_relation": relation,
            "interpretation": interp,
            "source_note": f"15번 lambda + macro overlay sensitivity, macro_signal_version={r['macro_signal_version']}",
        })
    return pd.DataFrame(rows)


def write_note(summary: pd.DataFrame, rank: pd.DataFrame):
    version = summary["macro_signal_version"].mode().iloc[0]
    top = rank.iloc[0]
    text = f"""# 15번 Lambda + Macro Overlay Sensitivity Note

## 목적
Lambda 0.1과 Lambda 0.3 후보 위에 macro companion을 약하게 얹었을 때 MDD를 낮추면서 CAGR과 Turnover를 크게 훼손하지 않는지 확인한다.

```text
HSI = 시장상태 판단
lambda = 목표비중으로 이동하는 속도
macro companion = 약한 방어 보정
```

## 조합 수

```text
lambda 후보: {LAMBDAS}
macro_scale 후보: {MACRO_SCALES}
전체 조합 수: {len(summary)}
조합 상한: {MAX_COMBINATIONS}
```

## GDP 처리
GDP는 직접 위험 조건에서 제외했다.
사용된 macro signal version은 다음과 같다.

```text
{version}
```

`no_gdp_rate_fx_verified`이면 금리·환율 컬럼을 이용해 GDP 제외 신호가 확인된 것이다.  
`fallback_existing_macro_may_include_gdp`이면 필요한 세부 컬럼이 부족하여 기존 macro_defense_addon을 사용한 것이므로 GDP 제외 검증으로는 제한이 있다.

## 동적 선택 점수 1순위

```text
strategy_id: {top['strategy_id']}
selection_score: {top['selection_score']:.4f}
CAGR: {top['CAGR_pct']:.2f}%
MDD: {top['MDD_pct']:.2f}%
Sharpe: {top['Sharpe']:.3f}
Calmar: {top['Calmar']:.3f}
avg Turnover: {top['avg_turnover_pct']:.2f}%
```

## 보고서 문장
후속 실험에서는 Lambda 0.1과 Lambda 0.3 후보 위에 macro companion을 직접 비중 보정값으로 얹는 방식을 비교하였다. 이때 macro_scale은 성과를 임의로 개선하기 위한 최적화 계수가 아니라, macro 보조 신호의 반영 강도에 따른 민감도를 확인하기 위한 사전 설정 범위로 사용하였다. GDP는 계절성·기저효과·발표 지연 문제를 고려하여 직접 위험 조건에서 제외하고, 금리와 환율의 위험형 이탈을 중심으로 macro overlay를 구성하였다.
"""
    OUT_NOTE.write_text(text, encoding="utf-8-sig")


def main():
    ensure_dirs()
    n = len(LAMBDAS) * len(MACRO_SCALES)
    if n > MAX_COMBINATIONS:
        raise ValueError(f"조합 수가 너무 많습니다: {n}개. 상한은 {MAX_COMBINATIONS}개입니다.")

    print("=" * 80)
    print("15_lambda_macro_overlay_sensitivity.py 실행 시작")
    print("=" * 80)
    print(f"[0] 조합 수 확인: {n}개")

    print("[1] 입력 파일 로드")
    target = load_target_weights()
    macro = build_macro_bridge()
    rets = load_returns()
    print(f"    target weights shape = {target.shape}")
    print(f"    macro bridge shape   = {macro.shape}")
    print(f"    monthly returns shape= {rets.shape}")

    print("[2] 조합 실행")
    all_ts = []
    for lam in LAMBDAS:
        for scale in MACRO_SCALES:
            print(f"    run: lambda={lam:.1f}, macro_scale={scale:.2f}")
            all_ts.append(run_one(target, macro, rets, lam, scale))
    all_ts = pd.concat(all_ts, ignore_index=True)

    print("[3] 성과표 계산")
    summary = build_summary(all_ts)
    rank = ranked(summary)
    dash = dashboard_rows(summary)

    print("[4] 저장")
    all_ts.to_csv(OUT_TS, index=False, encoding="utf-8-sig")
    summary.to_csv(OUT_SUMMARY, index=False, encoding="utf-8-sig")
    rank.to_csv(OUT_RANKED, index=False, encoding="utf-8-sig")
    dash.to_csv(OUT_DASHBOARD, index=False, encoding="utf-8-sig")
    write_note(summary, rank)

    print(f"    저장: {OUT_TS}")
    print(f"    저장: {OUT_SUMMARY}")
    print(f"    저장: {OUT_RANKED}")
    print(f"    저장: {OUT_DASHBOARD}")
    print(f"    저장: {OUT_NOTE}")

    show_cols = ["strategy_id", "CAGR_pct", "MDD_pct", "Sharpe", "Calmar", "avg_turnover_pct", "cost_drag_20bp", "candidate_decision"]
    print("\n[성과 요약]")
    print(summary[show_cols].to_string(index=False))

    rank_cols = ["strategy_id", "selection_score", "CAGR_pct", "MDD_pct", "Sharpe", "Calmar", "avg_turnover_pct", "candidate_decision"]
    print("\n[동적 점수 상위 후보]")
    print(rank[rank_cols].head(8).to_string(index=False))
    print("=" * 80)
    print("15_lambda_macro_overlay_sensitivity.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
