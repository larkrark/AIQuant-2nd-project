# -*- coding: utf-8 -*-
"""
34_adoption_decision.py — 사전등록 채택 결정규칙 적용 (v3)

프레이밍 (팀 합의 반영):
  RA는 시장 상태에 따라 매 시점 전략을 제시하고 사용자 성향(방어적 참여자)에 맞춰
  추천할 의무가 있다. 따라서 판정은 superiority(우월 입증)가 아니라
  non-inferiority(비열등) 기준이다:

  동적·비대칭 λ(시변 실행 layer)가 OOS·10bp 비용차감 기준으로 아래 4개 마진을
  모두 만족하고 8게이트를 통과하면 → '기본 추천 layer로 채택'.
  하나라도 실패하면 → '고정 λ(0.1/0.3) fallback' + "동적 층의 증분이 제한적" 기록.
  fallback 시에도 HSI 상태가 매월 w*를 바꾸므로 배분은 시변 적응 전략이다(1차 적응).

  마진(config.ADOPTION_RULE, 결과 후 변경 금지):
    ① Calmar_net10bp ≥ 대칭 최우수 × 0.90
    ② MDD 악화 ≤ 대칭 λ=0.1 대비 2.0%p
    ③ tail-month 평균수익 악화 ≤ 0.3%p (대칭 λ=0.1 대비)
    ④ avg Turnover ≤ 대칭 λ=0.3 × 1.5

출력: output/tables/main_final_adoption_decision.csv
"""

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
import common as X

dyn = importlib.import_module("30_dynamic_lambda_rule_v1")
dyn_macro = importlib.import_module("30_dynamic_lambda_rule_v1_macro")
R = C.ADOPTION_RULE

# 판정 대상 시변 layer 후보 (32번 Pareto 결과 확인 후 조정 — 이력 주석 기록)
TIME_VARYING_CANDIDATES = [
    ("asym_up0.1_down0.3", 0.10, 0.30),
    ("asym_up0.1_down0.5", 0.10, 0.50),
    ("asym_up0.2_down0.3", 0.20, 0.30),
    ("dynamic_v1", None, None),
    ("dynamic_v1_macro", None, None),
]


def oos_net_metrics(bt: pd.DataFrame, label: str) -> dict:
    seg = bt.loc[C.OOS_START:C.OOS_END]
    net = seg["strategy_return_gross"] - seg["turnover"] * (R["cost_bp"] / 10000.0)
    m = X.perf_metrics(net, seg["turnover"], label)
    m["calmar_net"] = m["calmar"]
    return m, seg, net


def main() -> None:
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()
    risk_r = returns[C.RISK_TICKER]

    # 대칭 참조
    refs = {}
    for lam in (0.1, 0.3):
        bt = X.run_lambda_backtest(returns, target_w, lam, lam)
        m, seg, net = oos_net_metrics(bt, f"sym_{lam}")
        tm = X.tail_month_defense(net, risk_r.loc[seg.index])
        m["tail_avg_pct"] = tm["strategy_avg_pct"]
        refs[lam] = m
    calmar_best_sym = max(refs[0.1]["calmar_net"], refs[0.3]["calmar_net"])
    mdd_ref = refs[0.1]["mdd_pct"]
    tail_ref = refs[0.1]["tail_avg_pct"]
    to_cap = refs[0.3]["avg_turnover_pct"] * R["turnover_cap_mult"]

    rows = []
    for name, lu, ld in TIME_VARYING_CANDIDATES:
        if name == "dynamic_v1":
            sv = dyn.build_state_variables(returns, target_w)
            lam_t, _ = dyn.assign_lambda(sv)
            lam_t = lam_t.fillna(C.E30_RULE_V1["lambda_base"])

            bt = X.run_lambda_backtest(
                returns,
                target_w,
                np.nan,
                np.nan,
                lambda_series=lam_t,
            )

        elif name == "dynamic_v1_macro":
            sv_macro = dyn_macro.build_state_variables_macro(returns, target_w)
            lam_macro, cond_macro, reason_macro = dyn_macro.assign_lambda_macro(sv_macro)
            lam_macro = lam_macro.fillna(C.E30_RULE_V1["lambda_base"])

            bt = X.run_lambda_backtest(
                returns,
                target_w,
                np.nan,
                np.nan,
                lambda_series=lam_macro,
            )

        else:
            bt = X.run_lambda_backtest(returns, target_w, lu, ld)
            
        m, seg, net = oos_net_metrics(bt, name)
        tm = X.tail_month_defense(net, risk_r.loc[seg.index])

        c1 = m["calmar_net"] >= R["calmar_ratio_min"] * calmar_best_sym
        c2 = m["mdd_pct"] >= mdd_ref - R["mdd_worsen_max_pp"]
        c3 = tm["strategy_avg_pct"] >= tail_ref - R["tail_worsen_max_pp"]
        c4 = m["avg_turnover_pct"] <= to_cap
        non_inferior = c1 and c2 and c3 and c4
        rows.append({
            "strategy": name, "segment": "OOS(net10bp)",
            "calmar_net": m["calmar_net"], "mdd_pct": m["mdd_pct"],
            "tail_avg_pct": tm["strategy_avg_pct"],
            "avg_turnover_pct": m["avg_turnover_pct"],
            "①calmar≥0.9×sym": c1, "②mdd_worsen≤2pp": c2,
            "③tail_worsen≤0.3pp": c3, "④turnover≤1.5×sym0.3": c4,
            "non_inferior": non_inferior,
            "판정": ("채택 후보(시변 기본 layer) — 8게이트 통과 조건부"
                    if non_inferior else "미달 → 고정 λ fallback 대상"),
        })

    dec = pd.DataFrame(rows)
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    dec.to_csv(C.TABLE_DIR / f"{C.FINAL_PREFIX}adoption_decision.csv",
               index=False, encoding="utf-8-sig")

    print("[완료] 34_adoption_decision — 사전등록 비열등 판정 (OOS, 10bp net)")
    print(f"참조: 대칭 최우수 Calmar_net={calmar_best_sym:.3f}, "
          f"MDD 기준={mdd_ref:.2f}%, tail 기준={tail_ref:.2f}%, TO 상한={to_cap:.2f}%")
    print(dec.round(3).to_string(index=False))
    if dec["non_inferior"].any():
        print("\n→ 비열등 후보 존재: 8게이트(31번) 통과 시 시변 layer를 기본 추천으로 채택.")
    else:
        print("\n→ 전 후보 미달: 고정 λ(0.1/0.3) fallback. 보고서에는 '동적 층의 증분이 제한적'으로"
              " 기록하고, 고정 λ도 HSI 상태 기반 시변 배분(1차 적응)임을 명시.")


if __name__ == "__main__":
    main()
