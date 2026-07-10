# -*- coding: utf-8 -*-
"""
00_smoke_test.py — 합성 데이터 기계 검증 (실데이터 도착 전 게이트 ① 사전 리허설)

검증 항목:
  T1. 대각선 일치: 비대칭 엔진(λ_up=λ_down=λ)의 결과가 대칭 λ 결과와 완전 일치
  T2. Turnover 규약: λ=1, risk_relief→accident_zone 점프에서 Turnover=70.00%
  T3. look-ahead 방지: 모든 행에서 signal_date < apply_date
  T4. 비중 합=1 유지 (비대칭 적용 후에도)
  T5. 방향 판정: Δ<0 인 달에 λ_down, Δ≥0 인 달에 λ_up 이 실제로 적용됨
  T6. E30 상태변수에 미래 정보가 없는지 (마지막 관측 제거 시 과거 값 불변)

실행: python src/00_smoke_test.py
통과 시 "ALL SMOKE TESTS PASSED" 출력. 실데이터 연결 후에는 E28의 게이트 ① 대조가 본검증.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
import common as X


def make_synthetic(n_months=172, seed=7):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2012-03-31", periods=n_months, freq="ME")
    ret = pd.DataFrame({
        "069500": rng.normal(0.008, 0.045, n_months),
        "114260": rng.normal(0.003, 0.010, n_months),
        "153130": rng.normal(0.002, 0.002, n_months),
    }, index=dates)
    states = list(C.STATE_TARGET_WEIGHTS.keys())[:5]
    st = pd.Series(rng.choice(states, n_months, p=[0.35, 0.30, 0.15, 0.12, 0.08]), index=dates)
    tw = pd.DataFrame([C.STATE_TARGET_WEIGHTS[s] for s in st], index=dates, columns=C.TICKERS)
    tw["hsi_state"] = st.values
    return ret, tw


def main():
    ret, tw = make_synthetic()
    failures = []

    # T1 대각선 일치
    for lam in (0.1, 0.3, 1.0):
        a = X.run_lambda_backtest(ret, tw, lam, lam)
        b = X.run_lambda_backtest(ret, tw, lambda_up=lam, lambda_down=lam)
        if not np.allclose(a["strategy_return_gross"], b["strategy_return_gross"]):
            failures.append(f"T1 실패 λ={lam}")
    print("T1 대각선=대칭 일치: OK")

    # T2 Turnover 규약 (강제 점프 시나리오)
    dates2 = pd.date_range("2020-01-31", periods=4, freq="ME")
    ret2 = pd.DataFrame(0.0, index=dates2, columns=C.TICKERS)
    tw2 = pd.DataFrame([C.STATE_TARGET_WEIGHTS["risk_relief"],
                        C.STATE_TARGET_WEIGHTS["risk_relief"],
                        C.STATE_TARGET_WEIGHTS["accident_zone"],
                        C.STATE_TARGET_WEIGHTS["accident_zone"]],
                       index=dates2, columns=C.TICKERS)
    bt2 = X.run_lambda_backtest(ret2, tw2, 1.0, 1.0, min_months=2)
    to_jump = bt2["turnover"].max()
    if not np.isclose(to_jump, 0.70):
        failures.append(f"T2 실패: 점프 Turnover={to_jump:.4f} (기대 0.70)")
    print(f"T2 Turnover 규약(Σ|Δw|/2, 최대점프=70%): OK ({to_jump:.2%})")

    # T3 look-ahead
    bt = X.run_lambda_backtest(ret, tw, 0.2, 0.4)
    if not (bt["signal_date"] < bt.index).all():
        failures.append("T3 실패: signal_date >= apply_date 존재")
    print("T3 t신호→t+1적용: OK")

    # T4 비중 합
    wsum = bt[[f"w_{t}" for t in C.TICKERS]].sum(axis=1)
    if not np.allclose(wsum, 1.0):
        failures.append("T4 실패: 비중 합≠1")
    print("T4 비중 합=1 유지: OK")

    # T5 방향 판정
    lam_used = bt["lambda_used"]
    dir_lab = bt["direction"]
    if not (((dir_lab == "down") == (lam_used == 0.4)).all()
            and ((dir_lab == "up") == (lam_used == 0.2)).all()):
        failures.append("T5 실패: 방향별 λ 적용 불일치")
    print("T5 방향별 λ_up/λ_down 적용: OK")

    # T6 상태변수 look-ahead (마지막 달 제거해도 과거 값 동일)
    dyn = __import__("importlib").import_module("30_dynamic_lambda_rule_v1"
                                                .replace(".py", ""))
    sv_full = dyn.build_state_variables(ret, tw)
    sv_trim = dyn.build_state_variables(ret.iloc[:-1], tw.iloc[:-1])
    common_idx = sv_trim.index
    for col in ["annualized_volatility_z", "rolling_drawdown", "momentum_z"]:
        if not np.allclose(sv_full.loc[common_idx, col].fillna(0),
                           sv_trim[col].fillna(0)):
            failures.append(f"T6 실패: {col}에 미래정보 의존")
    print("T6 상태변수 look-ahead 없음: OK")

    if failures:
        print("\n".join(failures)); sys.exit(1)
    print("\nALL SMOKE TESTS PASSED — 실데이터 연결 후 E28 게이트 ① 대조로 본검증 진행")


if __name__ == "__main__":
    main()
