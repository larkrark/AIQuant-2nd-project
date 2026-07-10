# -*- coding: utf-8 -*-
"""
45_adoption_margin_sensitivity.py — Adoption decision 마진 민감도 분석

배경
----
34_adoption_decision.py의 비열등 판정 마진(config.ADOPTION_RULE):
  calmar_ratio_min = 0.90     (대칭 최우수 Calmar × 0.90 이상)
  mdd_worsen_max_pp = 2.0     (대칭 λ=0.1 대비 MDD 악화 2.0%p 이내)
  tail_worsen_max_pp = 0.3    (대칭 λ=0.1 대비 tail-month 악화 0.3%p 이내)
  turnover_cap_mult = 1.5     (대칭 λ=0.3 평균 Turnover × 1.5 이내)
은 "판정 기준"으로만 문서화되어 있고, 왜 0.90/2.0%p/0.3%p/1.5배인지 산출식은
없다. 이 마진은 최종 후보(dynamic_v1) 채택 여부를 직접 좌우하는 값이므로,
E30·θ 임계값보다 방어 우선순위가 높다.

목적
----
34번의 실제 후보별 성과지표(Calmar_net, MDD, tail-month 평균수익, 평균 Turnover)는
마진 값과 무관하게 고정되어 있다. 따라서 백테스트를 다시 돌릴 필요 없이,
4개 마진 각각을 baseline 주변에서 엄격/완화 방향으로 흔들면서 각 후보의
non_inferior 판정이 몇 %까지 강화해도 유지되는지(breaking point)를 계산한다.

방법
----
34번과 동일한 참조값(대칭 최우수 Calmar, MDD 기준, tail 기준, Turnover 상한)과
후보별 실측치를 재사용하여, 마진 그리드에 대해 판정식만 재적용한다.
"이 마진을 얼마나 강화해야 dynamic_v1이 탈락하는가"를 breaking point로 보고한다.

출력
----
- output/tables/main_final_adoption_margin_sensitivity_detail.csv
- output/tables/main_final_adoption_margin_sensitivity_breaking_points.csv
- docs/main_final_adoption_margin_sensitivity_note.md
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

BASELINE_MARGIN = dict(C.ADOPTION_RULE)

# 마진 민감도 그리드 (baseline을 중심으로 완화<->강화 방향 모두 포함, 사전 고정)
MARGIN_GRID = {
    "calmar_ratio_min":  [0.80, 0.85, 0.90, 0.95, 1.00],
    "mdd_worsen_max_pp": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
    "tail_worsen_max_pp": [0.1, 0.2, 0.3, 0.4, 0.5],
    "turnover_cap_mult": [1.0, 1.25, 1.5, 1.75, 2.0],
}

TIME_VARYING_CANDIDATES = [
    ("asym_up0.1_down0.3", 0.10, 0.30),
    ("asym_up0.1_down0.5", 0.10, 0.50),
    ("asym_up0.2_down0.3", 0.20, 0.30),
    ("dynamic_v1", None, None),
    ("dynamic_v1_macro", None, None),
]

OUTPUT_DETAIL = C.TABLE_DIR / f"{C.FINAL_PREFIX}adoption_margin_sensitivity_detail.csv"
OUTPUT_BREAKING = C.TABLE_DIR / f"{C.FINAL_PREFIX}adoption_margin_sensitivity_breaking_points.csv"
OUTPUT_NOTE = C.REPORT_DIR.parent / "docs" / f"{C.FINAL_PREFIX}adoption_margin_sensitivity_note.md"


def oos_net_metrics(bt: pd.DataFrame, label: str) -> dict:
    seg = bt.loc[C.OOS_START:C.OOS_END]
    net = seg["strategy_return_gross"] - seg["turnover"] * (C.ADOPTION_RULE["cost_bp"] / 10000.0)
    m = X.perf_metrics(net, seg["turnover"], label)
    m["calmar_net"] = m["calmar"]
    return m, seg, net


def compute_candidate_metrics(returns: pd.DataFrame, target_w: pd.DataFrame) -> tuple[dict, list[dict]]:
    """34번과 동일하게 참조값 + 후보별 실측치를 1회만 계산한다 (마진과 무관)."""
    risk_r = returns[C.RISK_TICKER]

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
    turnover_sym03 = refs[0.3]["avg_turnover_pct"]

    reference = {
        "calmar_best_sym": calmar_best_sym,
        "mdd_ref": mdd_ref,
        "tail_ref": tail_ref,
        "turnover_sym03": turnover_sym03,
    }

    candidate_rows = []
    for name, lu, ld in TIME_VARYING_CANDIDATES:
        if name == "dynamic_v1":
            sv = dyn.build_state_variables(returns, target_w)
            lam_t, _ = dyn.assign_lambda(sv)
            lam_t = lam_t.fillna(C.E30_RULE_V1["lambda_base"])
            bt = X.run_lambda_backtest(returns, target_w, np.nan, np.nan, lambda_series=lam_t)
        elif name == "dynamic_v1_macro":
            sv_macro = dyn_macro.build_state_variables_macro(returns, target_w)
            lam_macro, cond_macro, reason_macro = dyn_macro.assign_lambda_macro(sv_macro)
            lam_macro = lam_macro.fillna(C.E30_RULE_V1["lambda_base"])
            bt = X.run_lambda_backtest(returns, target_w, np.nan, np.nan, lambda_series=lam_macro)
        else:
            bt = X.run_lambda_backtest(returns, target_w, lu, ld)

        m, seg, net = oos_net_metrics(bt, name)
        tm = X.tail_month_defense(net, risk_r.loc[seg.index])

        candidate_rows.append({
            "strategy": name,
            "calmar_net": m["calmar_net"],
            "mdd_pct": m["mdd_pct"],
            "tail_avg_pct": tm["strategy_avg_pct"],
            "avg_turnover_pct": m["avg_turnover_pct"],
        })

    return reference, candidate_rows


def judge(candidate: dict, reference: dict, margin: dict) -> bool:
    to_cap = reference["turnover_sym03"] * margin["turnover_cap_mult"]
    c1 = candidate["calmar_net"] >= margin["calmar_ratio_min"] * reference["calmar_best_sym"]
    c2 = candidate["mdd_pct"] >= reference["mdd_ref"] - margin["mdd_worsen_max_pp"]
    c3 = candidate["tail_avg_pct"] >= reference["tail_ref"] - margin["tail_worsen_max_pp"]
    c4 = candidate["avg_turnover_pct"] <= to_cap
    return c1 and c2 and c3 and c4


def main() -> None:
    print("=" * 80)
    print("45_adoption_margin_sensitivity.py 실행 시작")
    print("=" * 80)

    print("[1] 데이터 로드 및 후보별 실측치 계산 (1회만 — 마진과 무관)")
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()
    reference, candidate_rows = compute_candidate_metrics(returns, target_w)
    print(f"    참조값: {reference}")
    for row in candidate_rows:
        print(f"    {row}")

    print("[2] Baseline 마진으로 판정")
    for row in candidate_rows:
        row["non_inferior_baseline"] = judge(row, reference, BASELINE_MARGIN)

    print("[3] 마진 그리드 스캔")
    detail_rows = []
    for margin_name, grid in MARGIN_GRID.items():
        for value in grid:
            margin = dict(BASELINE_MARGIN)
            margin[margin_name] = value
            for cand in candidate_rows:
                passed = judge(cand, reference, margin)
                detail_rows.append({
                    "margin_name": margin_name,
                    "margin_value": value,
                    "is_baseline": np.isclose(value, BASELINE_MARGIN[margin_name]),
                    "strategy": cand["strategy"],
                    "non_inferior": passed,
                })

    detail_df = pd.DataFrame(detail_rows)

    print("[4] Breaking point 계산 (dynamic_v1이 탈락하는 최초 강화 지점)")
    breaking_rows = []
    # 강화 방향 정의: calmar_ratio_min은 클수록 엄격, mdd/tail_worsen은 작을수록 엄격,
    # turnover_cap_mult는 작을수록 엄격
    STRICTER_DIRECTION = {
        "calmar_ratio_min": "increasing",
        "mdd_worsen_max_pp": "decreasing",
        "tail_worsen_max_pp": "decreasing",
        "turnover_cap_mult": "decreasing",
    }
    for margin_name, grid in MARGIN_GRID.items():
        direction = STRICTER_DIRECTION[margin_name]
        ordered = sorted(grid) if direction == "increasing" else sorted(grid, reverse=True)
        for strategy in [c["strategy"] for c in candidate_rows]:
            sub = detail_df[(detail_df["margin_name"] == margin_name) & (detail_df["strategy"] == strategy)]
            breaking_value = None
            for value in ordered:
                row = sub[np.isclose(sub["margin_value"], value)]
                if row.empty:
                    continue
                if not row.iloc[0]["non_inferior"]:
                    breaking_value = value
                    break
            breaking_rows.append({
                "margin_name": margin_name,
                "strategy": strategy,
                "baseline_value": BASELINE_MARGIN[margin_name],
                "stricter_direction": direction,
                "first_failing_value": breaking_value,
                "still_passes_at_grid_extreme": breaking_value is None,
            })

    breaking_df = pd.DataFrame(breaking_rows)

    print("[5] 저장")
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    detail_df.to_csv(OUTPUT_DETAIL, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_DETAIL}")
    breaking_df.to_csv(OUTPUT_BREAKING, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_BREAKING}")

    print("[6] 노트 생성")
    lines = []
    lines.append("# Adoption Decision 마진 민감도 분석 노트")
    lines.append("")
    lines.append(
        "34_adoption_decision.py의 4개 마진(calmar_ratio_min=0.90, mdd_worsen_max_pp=2.0, "
        "tail_worsen_max_pp=0.3, turnover_cap_mult=1.5)은 판정 기준으로만 문서화되어 있고 "
        "산출식은 없다. 본 분석은 각 마진을 baseline보다 엄격한 방향으로 강화했을 때, "
        "각 후보(특히 dynamic_v1)가 몇 단계까지 non-inferior 판정을 유지하는지 확인한다."
    )
    lines.append("")
    lines.append("## Breaking point 요약")
    lines.append("")
    lines.append("| 마진 | 후보 | baseline | 강화 방향 | 최초 탈락 지점 | grid 끝까지 통과 |")
    lines.append("|---|---|---:|---|---|---|")
    for _, row in breaking_df.iterrows():
        fail_val = row["first_failing_value"] if row["first_failing_value"] is not None else "—"
        lines.append(
            f"| {row['margin_name']} | {row['strategy']} | {row['baseline_value']} | "
            f"{row['stricter_direction']} | {fail_val} | {row['still_passes_at_grid_extreme']} |"
        )
    lines.append("")
    lines.append("## 해석 (초안)")
    lines.append("")
    lines.append(
        "[TODO] dynamic_v1이 grid 끝까지(가장 엄격한 값에서도) 통과한다면, adoption 마진을 "
        "다소 엄격하게 잡았어도 채택 결론이 바뀌지 않는다는 근거가 된다. 반대로 baseline "
        "근처에서 바로 탈락한다면, 그 마진이 결론을 좌우하는 취약한 지점이므로 보고서에서 "
        "'이 마진 설정에 결론이 의존적'이라고 정직하게 밝혀야 한다."
    )
    lines.append("")

    Path(OUTPUT_NOTE).parent.mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_NOTE).write_text("\n".join(lines), encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[dynamic_v1 breaking points]")
    print(breaking_df[breaking_df["strategy"] == "dynamic_v1"].to_string(index=False))

    print("=" * 80)
    print("45_adoption_margin_sensitivity.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
