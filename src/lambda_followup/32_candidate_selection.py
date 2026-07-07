# -*- coding: utf-8 -*-
"""
32_candidate_selection.py — E29 후보 선별 (자유 가중치 0개 방식)

배경:
  Score(λ) = Calmar + a·Sharpe − b·Turnover − c·CostSensitivity 형태의 합성점수는
  a·b·c가 사후 조정 가능한 자유 파라미터가 되어 과적합 통로가 되고,
  v2 문서 §1.7 "CAGR 1등 채택 금지" / §3.6 "단일 점수만 보지 않음"과도 충돌한다.
  → 폐기하고, 문서의 4차 필터를 그대로 수식화한 아래 절차로 대체한다.

절차 (사전등록, 결과 후 변경 금지):
  [필터 A] 기술 오류 제거: 결측·비정상 Turnover (1차 필터)
  [필터 B] 방어형 제약 (2차 필터, 하드 제약 — 가중치 아님):
      B1. MDD ≥ min(대칭 λ=0.1, λ=0.3의 MDD)   ← 대칭 대비 악화 금지
      B2. avg Turnover ≤ 대칭 λ=0.3 Turnover × 1.5
  [필터 C] 인접 안정 (3차 필터): neighbor_min_calmar ≥ 대칭 λ=0.1 Calmar의 80%
      (고립된 최고점 배제)
  [선별]  통과 셀 중 (calmar_net10bp ↑, mdd ↑, avg_turnover ↓) 3축 Pareto
          비지배 집합 전체를 후보로 보고. 우승자 1개를 뽑지 않는다.
  [스칼라] 소통용 단일 수치가 필요하면 calmar_net10bp 하나만 사용
          (Turnover·비용 페널티가 실제 비용모형으로 수익률 단위에 내재화 → 자유 가중치 불필요)

입력: output/tables/main_final_asymmetric_lambda_grid.csv (E29 실행 후)
출력: output/tables/main_final_candidate_selection_table.csv
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

GRID_FILE = C.TABLE_DIR / f"{C.FINAL_PREFIX}asymmetric_lambda_grid.csv"

# 사전등록 제약 배수 (경제적 해석이 있는 상수 — 성과를 보고 조정하지 않는다)
TURNOVER_CAP_MULT = 1.5      # 대칭 λ=0.3 대비 회전율 상한 배수
NEIGHBOR_CALMAR_FLOOR = 0.8  # 인접 셀 Calmar 하한 (대칭 λ=0.1 Calmar 대비 비율)
COST_BP_FOR_SCALAR = 10      # 소통용 스칼라의 비용 가정 (보수적 중간값)


def pareto_non_dominated(df: pd.DataFrame, maximize: list, minimize: list) -> pd.Series:
    """3축 Pareto 비지배 여부."""
    vals = df[maximize + minimize].values.copy()
    vals[:, len(maximize):] *= -1  # minimize 축 부호 반전 → 전부 maximize
    n = len(vals)
    dominated = np.zeros(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if np.all(vals[j] >= vals[i]) and np.any(vals[j] > vals[i]):
                dominated[i] = True
                break
    return pd.Series(~dominated, index=df.index, name="pareto_non_dominated")


def main() -> None:
    if not GRID_FILE.exists():
        raise FileNotFoundError(f"E29 결과가 없습니다: {GRID_FILE} — 29번을 먼저 실행하세요.")
    g = pd.read_csv(GRID_FILE)

    # calmar_net10bp: 10bp 비용차감 CAGR / |MDD|  (소통용 스칼라, 자유 가중치 없음)
    g["calmar_net10bp"] = g[f"cagr_net_{COST_BP_FOR_SCALAR}bp"] / g["mdd_pct"].abs()

    sym01 = g[(g["lambda_up"] == 0.1) & (g["lambda_down"] == 0.1)].iloc[0]
    sym03 = g[(g["lambda_up"] == 0.3) & (g["lambda_down"] == 0.3)].iloc[0]

    g["pass_A_valid"] = g[["cagr_pct", "mdd_pct", "calmar", "avg_turnover_pct"]].notna().all(axis=1)
    mdd_floor = min(sym01["mdd_pct"], sym03["mdd_pct"])           # 더 나쁜(더 음수) 대칭 MDD
    g["pass_B1_mdd"] = g["mdd_pct"] >= mdd_floor
    to_cap = sym03["avg_turnover_pct"] * TURNOVER_CAP_MULT
    g["pass_B2_turnover"] = g["avg_turnover_pct"] <= to_cap
    calmar_floor = sym01["calmar"] * NEIGHBOR_CALMAR_FLOOR
    g["pass_C_neighbor"] = g["neighbor_min_calmar"] >= calmar_floor

    g["pass_all_filters"] = g[["pass_A_valid", "pass_B1_mdd",
                               "pass_B2_turnover", "pass_C_neighbor"]].all(axis=1)

    feasible = g[g["pass_all_filters"]].copy()
    if feasible.empty:
        g["pareto_non_dominated"] = False
        verdict = "통과 셀 없음 → 대칭 λ 후보(0.1/0.3) 유지, 비대칭은 '증분 제한적'으로 기록"
    else:
        nd = pareto_non_dominated(feasible,
                                  maximize=["calmar_net10bp", "mdd_pct"],
                                  minimize=["avg_turnover_pct"])
        g["pareto_non_dominated"] = False
        g.loc[nd.index, "pareto_non_dominated"] = nd
        verdict = "Pareto 비지배 집합을 후보로 보고 (우승자 1개를 뽑지 않음)"

    g["final_class"] = np.where(g["pareto_non_dominated"], "후보(Pareto)",
                        np.where(g["pass_all_filters"], "보류(지배됨)", "제외(필터 미통과)"))

    out_cols = ["lambda_up", "lambda_down", "region", "cagr_pct", "mdd_pct", "calmar",
                "calmar_net10bp", "avg_turnover_pct", "neighbor_min_calmar",
                "tail_strategy_avg_pct",
                "pass_B1_mdd", "pass_B2_turnover", "pass_C_neighbor",
                "pareto_non_dominated", "final_class"]
    out = g[out_cols].sort_values(["final_class", "calmar_net10bp"],
                                  ascending=[True, False])
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(C.TABLE_DIR / f"{C.FINAL_PREFIX}candidate_selection_table.csv",
               index=False, encoding="utf-8-sig")

    print("[완료] 32_candidate_selection (자유 가중치 0개)")
    print(f"제약: MDD ≥ {mdd_floor:.2f}%, Turnover ≤ {to_cap:.2f}%, "
          f"인접 Calmar ≥ {calmar_floor:.3f}")
    print(f"판정: {verdict}")
    print(out.round(3).to_string(index=False))
    print("\n※ 여기서 나온 후보는 게이트 ⑤⑥(IS/OOS·walk-forward, 31번)을 통과해야 '채택'.")


if __name__ == "__main__":
    main()
