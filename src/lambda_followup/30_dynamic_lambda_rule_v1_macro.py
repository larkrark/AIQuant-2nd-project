# -*- coding: utf-8 -*-
"""
30_dynamic_lambda_rule_v1_macro.py — E30-M Macro-aware 조건부(동적) λ 규칙

목적
----
기존 dynamic_v1의 조건부 λ 규칙에 MacroRisk 조건을 명시적으로 반영한다.

핵심 규칙
---------
기본 λ = 0.3

고위험 조건:
    annualized_volatility_z > 1
    또는 rolling_drawdown < -10%
    또는 MacroRisk >= 2
    → λ = 0.1

안정 완화 조건:
    risk_relief 3개월 이상 지속
    그리고 annualized_volatility_z < 0
    그리고 momentum_z > 0
    → λ = 0.5

그 외:
    λ = 0.3

주의
----
이 파일은 기존 30_dynamic_lambda_rule_v1.py를 덮어쓰지 않는다.
기존 dynamic_v1과 macro-aware dynamic_v1_macro를 비교하기 위한 별도 실험 파일이다.

출력
----
output/tables/main_final_dynamic_lambda_macro_comparison.csv
output/tables/flex_dynamic_lambda_macro_path.csv
"""

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
import common as X

base_dyn = importlib.import_module("30_dynamic_lambda_rule_v1")

R = C.E30_RULE_V1


def load_macro_risk_score(index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series, str]:
    """
    factor_inputs_monthly.csv에서 MacroRisk를 읽어 dynamic λ용 macro_risk_score로 변환한다.

    허용 열 이름:
    - macro_risk_score
    - MacroRisk
    - macro_risk
    - Macro_Risk

    반환:
    - macro_risk_score: index에 맞춘 0/1/2 점수
    - macro_available: 해당 월 macro 값이 실제로 존재했는지 여부
    - used_col: 실제 사용한 열 이름
    """
    if not C.FACTORS_FILE.exists():
        score = pd.Series(0.0, index=index, name="macro_risk_score")
        available = pd.Series(False, index=index, name="macro_available")
        return score, available, "NO_FACTOR_FILE"

    f = pd.read_csv(C.FACTORS_FILE, index_col=0, parse_dates=True).sort_index()

    candidates = ["macro_risk_score", "MacroRisk", "macro_risk", "Macro_Risk"]
    used_col = None
    for col in candidates:
        if col in f.columns:
            used_col = col
            break

    if used_col is None:
        score = pd.Series(0.0, index=index, name="macro_risk_score")
        available = pd.Series(False, index=index, name="macro_available")
        return score, available, "NO_MACRO_COLUMN"

    raw = pd.to_numeric(f[used_col], errors="coerce").reindex(index)
    available = raw.notna()
    score = raw.fillna(0.0).astype(float)
    score.name = "macro_risk_score"
    available.name = "macro_available"

    return score, available, used_col


def build_state_variables_macro(returns: pd.DataFrame, target_w: pd.DataFrame) -> pd.DataFrame:
    """
    기존 dynamic_v1의 상태변수에 MacroRisk를 명시적으로 결합한다.
    volatility_z, rolling_drawdown, momentum_z, relief_persist는 기존 로직을 재사용한다.
    """
    sv = base_dyn.build_state_variables(returns, target_w).copy()

    macro_score, macro_available, used_col = load_macro_risk_score(sv.index)

    # 기존 build_state_variables가 만든 macro 열이 있더라도 여기서 명시적으로 덮어쓴다.
    sv["macro_risk_score"] = macro_score
    sv["macro_available"] = macro_available

    # 감사용 메타 열
    sv["macro_source_col"] = used_col
    sv["macro_high_risk_flag"] = sv["macro_available"] & (
        sv["macro_risk_score"] >= R["macro_risk_high"]
    )

    return sv


def pick_col(df: pd.DataFrame, candidates: list[str], label: str) -> str:
    """
    후보 열 이름 중 실제 존재하는 첫 번째 열을 반환한다.
    """
    for col in candidates:
        if col in df.columns:
            return col
    raise KeyError(
        f"{label} 열을 찾을 수 없습니다. "
        f"후보={candidates}, 실제 열={list(df.columns)}"
    )


def assign_lambda_macro(sv: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MacroRisk를 포함한 E30-M λ 배정 규칙.
    고위험 조건이 안정완화 조건보다 우선한다.
    """

    vol_z_col = pick_col(
        sv,
        ["annualized_volatility_z", "volatility_z", "vol_z"],
        "annualized volatility z-score",
    )

    drawdown_col = pick_col(
        sv,
        ["rolling_drawdown", "drawdown", "dd"],
        "rolling drawdown",
    )

    momentum_z_col = pick_col(
        sv,
        ["momentum_z", "mom_z"],
        "momentum z-score",
    )

    relief_col = pick_col(
        sv,
        ["relief_persist", "risk_relief_persist", "relief_persist_months"],
        "risk relief persistence",
    )

    high_risk_vol = sv[vol_z_col] > R["volatility_z_high"]
    high_risk_dd = sv[drawdown_col] < R["drawdown_low"]
    high_risk_macro = sv["macro_available"] & (
        sv["macro_risk_score"] >= R["macro_risk_high"]
    )

    high_risk = high_risk_vol | high_risk_dd | high_risk_macro

    stable_relief = (
        (sv[relief_col] >= R["relief_persist_months"])
        & (sv[vol_z_col] < R["volatility_z_calm"])
        & (sv[momentum_z_col] > R["momentum_z_positive"])
    )

    lam = pd.Series(R["lambda_base"], index=sv.index, name="lambda_t")
    label = pd.Series("base", index=sv.index, name="condition")

    lam[stable_relief] = R["lambda_stable_relief"]
    label[stable_relief] = "stable_relief"

    # 고위험 조건이 최종 우선권을 가진다.
    lam[high_risk] = R["lambda_high_risk"]
    label[high_risk] = "high_risk"

    reason = pd.Series("", index=sv.index, name="condition_reason")
    reason[high_risk_vol] = reason[high_risk_vol] + "|vol_z"
    reason[high_risk_dd] = reason[high_risk_dd] + "|drawdown"
    reason[high_risk_macro] = reason[high_risk_macro] + "|macro"
    reason[stable_relief & ~high_risk] = "stable_relief"
    reason = reason.str.lstrip("|")
    reason[reason == ""] = "base"

    return lam, label, reason


def add_net_cagr_columns(comp: pd.DataFrame, bt_map: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    거래비용 bps별 net CAGR을 comp에 추가한다.
    """
    comp = comp.copy()

    for row_idx, row in comp.iterrows():
        name = row["strategy"]
        bt = bt_map[name]
        for bps in C.COST_BPS_GRID:
            net = bt["strategy_return_gross"] - bt["turnover"] * (bps / 10000.0)
            cagr = ((1.0 + net).prod() ** (12.0 / len(net)) - 1.0) * 100.0
            comp.loc[row_idx, f"cagr_net_{bps}bp"] = cagr

    return comp


def main() -> None:
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()

    # 1. macro-aware dynamic λ
    sv_macro = build_state_variables_macro(returns, target_w)
    lam_macro, cond_macro, reason_macro = assign_lambda_macro(sv_macro)
    lam_macro = lam_macro.fillna(R["lambda_base"])

    bt_macro = X.run_lambda_backtest(
        returns,
        target_w,
        lambda_up=np.nan,
        lambda_down=np.nan,
        lambda_series=lam_macro,
    )

    # 2. 기존 dynamic_v1도 비교용으로 같이 계산
    sv_prev = base_dyn.build_state_variables(returns, target_w)
    lam_prev, cond_prev = base_dyn.assign_lambda(sv_prev)
    lam_prev = lam_prev.fillna(R["lambda_base"])

    bt_prev = X.run_lambda_backtest(
        returns,
        target_w,
        lambda_up=np.nan,
        lambda_down=np.nan,
        lambda_series=lam_prev,
    )

    # 3. 대칭 λ 비교군
    bt_01 = X.run_lambda_backtest(returns, target_w, lambda_up=0.10, lambda_down=0.10)
    bt_03 = X.run_lambda_backtest(returns, target_w, lambda_up=0.30, lambda_down=0.30)

    bt_map = {
        "dynamic_v1_macro": bt_macro,
        "dynamic_v1_previous": bt_prev,
        "lambda_0.1": bt_01,
        "lambda_0.3": bt_03,
    }

    rows = []
    for name, bt in bt_map.items():
        rows.append(
            X.perf_metrics(
                bt["strategy_return_gross"],
                bt["turnover"],
                name,
            )
        )

    comp = pd.DataFrame(rows)
    comp = add_net_cagr_columns(comp, bt_map)

    # 4. path 저장
    path_df = pd.concat(
        [
            sv_macro,
            lam_macro.rename("lambda_t"),
            cond_macro,
            reason_macro,
        ],
        axis=1,
    )

    # 적용월별 실제 포트폴리오 결과도 함께 저장
    bt_macro_out = bt_macro.copy()
    bt_macro_out.index.name = "apply_date"

    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)

    comp_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}dynamic_lambda_macro_comparison.csv"
    path_path = C.TABLE_DIR / f"{C.INTERIM_PREFIX}dynamic_lambda_macro_path.csv"
    bt_path = C.TABLE_DIR / f"{C.INTERIM_PREFIX}dynamic_lambda_macro_backtest_timeseries.csv"

    comp.to_csv(comp_path, index=False, encoding="utf-8-sig")
    path_df.to_csv(path_path, encoding="utf-8-sig")
    bt_macro_out.to_csv(bt_path, encoding="utf-8-sig")

    # 5. 출력
    print("[완료] E30-M — Macro-aware dynamic λ v1")
    print(f"사용 factor file: {C.FACTORS_FILE}")
    print("macro source column:", sv_macro["macro_source_col"].iloc[0])
    print("조건 분포:", cond_macro.value_counts().to_dict())
    print("고위험 사유 분포:")
    print(reason_macro.value_counts().to_string())

    print("\n[MacroRisk 분포]")
    print(sv_macro["macro_risk_score"].value_counts(dropna=False).sort_index().to_string())

    print("\n[성과 비교]")
    show_cols = [
        "strategy",
        "cagr_pct",
        "mdd_pct",
        "calmar",
        "ann_vol_pct",
        "sharpe",
        "avg_turnover_pct",
        "max_turnover_pct",
    ]
    print(comp[show_cols].round(3).to_string(index=False))

    print("\n[저장]")
    print(f"- {comp_path}")
    print(f"- {path_path}")
    print(f"- {bt_path}")


if __name__ == "__main__":
    main()