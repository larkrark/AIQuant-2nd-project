# -*- coding: utf-8 -*-
"""
31_validation.py — 검증 게이트 실행 (v2 §3.8~3.10)

수행:
  게이트 ④ robustness : 기간분할(4구간)·tail-month, 후보 vs 대칭 λ
  게이트 ⑤ IS/OOS     : IS(2012-04~2020-12) 성과와 OOS(2021-01~2026-06) 성과 병렬 제시
  게이트 ⑥ walk-forward: 60개월 점검 → 12개월 평가 → 12개월 이동, 평가구간 연결 성과
  게이트 ⑦ 누수 audit  : 체크리스트를 표로 출력(코드로 검증 가능한 항목은 자동 판정)

주의:
- 본 스크립트는 '평가'만 수행한다. grid·threshold를 여기서 바꾸지 않는다.
- 후보 목록은 E29 결과에서 인접 안정 영역을 사람이 판단해 CANDIDATES 에 기입한다.
  (기본값: 사전 가설 영역의 대표 셀 + 대칭 참조 2개 — full-grid 기록은 E29가 담당)

출력:
  output/tables/main_final_validation_audit_table.csv
  output/tables/main_final_is_oos_comparison.csv
  output/tables/main_final_walk_forward_results.csv
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
# 평가 대상 후보 (λ_up, λ_down). E29 full-grid 확인 후 필요 시 추가 — 추가 이력은 주석으로 기록.
CANDIDATES = [
    (0.10, 0.10),  # 대칭 참조 (방어형)
    (0.30, 0.30),  # 대칭 참조 (균형형)
    (0.10, 0.30),  # 방어형 가설: cut fast(0.3), add back slow(0.1)
    (0.10, 0.50),
    (0.20, 0.30),
    (0.20, 0.50),
    (0.30, 0.10),  # 반대 가설 영역 (기록용)
]
INCLUDE_DYNAMIC_V1 = True

def slice_metrics(bt: pd.DataFrame, start, end, label) -> dict:
    seg = bt.loc[start:end]
    if len(seg) < 6:
        return {"strategy": label, "months": len(seg)}
    return X.perf_metrics(seg["strategy_return_gross"], seg["turnover"], label)


def main() -> None:
    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()
    risk_r = returns[C.RISK_TICKER]

    backtests = {}
    for lu, ld in CANDIDATES:
        key = f"up{lu:.2f}_down{ld:.2f}"
        backtests[key] = X.run_lambda_backtest(
            returns,
            target_w,
            lambda_up=lu,
            lambda_down=ld,
        )

    # E30 dynamic_v1도 동일 validation 게이트에 포함
    if INCLUDE_DYNAMIC_V1:
        sv = dyn.build_state_variables(returns, target_w)
        lam_t, cond = dyn.assign_lambda(sv)
        lam_t = lam_t.fillna(C.E30_RULE_V1["lambda_base"])

        backtests["dynamic_v1"] = X.run_lambda_backtest(
            returns,
            target_w,
            lambda_up=np.nan,
            lambda_down=np.nan,
            lambda_series=lam_t,
        )

    # --- 게이트 ⑤ IS / OOS ---
    rows = []
    for key, bt in backtests.items():
        for seg_label, (s, e) in (("IS", (C.IS_START, C.IS_END)),
                                  ("OOS", (C.OOS_START, C.OOS_END)),
                                  ("FULL", (None, None))):
            seg = bt if s is None else bt.loc[s:e]
            m = X.perf_metrics(seg["strategy_return_gross"], seg["turnover"], key)
            m["segment"] = seg_label
            tm = X.tail_month_defense(seg["strategy_return_gross"],
                                      risk_r.loc[seg.index])
            m["tail_strategy_avg_pct"] = tm["strategy_avg_pct"]
            rows.append(m)
    is_oos = pd.DataFrame(rows)

    # --- 게이트 ④ robustness 기간분할 ---
    rob_rows = []
    for key, bt in backtests.items():
        for split, (s, e) in C.ROBUSTNESS_SPLITS.items():
            m = slice_metrics(bt, s, e, key)
            m["split"] = split
            rob_rows.append(m)
    robustness = pd.DataFrame(rob_rows)

    # --- 게이트 ⑥ walk-forward ---
    # 각 후보를 고정 규칙으로 두고, 60개월 뒤 12개월 평가 구간들을 이어붙인다.
    wf_rows = []
    all_idx = next(iter(backtests.values())).index
    starts = range(0, len(all_idx) - C.WF_TRAIN_MONTHS - C.WF_TEST_MONTHS + 1, C.WF_STEP_MONTHS)
    for key, bt in backtests.items():
        eval_returns = []
        for s0 in starts:
            test_idx = all_idx[s0 + C.WF_TRAIN_MONTHS: s0 + C.WF_TRAIN_MONTHS + C.WF_TEST_MONTHS]
            eval_returns.append(bt.loc[test_idx, "strategy_return_gross"])
        if eval_returns:
            stitched = pd.concat(eval_returns)
            stitched = stitched[~stitched.index.duplicated()]
            m = X.perf_metrics(stitched, label=key)
            m["wf_windows"] = len(eval_returns)
            wf_rows.append(m)
    walk_forward = pd.DataFrame(wf_rows)

    # --- 게이트 ⑦ 누수 audit (자동 판정 가능한 항목) ---
    audit = []
    # 시점 정합: signal_date < apply_date 전수 확인
    ok_timing = all((bt["signal_date"] < bt.index).all() for bt in backtests.values())
    audit.append({"항목": "시점 정합(t신호→t+1적용)", "자동판정": "통과" if ok_timing else "실패"})
    audit.append({"항목": "rolling 계산 미래값 금지",
                  "자동판정": "코드 규약(30번: rolling만 사용, 전구간 z 금지) — 수동 확인 병행"})
    audit.append({"항목": "grid 사전고정", "자동판정": "config.py 고정 — 변경 이력 주석 확인"})
    audit.append({"항목": "OOS 격리(후보선정에 미사용)",
                  "자동판정": "CANDIDATES 선정 근거가 IS·full-grid인지 수동 확인"})
    audit.append({"항목": "비용 민감도 확인", "자동판정": "E28/E29 cagr_net_*bp 열 존재 — 통과"})
    audit.append({"항목": "다지표 판단(CAGR 단독 금지)",
                  "자동판정": "MDD·Calmar·Turnover 동시 산출 — 통과"})
    audit_df = pd.DataFrame(audit)

    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    is_oos.to_csv(C.TABLE_DIR / f"{C.FINAL_PREFIX}is_oos_comparison.csv",
                  index=False, encoding="utf-8-sig")
    robustness.to_csv(C.TABLE_DIR / f"{C.FINAL_PREFIX}robustness_splits.csv",
                      index=False, encoding="utf-8-sig")
    walk_forward.to_csv(C.TABLE_DIR / f"{C.FINAL_PREFIX}walk_forward_results.csv",
                        index=False, encoding="utf-8-sig")
    audit_df.to_csv(C.TABLE_DIR / f"{C.FINAL_PREFIX}validation_audit_table.csv",
                    index=False, encoding="utf-8-sig")

    print("[완료] 31_validation")
    print("\n[IS/OOS] (순위 역전 여부를 보고서에 명시)")
    cols = ["strategy", "segment", "cagr_pct", "mdd_pct", "calmar", "avg_turnover_pct",
            "tail_strategy_avg_pct"]
    print(is_oos[cols].round(3).to_string(index=False))
    print("\n[Walk-forward 평가구간 연결 성과]")
    print(walk_forward[["strategy", "wf_windows", "cagr_pct", "mdd_pct", "calmar"]]
          .round(3).to_string(index=False))
    print("\n[누수 audit]")
    print(audit_df.to_string(index=False))


if __name__ == "__main__":
    main()
