# -*- coding: utf-8 -*-
"""
43_e30_threshold_sensitivity.py — E30 조건부 λ 임계값 민감도 분석

배경
----
30_dynamic_lambda_rule_v1.py의 임계값(volatility_z_high=1.0, drawdown_low=-0.10,
relief_persist_months=3, volatility_z_calm=0.0, momentum_z_positive=0.0,
macro_risk_high=2)은 HSI_RA_비대칭람다_상세수행문서_v2 §1.6/§3.7에 "IS에서만
threshold를 결정한다"는 절차 원칙만 기록되어 있을 뿐, 그 값 자체를 데이터로부터
산출한 계산식은 문서화되어 있지 않다. 즉 이 값들은 관행적 라운드넘버(1 표준편차,
0 기준선, 10% 낙폭, 3개월)로 사전등록된 것이며, IS 데이터 분포에 맞춰 최적화된
값이 아니다.

목적
----
이 값들을 데이터로부터 "최적화"하지 않았더라도, 그 값 근처에서 성과가 급격히
무너지지 않는지(안정 구간, plateau)를 확인하여 "임의로 골랐지만 결과가 그 값에
민감하게 좌우되지는 않는다"는 방어 근거를 만든다. 이는 사후 파라미터 튜닝이
아니라, 이미 사전등록된 값 주변의 안정성만 사후에 진단하는 것이므로
데이터 누수(leakage)에 해당하지 않는다.

방법
----
config.E30_RULE_V1의 6개 임계값을 각각 하나씩 변화시키며(다른 값은 baseline
고정) dynamic_v1 백테스트를 재실행하고, FULL/IS/OOS 구간의 CAGR·MDD·Calmar·
평균 Turnover를 기록한다. baseline 대비 각 지표의 변화 폭이 특정 허용범위
(CAGR ±1.5%p, MDD ±2.0%p, Calmar ±0.15) 안에 머무는 "안정 구간"의 폭을
계산하여 요약한다.

출력
----
- output/tables/main_final_e30_threshold_sensitivity_detail.csv
- output/tables/main_final_e30_threshold_sensitivity_summary.csv
- output/figures/main_final_e30_threshold_sensitivity_{param}.png (6개)
- docs/main_final_e30_threshold_sensitivity_note.md
"""

import sys
import copy
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config as C
import common as X

# ------------------------------------------------------------
# 30번 스크립트를 모듈로 로드하여 build_state_variables / assign_lambda 재사용
# (파일명이 숫자로 시작해 일반 import 불가 → importlib으로 경로 지정 로드)
# ------------------------------------------------------------
spec = importlib.util.spec_from_file_location(
    "e30_rule_v1", HERE / "30_dynamic_lambda_rule_v1.py"
)
E30 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E30)

BASELINE = copy.deepcopy(C.E30_RULE_V1)

# ------------------------------------------------------------
# 파라미터별 탐색 범위 (baseline을 중심으로 대칭적으로, 문서의 "관행적 라운드넘버"
# 성격에 맞춰 상식적인 폭으로 설정 — 이 범위 자체도 사전에 고정하고 결과를 본 뒤
# 넓히거나 좁히지 않는다)
# ------------------------------------------------------------
SENSITIVITY_GRID = {
    "volatility_z_high":   [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
    "drawdown_low":        [-0.05, -0.075, -0.10, -0.125, -0.15, -0.20],
    "relief_persist_months": [1, 2, 3, 4, 5, 6],
    "volatility_z_calm":   [-0.5, -0.25, 0.0, 0.25, 0.5],
    "momentum_z_positive": [-0.5, -0.25, 0.0, 0.25, 0.5],
    "macro_risk_high":     [1, 2, 3],
}

# 안정 구간 판정 허용폭 (사전 고정)
TOLERANCE = {
    "cagr_pct": 1.5,     # %p
    "mdd_pct": 2.0,       # %p
    "calmar": 0.15,       # ratio
}

PERIODS = {
    "FULL": (None, None),
    "IS": (C.IS_START, C.IS_END),
    "OOS": (C.OOS_START, C.OOS_END),
}

OUTPUT_DETAIL = C.TABLE_DIR / f"{C.FINAL_PREFIX}e30_threshold_sensitivity_detail.csv"
OUTPUT_SUMMARY = C.TABLE_DIR / f"{C.FINAL_PREFIX}e30_threshold_sensitivity_summary.csv"
OUTPUT_NOTE = C.REPORT_DIR.parent / "docs" / f"{C.FINAL_PREFIX}e30_threshold_sensitivity_note.md"


def run_one(rule: dict, returns: pd.DataFrame, target_w: pd.DataFrame) -> dict:
    """주어진 rule(dict)로 dynamic λ를 계산하고 FULL/IS/OOS 성과를 반환한다."""
    # E30 모듈의 R은 C.E30_RULE_V1을 참조하므로, dict를 직접 갱신해야 반영된다.
    C.E30_RULE_V1.clear()
    C.E30_RULE_V1.update(rule)

    sv = E30.build_state_variables(returns, target_w)
    lam_t, cond_label = E30.assign_lambda(sv)
    lam_t = lam_t.fillna(rule["lambda_base"])

    bt = X.run_lambda_backtest(
        returns, target_w,
        lambda_up=np.nan, lambda_down=np.nan,
        lambda_series=lam_t,
    )

    result = {}
    for label, (start, end) in PERIODS.items():
        if start is None:
            ret = bt["strategy_return_gross"]
            tno = bt["turnover"]
        else:
            mask = (bt.index >= pd.Timestamp(start)) & (bt.index <= pd.Timestamp(end))
            ret = bt["strategy_return_gross"][mask]
            tno = bt["turnover"][mask]
        m = X.perf_metrics(ret, tno, f"dynamic_v1_{label}")
        result[f"{label}_cagr_pct"] = m["cagr_pct"]
        result[f"{label}_mdd_pct"] = m["mdd_pct"]
        result[f"{label}_calmar"] = m["calmar"]
        result[f"{label}_avg_turnover_pct"] = m["avg_turnover_pct"]

    result["condition_dist"] = cond_label.value_counts().to_dict()
    return result


def main() -> None:
    print("=" * 80)
    print("43_e30_threshold_sensitivity.py 실행 시작")
    print("=" * 80)

    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()

    print("[1] Baseline(v1) 성과 계산")
    baseline_result = run_one(copy.deepcopy(BASELINE), returns, target_w)
    print(f"    FULL CAGR={baseline_result['FULL_cagr_pct']:.3f}%  "
          f"MDD={baseline_result['FULL_mdd_pct']:.3f}%  "
          f"Calmar={baseline_result['FULL_calmar']:.3f}")

    detail_rows = []
    for value in [BASELINE["volatility_z_high"]]:
        pass  # baseline은 아래 루프에서 각 파라미터별로 함께 기록됨

    print("[2] 파라미터별 민감도 스캔")
    for param, grid in SENSITIVITY_GRID.items():
        print(f"    - {param}: {grid}")
        for value in grid:
            rule = copy.deepcopy(BASELINE)
            rule[param] = value
            res = run_one(rule, returns, target_w)
            row = {"param": param, "value": value,
                   "is_baseline": np.isclose(value, BASELINE[param]) if isinstance(value, float)
                                  else (value == BASELINE[param])}
            row.update({k: v for k, v in res.items() if k != "condition_dist"})
            detail_rows.append(row)

    # 마지막에 원상복구 (다른 스크립트에 영향 주지 않도록)
    C.E30_RULE_V1.clear()
    C.E30_RULE_V1.update(BASELINE)

    detail_df = pd.DataFrame(detail_rows)

    print("[3] 안정 구간(plateau) 계산")
    summary_rows = []
    for param, grid in SENSITIVITY_GRID.items():
        sub = detail_df[detail_df["param"] == param].sort_values("value")
        base_row = sub[sub["is_baseline"]]
        if base_row.empty:
            continue
        base = base_row.iloc[0]

        stable_values = []
        for _, r in sub.iterrows():
            ok = (
                abs(r["FULL_cagr_pct"] - base["FULL_cagr_pct"]) <= TOLERANCE["cagr_pct"]
                and abs(r["FULL_mdd_pct"] - base["FULL_mdd_pct"]) <= TOLERANCE["mdd_pct"]
                and abs(r["FULL_calmar"] - base["FULL_calmar"]) <= TOLERANCE["calmar"]
            )
            if ok:
                stable_values.append(r["value"])

        summary_rows.append({
            "param": param,
            "baseline_value": BASELINE[param],
            "grid_min": min(grid),
            "grid_max": max(grid),
            "stable_min": min(stable_values) if stable_values else np.nan,
            "stable_max": max(stable_values) if stable_values else np.nan,
            "n_stable_of_total": f"{len(stable_values)}/{len(grid)}",
            "full_grid_stable": len(stable_values) == len(grid),
        })

    summary_df = pd.DataFrame(summary_rows)

    print("[4] 저장")
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    detail_df.to_csv(OUTPUT_DETAIL, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_DETAIL}")

    summary_df.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_SUMMARY}")

    print("[5] 파라미터별 그림 생성")
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for name in ["Malgun Gothic", "NanumGothic", "AppleGothic"]:
        try:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False
            break
        except Exception:
            continue

    for param in SENSITIVITY_GRID:
        sub = detail_df[detail_df["param"] == param].sort_values("value")
        fig, axes = plt.subplots(1, 3, figsize=(13, 4))
        for ax, metric, ylabel in zip(
            axes,
            ["FULL_cagr_pct", "FULL_mdd_pct", "FULL_calmar"],
            ["CAGR (%)", "MDD (%)", "Calmar"],
        ):
            ax.plot(sub["value"], sub[metric], marker="o")
            base_val = BASELINE[param]
            ax.axvline(base_val, color="red", linestyle="--", alpha=0.6, label=f"baseline={base_val}")
            ax.set_xlabel(param)
            ax.set_ylabel(ylabel)
            ax.legend(fontsize=8)
        fig.suptitle(f"E30 임계값 민감도 — {param} (FULL 구간)")
        fig.tight_layout()
        fig_path = C.FIGURE_DIR / f"{C.FINAL_PREFIX}e30_threshold_sensitivity_{param}.png"
        fig.savefig(fig_path, dpi=150)
        plt.close(fig)
        print(f"    저장: {fig_path}")

    print("[6] 노트 생성")
    lines = []
    lines.append("# E30 조건부 λ 임계값 민감도 분석 노트")
    lines.append("")
    lines.append(
        "config.E30_RULE_V1의 6개 임계값은 IS 데이터로부터 산출한 계산식이 아니라 "
        "사전등록된 관행적 라운드넘버이다. 본 분석은 각 임계값을 baseline 주변에서 "
        "변화시켰을 때 FULL 구간 CAGR/MDD/Calmar가 급격히 무너지지 않는지(안정 구간) "
        "확인하여, 특정 값 선택이 결과를 좌우하는 취약한 지점(fragile point)이 아님을 "
        "보조적으로 확인한다."
    )
    lines.append("")
    lines.append("## 파라미터별 안정 구간 요약")
    lines.append("")
    lines.append("| 파라미터 | baseline | 탐색범위 | 안정범위 | 안정 비율 | 전 구간 안정 |")
    lines.append("|---|---:|---|---|---|---|")
    for _, row in summary_df.iterrows():
        lines.append(
            f"| {row['param']} | {row['baseline_value']} | "
            f"[{row['grid_min']}, {row['grid_max']}] | "
            f"[{row['stable_min']}, {row['stable_max']}] | "
            f"{row['n_stable_of_total']} | {row['full_grid_stable']} |"
        )
    lines.append("")
    lines.append(
        f"(안정 판정 기준: baseline 대비 CAGR ±{TOLERANCE['cagr_pct']}%p, "
        f"MDD ±{TOLERANCE['mdd_pct']}%p, Calmar ±{TOLERANCE['calmar']} 이내)"
    )
    lines.append("")
    lines.append("## 해석 (초안 — 실제 수치 확인 후 다듬을 것)")
    lines.append("")
    lines.append(
        "[TODO] 전 구간(full_grid_stable=True)에서 안정적인 파라미터는, 그 값을 정확히 "
        "'최적화'하지 않았어도 성과가 임계값 선택에 취약하지 않다는 근거로 제시할 수 있다."
    )
    lines.append("")
    lines.append(
        "[TODO] 안정 구간이 grid 전체를 덮지 못하는 파라미터가 있다면, 해당 값 근처에서 "
        "결과가 민감하다는 뜻이므로 보고서에서 그 파라미터에 대해서는 '관행값이지만 결과가 "
        "여기에 다소 의존적이다'라고 정직하게 한계로 명시해야 한다."
    )
    lines.append("")

    Path(OUTPUT_NOTE).parent.mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_NOTE).write_text("\n".join(lines), encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("[요약]")
    print(summary_df.to_string(index=False))

    print("=" * 80)
    print("43_e30_threshold_sensitivity.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
