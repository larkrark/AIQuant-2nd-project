# -*- coding: utf-8 -*-
"""
38c_hsi_shuffle_overfitting_check_final.py

HSI Shuffle Placebo Test (38b) 결과에 대해
"100회 단위로 셔플을 반복 실행해도 특정 배치에 결과가 과적합되지 않았는지"를
통계적으로 검증하고 시각화하는 후속 스크립트.

38b 산출물(placebo runs, actual metrics)을 입력으로 사용한다.

핵심 아이디어
------------
advantage_percentile은 사실상 "이항비율(proportion)" 추정이다.
    success_i = 1  (actual이 i번째 placebo보다 유리했던 경우)
    success_i = 0  (그렇지 않은 경우)
    advantage_percentile = mean(success_i) * 100

이 비율 추정이 특정 100개 배치에서만 우연히 높게 나온 "과적합"이 아니라,
모집단 성격의 안정적 추정치라는 것을 아래 3가지 검정으로 확인한다.

1. 배치 동질성 검정 (Chi-square homogeneity test)
   1000회를 100개씩 10개 배치로 나누고, 배치별 success 비율이
   통계적으로 동일한지(=배치마다 결과가 들쭉날쭉하지 않은지) 검정한다.

2. Split-half 검정 (2-표본 비율 z검정)
   앞 절반(1~500) vs 뒤 절반(501~1000)의 success 비율을 비교한다.
   두 절반이 유의하게 다르지 않으면 특정 시드 구간에 결과가 종속되지 않았다는 근거이다.

3. 누적 수렴 진단 (Convergence diagnostics)
   이항분포 이론 표준오차 SE = sqrt(p(1-p)/n)를 이용해 신뢰구간을 계산하고,
   표본이 늘어날수록(특히 n>=300 이후) 누적 추정치가 최종값(n=1000) 대비
   허용오차(기본 5%p) 이내로 수렴하는지 확인한다.

세 조건을 모두 만족하면 "overall_no_overfitting_evidence = True"로 판정한다.

주요 출력
---------
output/tables/main_final_38c_batch_homogeneity_test.csv
output/tables/main_final_38c_split_half_test.csv
output/tables/main_final_38c_convergence_diagnostics.csv
output/tables/main_final_38c_overfitting_verdict_summary.csv
output/figures/main_final_fig_38c_batch_percentile_stability.png
output/figures/main_final_fig_38c_convergence_band.png
output/figures/main_final_fig_38c_split_half_comparison.png
output/figures/main_final_fig_38c_overfitting_verdict_summary.png
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

import final_project_config as cfg


def configure_matplotlib_font() -> None:
    candidates = ["Malgun Gothic", "맑은 고딕", "NanumGothic", "Noto Sans CJK KR", "AppleGothic"]
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


# =============================================================================
# 0. 설정
# =============================================================================
PROJECT_DIR = getattr(cfg, "PROJECT_DIR", Path(__file__).resolve().parents[1])
TABLE_DIR = getattr(cfg, "TABLE_DIR", PROJECT_DIR / "output" / "tables")
FIGURE_DIR = getattr(cfg, "FIGURE_DIR", PROJECT_DIR / "output" / "figures")

INPUT_RUNS = TABLE_DIR / "flex_38b_hsi_shuffle_placebo_runs.csv"
INPUT_ACTUAL = TABLE_DIR / "main_final_38b_hsi_shuffle_actual_metrics.csv"

OUTPUT_BATCH = TABLE_DIR / "main_final_38c_batch_homogeneity_test.csv"
OUTPUT_SPLITHALF = TABLE_DIR / "main_final_38c_split_half_test.csv"
OUTPUT_CONVERGENCE = TABLE_DIR / "main_final_38c_convergence_diagnostics.csv"
OUTPUT_VERDICT = TABLE_DIR / "main_final_38c_overfitting_verdict_summary.csv"

PERIOD_TO_CHECK = "OOS"
BATCH_SIZE = 100          # "100 단위" 요청 반영
CONVERGENCE_STEP = 100
GAP_TOLERANCE_PCT_POINTS = 5.0   # 후반부 수렴 허용오차
MIN_N_FOR_GAP_CHECK = 300        # 이 시점 이후 gap만 판정에 사용
ALPHA = 0.05

# 지표명: (표시이름, 단위, 방향)  — 38b의 METRIC_INFO와 동일한 규칙
METRIC_INFO: Dict[str, Tuple[str, str, str]] = {
    "net10_cagr_pct": ("Net10bp CAGR", "%", "higher"),
    "net10_mdd_pct": ("Net10bp MDD", "%", "higher"),
    "net10_calmar": ("Net10bp Calmar", "ratio", "higher"),
    "net10_sharpe": ("Net10bp Sharpe", "ratio", "higher"),
    "net10_tail_strategy_avg_pct": ("Net10bp tail-month 평균수익", "%", "higher"),
    "net10_ann_vol_pct": ("Net10bp 연환산 변동성", "%", "lower"),
    "avg_annual_turnover_pct": ("평균 연환산 Turnover", "%", "lower"),
    "net10_win_rate_pct": ("Net10bp 월 승률", "%", "higher"),
}

# 그림에서 대표로 보여줄 핵심 4개 지표
HEADLINE_METRICS = ["net10_cagr_pct", "net10_mdd_pct", "net10_calmar", "net10_sharpe"]


# =============================================================================
# 1. 데이터 로딩
# =============================================================================
def ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} 파일이 없습니다: {path}. 먼저 38b 스크립트를 실행하세요.")


def load_inputs() -> Tuple[pd.DataFrame, pd.DataFrame]:
    require_file(INPUT_RUNS, "38b placebo runs")
    require_file(INPUT_ACTUAL, "38b actual metrics")
    runs = pd.read_csv(INPUT_RUNS)
    actual = pd.read_csv(INPUT_ACTUAL)
    return runs, actual


def compute_success_series(
    runs: pd.DataFrame, actual: pd.DataFrame, metric: str, period: str, direction: str
) -> pd.Series:
    """
    actual이 placebo보다 '유리'했는지를 나타내는 0/1 시리즈를 sim_id 순서대로 만든다.
    38b의 advantage_percentile 정의와 동일한 규칙을 사용한다.
    """
    run_rows = runs.loc[runs["period"].eq(period)].copy()
    run_rows = run_rows.dropna(subset=[metric, "sim_id"])
    run_rows["sim_id"] = run_rows["sim_id"].astype(int)
    run_rows = run_rows.sort_values("sim_id")

    actual_row = actual.loc[actual["period"].eq(period)].iloc[0]
    actual_value = float(actual_row[metric])

    vals = run_rows.set_index("sim_id")[metric].astype(float)
    if direction == "higher":
        success = (vals <= actual_value).astype(int)
    else:
        success = (vals >= actual_value).astype(int)
    return success.sort_index()


# =============================================================================
# 2. 통계 검정 함수 (핵심: 과적합 여부 증명)
# =============================================================================
def batch_homogeneity_test(success: pd.Series, batch_size: int = BATCH_SIZE) -> Tuple[pd.DataFrame, float, float]:
    """
    100개씩 배치로 나누어 배치 간 success 비율이 동일한지 카이제곱 동질성 검정을 수행한다.
    p_value가 크면(예: >0.05) '배치마다 결과가 유의하게 달라지지 않는다' = 과적합 근거 없음.
    """
    n_total = len(success)
    n_batches = n_total // batch_size
    used = success.iloc[: n_batches * batch_size]
    pooled_p = float(used.mean())

    rows: List[Dict[str, float]] = []
    for b in range(n_batches):
        chunk = used.iloc[b * batch_size:(b + 1) * batch_size]
        k = int(chunk.sum())
        n = len(chunk)
        rows.append({
            "batch": b + 1,
            "sim_range": f"{b * batch_size}-{(b + 1) * batch_size - 1}",
            "k_success": k,
            "n": n,
            "phat_pct": k / n * 100.0,
        })
    batch_df = pd.DataFrame(rows)
    batch_df["pooled_phat_pct"] = pooled_p * 100.0

    expected = batch_size * pooled_p
    var = batch_size * pooled_p * (1.0 - pooled_p)
    if var <= 0 or n_batches <= 1:
        chi2_stat, p_value = float("nan"), float("nan")
    else:
        chi2_stat = float(((batch_df["k_success"] - expected) ** 2 / var).sum())
        dof = n_batches - 1
        p_value = float(chi2.sf(chi2_stat, dof))
    return batch_df, chi2_stat, p_value


def split_half_test(success: pd.Series) -> Dict[str, float]:
    """
    앞 절반과 뒤 절반의 success 비율을 2-표본 비율 z검정으로 비교한다.
    """
    n = len(success)
    half = n // 2
    first = success.iloc[:half]
    second = success.iloc[half:2 * half]

    n1, n2 = len(first), len(second)
    p1, p2 = float(first.mean()), float(second.mean())
    pooled = (first.sum() + second.sum()) / (n1 + n2)

    if 0 < pooled < 1:
        se = float(np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2)))
        z = (p1 - p2) / se if se > 0 else float("nan")
        p_value = float(2 * (1 - norm.cdf(abs(z)))) if pd.notna(z) else float("nan")
    else:
        se, z, p_value = float("nan"), float("nan"), float("nan")

    return {
        "n1": n1, "n2": n2,
        "phat_first_half_pct": p1 * 100.0,
        "phat_second_half_pct": p2 * 100.0,
        "diff_pct_points": (p1 - p2) * 100.0,
        "z_stat": z,
        "p_value": p_value,
    }


def cumulative_convergence(success: pd.Series, step: int = CONVERGENCE_STEP) -> pd.DataFrame:
    """
    누적 표본 수를 늘려가며 이론적 이항 신뢰구간과 최종값 대비 gap을 계산한다.
    """
    n_total = len(success)
    checkpoints = list(range(step, n_total + 1, step))
    if checkpoints[-1] != n_total:
        checkpoints.append(n_total)

    final_p = float(success.mean())
    rows: List[Dict[str, float]] = []
    for k in checkpoints:
        sub = success.iloc[:k]
        p_hat = float(sub.mean())
        se = float(np.sqrt(p_hat * (1 - p_hat) / k)) if 0 < p_hat < 1 else 0.0
        ci_low = max(0.0, p_hat - 1.96 * se)
        ci_high = min(1.0, p_hat + 1.96 * se)
        rows.append({
            "checkpoint": k,
            "phat_pct": p_hat * 100.0,
            "se_pct": se * 100.0,
            "ci_low_pct": ci_low * 100.0,
            "ci_high_pct": ci_high * 100.0,
            "gap_to_final_pct_points": (p_hat - final_p) * 100.0,
        })
    df = pd.DataFrame(rows)
    df["final_phat_pct"] = final_p * 100.0
    return df


def overfitting_verdict(
    chi2_p: float, splithalf_p: float, convergence_df: pd.DataFrame,
    gap_tolerance: float = GAP_TOLERANCE_PCT_POINTS,
    min_n: int = MIN_N_FOR_GAP_CHECK,
    alpha: float = ALPHA,
) -> Dict[str, float]:
    late = convergence_df.loc[convergence_df["checkpoint"] >= min_n]
    max_late_gap = float(late["gap_to_final_pct_points"].abs().max()) if not late.empty else float("nan")

    batch_pass = bool(pd.notna(chi2_p) and chi2_p > alpha)
    splithalf_pass = bool(pd.notna(splithalf_p) and splithalf_p > alpha)
    convergence_pass = bool(pd.notna(max_late_gap) and max_late_gap <= gap_tolerance)
    overall_pass = batch_pass and splithalf_pass and convergence_pass

    return {
        "chi2_p_value": chi2_p,
        "batch_homogeneity_pass": batch_pass,
        "split_half_p_value": splithalf_p,
        "split_half_pass": splithalf_pass,
        "max_late_convergence_gap_pct_points": max_late_gap,
        "convergence_pass": convergence_pass,
        "overall_no_overfitting_evidence": overall_pass,
    }


def run_overfitting_checks(runs: pd.DataFrame, actual: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    batch_all: List[pd.DataFrame] = []
    splithalf_all: List[Dict[str, float]] = []
    convergence_all: List[pd.DataFrame] = []
    verdict_all: List[Dict[str, float]] = []

    for metric, (display_name, unit, direction) in METRIC_INFO.items():
        success = compute_success_series(runs, actual, metric, PERIOD_TO_CHECK, direction)
        if success.empty:
            continue

        batch_df, chi2_stat, chi2_p = batch_homogeneity_test(success)
        batch_df["metric"] = metric
        batch_df["display_name"] = display_name
        batch_df["chi2_stat"] = chi2_stat
        batch_df["chi2_p_value"] = chi2_p
        batch_all.append(batch_df)

        sh = split_half_test(success)
        sh.update({"metric": metric, "display_name": display_name})
        splithalf_all.append(sh)

        conv_df = cumulative_convergence(success)
        conv_df["metric"] = metric
        conv_df["display_name"] = display_name
        convergence_all.append(conv_df)

        verdict = overfitting_verdict(chi2_p, sh["p_value"], conv_df)
        verdict.update({"metric": metric, "display_name": display_name, "period": PERIOD_TO_CHECK})
        verdict_all.append(verdict)

    batch_result = pd.concat(batch_all, ignore_index=True)
    splithalf_result = pd.DataFrame(splithalf_all)
    convergence_result = pd.concat(convergence_all, ignore_index=True)
    verdict_result = pd.DataFrame(verdict_all)
    return batch_result, splithalf_result, convergence_result, verdict_result

# =============================================================================
# 3. 시각화 함수
# =============================================================================
def save_batch_stability_figure(batch_df: pd.DataFrame, metrics: List[str] = HEADLINE_METRICS) -> Path:
    """
    100개 단위 배치별 유리 비율(phat)을 오차막대와 함께 그려,
    배치마다 결과가 들쭉날쭉하지 않고 pooled 값 주변에서 안정적으로 흔들리는지 보여준다.
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    axes = axes.flatten()

    for ax, metric in zip(axes, metrics):
        sub = batch_df.loc[batch_df["metric"].eq(metric)].copy()
        if sub.empty:
            continue
        display_name = sub["display_name"].iloc[0]
        pooled = sub["pooled_phat_pct"].iloc[0]
        chi2_p = sub["chi2_p_value"].iloc[0]

        # 배치별 이항 95% CI
        n = sub["n"].iloc[0]
        se = np.sqrt((sub["phat_pct"] / 100.0) * (1 - sub["phat_pct"] / 100.0) / n) * 100.0
        yerr = 1.96 * se

        ax.errorbar(sub["batch"], sub["phat_pct"], yerr=yerr, fmt="o-", capsize=4, color="tab:blue")
        ax.axhline(pooled, linestyle="--", color="tab:red", label=f"pooled={pooled:.1f}%")
        ax.set_ylim(0, 100)
        ax.set_xlabel("Batch (100 sims each)")
        ax.set_ylabel("Advantage rate (%)")
        verdict_txt = "PASS" if chi2_p > ALPHA else "CHECK"
        ax.set_title(f"{display_name}\nchi2 p={chi2_p:.3f} ({verdict_txt})", fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("38c. 100-simulation batch homogeneity — OOS", fontsize=13)
    fig.tight_layout()
    out = FIGURE_DIR / "main_final_fig_38c_batch_percentile_stability.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def save_convergence_band_figure(convergence_df: pd.DataFrame, metrics: List[str] = HEADLINE_METRICS) -> Path:
    """
    누적 표본 수 증가에 따른 이론적 신뢰구간 축소와 최종값으로의 수렴을 보여준다.
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    axes = axes.flatten()

    for ax, metric in zip(axes, metrics):
        sub = convergence_df.loc[convergence_df["metric"].eq(metric)].sort_values("checkpoint")
        if sub.empty:
            continue
        display_name = sub["display_name"].iloc[0]
        final_p = sub["final_phat_pct"].iloc[0]

        ax.plot(sub["checkpoint"], sub["phat_pct"], marker="o", color="tab:blue", label="cumulative estimate")
        ax.fill_between(sub["checkpoint"], sub["ci_low_pct"], sub["ci_high_pct"],
                         color="tab:blue", alpha=0.2, label="95% CI (theoretical)")
        ax.axhline(final_p, linestyle="--", color="tab:red", label=f"final(n=1000)={final_p:.1f}%")
        ax.set_xlabel("Number of placebo simulations")
        ax.set_ylabel("Advantage rate (%)")
        ax.set_title(display_name, fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("38c. Convergence of advantage rate as simulations accumulate — OOS", fontsize=13)
    fig.tight_layout()
    out = FIGURE_DIR / "main_final_fig_38c_convergence_band.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def save_split_half_figure(splithalf_df: pd.DataFrame) -> Path:
    """
    각 지표별 앞 절반(1~500) vs 뒤 절반(501~1000) 유리 비율을 나란히 비교한다.
    """
    df = splithalf_df.copy().sort_values("display_name")
    x = np.arange(len(df))
    width = 0.35

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(x - width / 2, df["phat_first_half_pct"], width, label="first half (1-500)")
    ax.bar(x + width / 2, df["phat_second_half_pct"], width, label="second half (501-1000)")
    ax.set_xticks(x)
    ax.set_xticklabels(df["display_name"], rotation=30, ha="right")
    ax.set_ylabel("Advantage rate (%)")
    ax.set_title("38c. Split-half comparison of advantage rate — OOS")
    for i, (p, diff) in enumerate(zip(df["p_value"], df["diff_pct_points"])):
        tag = "OK" if pd.notna(p) and p > ALPHA else "CHECK"
        ax.text(i, max(df["phat_first_half_pct"].iloc[i], df["phat_second_half_pct"].iloc[i]) + 2,
                 f"diff={diff:+.1f}p\np={p:.2f} ({tag})", ha="center", fontsize=7)
    ax.set_ylim(0, 115)
    ax.legend()
    fig.tight_layout()
    out = FIGURE_DIR / "main_final_fig_38c_split_half_comparison.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def save_verdict_summary_figure(verdict_df: pd.DataFrame) -> Path:
    """
    지표별 chi2 p-value / split-half p-value를 alpha=0.05 기준선과 함께 요약한다.
    막대가 기준선(점선) 위에 있으면 '과적합 근거 없음(PASS)'으로 해석한다.
    """
    df = verdict_df.copy().sort_values("display_name")
    x = np.arange(len(df))
    width = 0.35

    fig, ax = plt.subplots(figsize=(11, 5.5))
    colors_chi2 = ["tab:green" if p > ALPHA else "tab:red" for p in df["chi2_p_value"]]
    colors_sh = ["tab:blue" if p > ALPHA else "tab:orange" for p in df["split_half_p_value"]]

    ax.bar(x - width / 2, df["chi2_p_value"], width, color=colors_chi2, label="batch homogeneity p-value")
    ax.bar(x + width / 2, df["split_half_p_value"], width, color=colors_sh, label="split-half p-value")
    ax.axhline(ALPHA, linestyle="--", color="black", label=f"alpha={ALPHA}")
    ax.set_xticks(x)
    ax.set_xticklabels(df["display_name"], rotation=30, ha="right")
    ax.set_ylabel("p-value")
    ax.set_title("38c. Overfitting check summary — higher p-value = more stable (no overfitting)")
    for i, overall in enumerate(df["overall_no_overfitting_evidence"]):
        tag = "PASS" if overall else "CHECK"
        ax.text(i, max(df["chi2_p_value"].iloc[i], df["split_half_p_value"].iloc[i]) + 0.03,
                 tag, ha="center", fontsize=9, fontweight="bold")
    ax.legend()
    fig.tight_layout()
    out = FIGURE_DIR / "main_final_fig_38c_overfitting_verdict_summary.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


# =============================================================================
# 4. main
# =============================================================================
def main() -> None:
    configure_matplotlib_font()
    ensure_dirs()

    print("=" * 80)
    print("38c_hsi_shuffle_overfitting_check_final.py 실행 시작")
    print("=" * 80)

    print("[1] 38b 산출물 로드")
    runs, actual = load_inputs()

    print("[2] 배치 동질성 / split-half / 수렴 진단 계산")
    batch_df, splithalf_df, convergence_df, verdict_df = run_overfitting_checks(runs, actual)
    print(verdict_df[["display_name", "chi2_p_value", "split_half_p_value",
                       "max_late_convergence_gap_pct_points", "overall_no_overfitting_evidence"]].to_string(index=False))

    print("[3] 저장 (표)")
    batch_df.to_csv(OUTPUT_BATCH, index=False, encoding="utf-8-sig")
    splithalf_df.to_csv(OUTPUT_SPLITHALF, index=False, encoding="utf-8-sig")
    convergence_df.to_csv(OUTPUT_CONVERGENCE, index=False, encoding="utf-8-sig")
    verdict_df.to_csv(OUTPUT_VERDICT, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_BATCH}")
    print(f"    저장: {OUTPUT_SPLITHALF}")
    print(f"    저장: {OUTPUT_CONVERGENCE}")
    print(f"    저장: {OUTPUT_VERDICT}")

    print("[4] 시각화")
    fig1 = save_batch_stability_figure(batch_df)
    fig2 = save_convergence_band_figure(convergence_df)
    fig3 = save_split_half_figure(splithalf_df)
    fig4 = save_verdict_summary_figure(verdict_df)
    print(f"    저장: {fig1}")
    print(f"    저장: {fig2}")
    print(f"    저장: {fig3}")
    print(f"    저장: {fig4}")

    n_pass = int(verdict_df["overall_no_overfitting_evidence"].sum())
    n_total = len(verdict_df)
    print(f"[결론] {n_total}개 지표 중 {n_pass}개가 3개 조건(배치동질성, split-half, 수렴) 모두 통과")

    print("=" * 80)
    print("38c_hsi_shuffle_overfitting_check_final.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
