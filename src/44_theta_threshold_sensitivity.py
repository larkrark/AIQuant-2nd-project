from pathlib import Path
import copy
import importlib.util

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import final_project_config as cfg


"""
44_theta_threshold_sensitivity.py

배경
----
04_build_hsi_state5_baseline.py의 HSI 5상태 분류 임계값
(THETA_COMMON=0.15, ACCIDENT_EXTRA=0.20, DIRECTION_MARGIN=0.05,
CONFLICT_DIRECTION_BAND=0.20)은 "θ 기준값"으로만 문서화되어 있고, 이 값을
데이터로부터 산출한 계산식은 없다. E30 임계값(43번 스크립트)과 성격이 같은
관행적 사전등록값이다.

목적
----
θ 및 관련 3개 임계값을 baseline 주변에서 흔들어, HSI 5상태 분류에서 파생되는
"HSI baseline"(λ=1, 즉시 반영) 성과가 특정 값 선택에 취약하지 않은지 확인한다.
이는 상태분류 규칙 자체를 사후에 최적화하는 것이 아니라, 이미 쓰고 있는 값
근처의 안정성만 진단하는 것이므로 데이터 누수에 해당하지 않는다.

방법
----
04번 모듈을 그대로 재사용(importlib)하여 classify_hsi_state 로직을 유지한 채
모듈 전역값(THETA_COMMON 등)만 바꿔가며 상태표를 재생성한다. 상태별 목표비중은
cfg.FINAL_BASELINE_ALLOCATION_RULES를 그대로 사용해 λ=1(즉시 반영) 백테스트를
수행한다 — 이는 λ 스무딩 효과를 제거하고 "상태분류 임계값 자체"의 순수한 영향만
보기 위함이다.

출력
----
- output/tables/main_final_theta_threshold_sensitivity_detail.csv
- output/tables/main_final_theta_threshold_sensitivity_summary.csv
- output/figures/main_final_theta_threshold_sensitivity_{param}.png
- docs/main_final_theta_threshold_sensitivity_note.md
"""


HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location(
    "state5_baseline", HERE / "04_build_hsi_state5_baseline.py"
)
S04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S04)

BASELINE = {
    "THETA_COMMON": S04.THETA_COMMON,
    "ACCIDENT_EXTRA": S04.ACCIDENT_EXTRA,
    "DIRECTION_MARGIN": S04.DIRECTION_MARGIN,
    "CONFLICT_DIRECTION_BAND": S04.CONFLICT_DIRECTION_BAND,
}

SENSITIVITY_GRID = {
    "THETA_COMMON":            [0.10, 0.125, 0.15, 0.175, 0.20],
    "ACCIDENT_EXTRA":          [0.10, 0.15, 0.20, 0.25, 0.30],
    "DIRECTION_MARGIN":        [0.00, 0.025, 0.05, 0.075, 0.10],
    "CONFLICT_DIRECTION_BAND": [0.10, 0.15, 0.20, 0.25, 0.30],
}

EXTREME_OVERRIDE_TESTS = {
    "THETA_COMMON": [0.00, 0.90],
    "ACCIDENT_EXTRA": [0.00, 0.90],
    "DIRECTION_MARGIN": [0.00, 0.50],
    "CONFLICT_DIRECTION_BAND": [0.00, 1.00],
}

TOLERANCE = {
    "cagr_pct": 1.5,
    "mdd_pct": 2.0,
    "calmar": 0.15,
}

IS_START, IS_END = "2012-04-30", "2020-12-31"
OOS_START, OOS_END = "2021-01-31", "2026-06-30"

OUTPUT_DETAIL = cfg.TABLE_DIR / "main_final_theta_threshold_sensitivity_detail.csv"
OUTPUT_SUMMARY = cfg.TABLE_DIR / "main_final_theta_threshold_sensitivity_summary.csv"
OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_theta_threshold_sensitivity_note.md"


def load_inputs():
    monthly_long = S04.read_csv(S04.INPUT_MONTHLY_SIGNAL_LONG, "월말 HSI signal long")
    monthly_returns = S04.read_csv(S04.INPUT_MONTHLY_RETURNS, "월간 수익률 decimal")
    return monthly_long, monthly_returns


def perf_from_returns(port_ret: pd.Series) -> dict:
    r = port_ret.dropna()
    n = len(r)
    if n == 0:
        return {"cagr_pct": np.nan, "mdd_pct": np.nan, "calmar": np.nan}
    idx = (1 + r).cumprod()
    years = n / 12.0
    cagr = idx.iloc[-1] ** (1 / years) - 1
    dd = idx / idx.cummax() - 1
    mdd = dd.min()
    calmar = cagr / abs(mdd) if mdd < 0 else np.nan
    return {"cagr_pct": cagr * 100, "mdd_pct": mdd * 100, "calmar": calmar}


def run_state5_immediate_backtest(alignment: pd.DataFrame) -> pd.Series:
    """
    HSI 5상태를 λ=1(즉시 반영)로 바로 적용하는 baseline 백테스트.
    insufficient_data는 직전 실제비중을 유지한다.
    """
    ret_cols = {t: f"next_return_{t}" for t in cfg.TICKERS}
    missing = [c for c in ret_cols.values() if c not in alignment.columns]
    if missing:
        raise ValueError(f"정렬표에 다음 열이 없습니다: {missing}")

    df = alignment.dropna(subset=list(ret_cols.values())).copy()

    prev_w = None
    port_returns = []
    dates = []
    for _, row in df.iterrows():
        state = row["hsi_state"]
        if state == "insufficient_data" or state not in cfg.FINAL_BASELINE_ALLOCATION_RULES:
            if prev_w is None:
                continue
            w = prev_w
        else:
            rule = cfg.FINAL_BASELINE_ALLOCATION_RULES[state]
            w = np.array([rule[t] for t in cfg.TICKERS])

        r = np.array([row[ret_cols[t]] for t in cfg.TICKERS])
        port_returns.append(float(np.dot(w, r)))
        dates.append(row["return_year_month"])
        prev_w = w

    idx = pd.PeriodIndex(dates, freq="M").to_timestamp("M")
    return pd.Series(port_returns, index=idx).sort_index()


def run_one(param_overrides: dict, monthly_long: pd.DataFrame, monthly_returns: pd.DataFrame) -> dict:
    for key, val in BASELINE.items():
        setattr(S04, key, param_overrides.get(key, val))

    state_table = S04.build_state_table(monthly_long)
    alignment = S04.build_alignment_preview(state_table, monthly_returns)
    port_ret = run_state5_immediate_backtest(alignment)

    result = {}
    for label, start, end in [
        ("FULL", None, None),
        ("IS", IS_START, IS_END),
        ("OOS", OOS_START, OOS_END),
    ]:
        seg = port_ret if start is None else port_ret[(port_ret.index >= pd.Timestamp(start)) & (port_ret.index <= pd.Timestamp(end))]
        m = perf_from_returns(seg)
        result[f"{label}_cagr_pct"] = m["cagr_pct"]
        result[f"{label}_mdd_pct"] = m["mdd_pct"]
        result[f"{label}_calmar"] = m["calmar"]

    dist = state_table["hsi_state"].value_counts(normalize=True).to_dict()
    result["insufficient_data_ratio"] = dist.get("insufficient_data", 0.0)
    return result


def main() -> None:
    print("=" * 80)
    print("44_theta_threshold_sensitivity.py 실행 시작")
    print("=" * 80)

    cfg.ensure_final_directories()

    print("[1] 입력 로드")
    monthly_long, monthly_returns = load_inputs()

    print("[2] Baseline(θ=0.15 등) 성과 계산")
    base_result, base_state_s, base_weight_df, base_port_ret = run_one_debug(
        {},
        monthly_long,
        monthly_returns,
        base_state_s=None,
        base_weight_df=None,
        base_port_ret=None,
    )

    print(f"    FULL CAGR={base_result['FULL_cagr_pct']:.3f}%  "
          f"MDD={base_result['FULL_mdd_pct']:.3f}%  "
          f"Calmar={base_result['FULL_calmar']:.3f}")
    print(f"    Baseline 평가상태: {base_result['not_evaluable_reason']}")

    print("[3] 파라미터별 민감도 스캔")
    detail_rows = []

    for param, grid in SENSITIVITY_GRID.items():
        print(f"    - {param}: {grid}")
        for value in grid:
            res, state_s, weight_df, port_ret = run_one_debug(
                {param: value},
                monthly_long,
                monthly_returns,
                base_state_s=base_state_s,
                base_weight_df=base_weight_df,
                base_port_ret=base_port_ret,
            )

            row = {
                "param": param,
                "value": value,
                "is_baseline": np.isclose(value, BASELINE[param]),
            }
            row.update(res)
            detail_rows.append(row)

    detail_df = pd.DataFrame(detail_rows)

    print("[3-추가] 극단값 override 반영 여부 점검")
    extreme_rows = []

    for param, grid in EXTREME_OVERRIDE_TESTS.items():
        print(f"    - {param}: {grid}")
        for value in grid:
            res, state_s, weight_df, port_ret = run_one_debug(
                {param: value},
                monthly_long,
                monthly_returns,
                base_state_s=base_state_s,
                base_weight_df=base_weight_df,
                base_port_ret=base_port_ret,
            )

            row = {
                "param": param,
                "value": value,
                "test_type": "extreme_override_check",
            }
            row.update(res)
            extreme_rows.append(row)

    extreme_df = pd.DataFrame(extreme_rows)
    extreme_path = cfg.TABLE_DIR / "main_final_theta_threshold_extreme_override_check.csv"
    extreme_df.to_csv(extreme_path, index=False, encoding="utf-8-sig")
    print(f"    저장: {extreme_path}")

    # 원상복구
    for key, val in BASELINE.items():
        setattr(S04, key, val)


    detail_df = pd.DataFrame(detail_rows)

    print("[4] 안정 구간(plateau) 계산")
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

    print("[5] 저장")
    detail_df.to_csv(OUTPUT_DETAIL, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_DETAIL}")
    summary_df.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_SUMMARY}")

    print("[6] 그림 생성")
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
            ax.axvline(BASELINE[param], color="red", linestyle="--", alpha=0.6,
                       label=f"baseline={BASELINE[param]}")
            ax.set_xlabel(param)
            ax.set_ylabel(ylabel)
            ax.legend(fontsize=8)
        fig.suptitle(f"HSI 5상태 분류 임계값 민감도 — {param} (HSI baseline, λ=1, FULL)")
        fig.tight_layout()
        fig_path = cfg.FIGURE_DIR / f"main_final_theta_threshold_sensitivity_{param}.png"
        fig.savefig(fig_path, dpi=150)
        plt.close(fig)
        print(f"    저장: {fig_path}")

    print("[7] 노트 생성")
    lines = []
    lines.append("# HSI 5상태 분류 임계값(θ 등) 민감도 분석 노트")
    lines.append("")
    lines.append(
        "04_build_hsi_state5_baseline.py의 THETA_COMMON=0.15 등 4개 임계값은 데이터로부터 "
        "산출한 계산식이 아니라 사전에 정한 관행값이다. 본 분석은 HSI baseline(λ=1, 즉시 반영) "
        "성과가 이 값 근처에서 급격히 무너지지 않는지 확인한다."
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
        f"MDD ±{TOLERANCE['mdd_pct']}%p, Calmar ±{TOLERANCE['calmar']} 이내, HSI baseline λ=1 기준)"
    )
    lines.append("")
    lines.append("## 해석 (초안)")
    lines.append("")
    lines.append(
        "[TODO] 전 구간 안정(full_grid_stable=True)인 파라미터는 θ 등 임계값을 정확히 "
        "튜닝하지 않았어도 상태분류 결과가 취약하지 않다는 근거로 제시할 수 있다."
    )
    lines.append("")

    Path(OUTPUT_NOTE).write_text("\n".join(lines), encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[요약]")
    print(summary_df.to_string(index=False))

    print("=" * 80)
    print("44_theta_threshold_sensitivity.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
