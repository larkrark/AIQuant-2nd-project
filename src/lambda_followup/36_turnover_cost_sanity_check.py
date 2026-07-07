# -*- coding: utf-8 -*-
"""
36_turnover_cost_sanity_check.py

목적
----
강사님 피드백 반영:
성과만 보지 않고 전략별 회전율, 거래비용, 연도별 성과를 함께 점검한다.

확인 항목
---------
1) 전략별 연도별 수익률
2) 전략별 연도별 Turnover
3) 연간 Turnover 100% / 200% 초과 여부
4) 비용 0bp / 5bp / 10bp / 20bp 차감 성과
5) 성과는 비슷하지만 회전율이 과도한 전략 여부
6) 회전율은 낮지만 성과가 나빠 실전 후보로 부적합한 전략 여부

출력
----
output/tables/main_final_annual_turnover_return_check.csv
output/tables/main_final_turnover_cost_sanity_summary.csv
output/figures/main_final_fig_annual_turnover_by_strategy.png
output/figures/main_final_fig_annual_return_vs_turnover.png
"""

import importlib
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
import common as X

dyn = importlib.import_module("30_dynamic_lambda_rule_v1")
dyn_macro = importlib.import_module("30_dynamic_lambda_rule_v1_macro")


STRATEGIES = [
    ("lambda_0.1", 0.10, 0.10),
    ("lambda_0.3", 0.30, 0.30),
    ("asym_up0.1_down0.3", 0.10, 0.30),
    ("asym_up0.1_down0.5", 0.10, 0.50),
    ("asym_up0.2_down0.3", 0.20, 0.30),
    ("dynamic_v1", None, None),
    ("dynamic_v1_macro", None, None),
]

COST_BPS = [0, 5, 10, 20]


def clean_strategy_name(name: str) -> str:
    mapping = {
        "lambda_0.1": "lambda 0.1",
        "lambda_0.3": "lambda 0.3",
        "asym_up0.1_down0.3": "asym 0.1/0.3",
        "asym_up0.1_down0.5": "asym 0.1/0.5",
        "asym_up0.2_down0.3": "asym 0.2/0.3",
        "dynamic_v1": "dynamic v1",
        "dynamic_v1_macro": "dynamic v1 macro",
    }
    return mapping.get(name, name)


def run_strategy(name: str, lu, ld, returns: pd.DataFrame, target_w: pd.DataFrame) -> pd.DataFrame:
    if name == "dynamic_v1":
        sv = dyn.build_state_variables(returns, target_w)
        lam_t, _ = dyn.assign_lambda(sv)
        lam_t = lam_t.fillna(C.E30_RULE_V1["lambda_base"])
        return X.run_lambda_backtest(
            returns,
            target_w,
            np.nan,
            np.nan,
            lambda_series=lam_t,
        )

    if name == "dynamic_v1_macro":
        sv_macro = dyn_macro.build_state_variables_macro(returns, target_w)
        lam_macro, _, _ = dyn_macro.assign_lambda_macro(sv_macro)
        lam_macro = lam_macro.fillna(C.E30_RULE_V1["lambda_base"])
        return X.run_lambda_backtest(
            returns,
            target_w,
            np.nan,
            np.nan,
            lambda_series=lam_macro,
        )

    return X.run_lambda_backtest(returns, target_w, lu, ld)


def annual_return(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) == 0:
        return np.nan
    return ((1 + r).prod() - 1) * 100


def max_drawdown(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) == 0:
        return np.nan
    idx = (1 + r).cumprod()
    dd = idx / idx.cummax() - 1
    return dd.min() * 100


def make_annual_table(backtests: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []

    for name, bt in backtests.items():
        tmp = bt.copy()
        tmp["year"] = tmp.index.year

        for year, g in tmp.groupby("year"):
            gross_r = g["strategy_return_gross"]
            annual_to = g["turnover"].sum() * 100
            avg_monthly_to = g["turnover"].mean() * 100

            rows.append({
                "strategy": name,
                "year": int(year),
                "months": int(len(g)),
                "annual_return_gross_pct": annual_return(gross_r),
                "annual_mdd_gross_pct": max_drawdown(gross_r),
                "annual_turnover_pct": annual_to,
                "avg_monthly_turnover_pct": avg_monthly_to,
                "turnover_flag_100": annual_to >= 100,
                "turnover_flag_200": annual_to >= 200,
            })

    return pd.DataFrame(rows)


def make_cost_summary(backtests: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []

    for name, bt in backtests.items():
        for bp in COST_BPS:
            net = bt["strategy_return_gross"] - bt["turnover"] * (bp / 10000.0)

            m = X.perf_metrics(net, bt["turnover"], label=name)
            rows.append({
                "strategy": name,
                "cost_bp": bp,
                "months": m["months"],
                "cagr_pct": m["cagr_pct"],
                "ann_vol_pct": m["ann_vol_pct"],
                "mdd_pct": m["mdd_pct"],
                "sharpe": m["sharpe"],
                "calmar": m["calmar"],
                "avg_turnover_pct": m["avg_turnover_pct"],
                "annualized_avg_turnover_pct": m["avg_turnover_pct"] * 12,
            })

    return pd.DataFrame(rows)


def make_sanity_summary(annual: pd.DataFrame, cost_summary: pd.DataFrame) -> pd.DataFrame:
    base = cost_summary[cost_summary["cost_bp"] == 10].copy()

    ann_summary = annual.groupby("strategy").agg(
        max_annual_turnover_pct=("annual_turnover_pct", "max"),
        mean_annual_turnover_pct=("annual_turnover_pct", "mean"),
        years_turnover_over_100=("turnover_flag_100", "sum"),
        years_turnover_over_200=("turnover_flag_200", "sum"),
        worst_annual_return_pct=("annual_return_gross_pct", "min"),
        best_annual_return_pct=("annual_return_gross_pct", "max"),
    ).reset_index()

    out = base.merge(ann_summary, on="strategy", how="left")

    def judge(row):
        if row["years_turnover_over_200"] > 0:
            return "주의: 특정 연도 Turnover 200% 이상"
        if row["years_turnover_over_100"] > 0:
            return "점검: 특정 연도 Turnover 100% 이상"
        if row["annualized_avg_turnover_pct"] < 100 and row["calmar"] > 0.7:
            return "양호: 평균 회전율 100% 미만 + Calmar 양호"
        if row["annualized_avg_turnover_pct"] < 100 and row["calmar"] <= 0.5:
            return "보류: 회전율은 낮으나 성과-위험 매력 제한"
        return "중립: 성과와 회전율 함께 해석 필요"

    out["turnover_cost_judgement"] = out.apply(judge, axis=1)

    cols = [
        "strategy",
        "cost_bp",
        "cagr_pct",
        "mdd_pct",
        "calmar",
        "avg_turnover_pct",
        "annualized_avg_turnover_pct",
        "mean_annual_turnover_pct",
        "max_annual_turnover_pct",
        "years_turnover_over_100",
        "years_turnover_over_200",
        "worst_annual_return_pct",
        "best_annual_return_pct",
        "turnover_cost_judgement",
    ]
    return out[cols]


def plot_annual_turnover(annual: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(13, 6))

    selected = [
        "lambda_0.1",
        "lambda_0.3",
        "asym_up0.1_down0.3",
        "dynamic_v1",
        "dynamic_v1_macro",
    ]

    for name in selected:
        sub = annual[annual["strategy"] == name].sort_values("year")
        if sub.empty:
            continue
        ax.plot(
            sub["year"],
            sub["annual_turnover_pct"],
            marker="o",
            linewidth=1.8,
            label=clean_strategy_name(name),
        )

    ax.axhline(100, linestyle="--", linewidth=1.0, alpha=0.8)
    ax.axhline(200, linestyle="--", linewidth=1.0, alpha=0.8)
    ax.text(annual["year"].min(), 102, "100% 기준", fontsize=9, va="bottom")
    ax.text(annual["year"].min(), 202, "200% 주의 기준", fontsize=9, va="bottom")

    ax.set_title("전략별 연도별 Turnover 점검")
    ax.set_xlabel("연도")
    ax.set_ylabel("연간 Turnover (%)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    out = C.FIGURE_DIR / f"{C.FINAL_PREFIX}fig_annual_turnover_by_strategy.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_return_vs_turnover(summary: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10.5, 6.2))

    x = summary["annualized_avg_turnover_pct"]
    y = summary["calmar"]

    ax.scatter(x, y, s=90, zorder=3)

    # 점이 몰려 있는 구간의 라벨을 수동 배치한다.
    # 값은 (라벨 x좌표, 라벨 y좌표)이며, 점 위치와 다르게 둘 수 있다.
    label_pos = {
        "lambda_0.1": (32, 0.605),
        "lambda_0.3": (87, 0.600),
        "asym_up0.1_down0.3": (43, 0.775),
        "asym_up0.1_down0.5": (63, 0.842),
        "asym_up0.2_down0.3": (73, 0.680),
        "dynamic_v1": (57, 0.720),
        "dynamic_v1_macro": (72, 0.765),
    }

    for _, row in summary.iterrows():
        strategy = row["strategy"]
        label = clean_strategy_name(strategy)

        px = row["annualized_avg_turnover_pct"]
        py = row["calmar"]

        tx, ty = label_pos.get(strategy, (px + 2, py + 0.02))

        ax.annotate(
            label,
            xy=(px, py),
            xytext=(tx, ty),
            textcoords="data",
            fontsize=8,
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.22",
                facecolor="white",
                edgecolor="lightgray",
                alpha=0.85,
            ),
            arrowprops=dict(
                arrowstyle="-",
                color="gray",
                lw=0.7,
                alpha=0.7,
                shrinkA=2,
                shrinkB=5,
            ),
            zorder=4,
        )

    ax.axvline(100, linestyle="--", linewidth=1.0, alpha=0.8)
    ax.axvline(200, linestyle="--", linewidth=1.0, alpha=0.8)
    ax.axhline(0, linewidth=0.8)

    ax.set_title("비용차감 Calmar vs 평균 연환산 Turnover — 10bp 기준")
    ax.set_xlabel("평균 연환산 Turnover (%)")
    ax.set_ylabel("Calmar, net 10bp")

    # 100%, 200% 기준선을 보여주되, 점들이 몰린 구간의 라벨이 잘리지 않도록 여백 확보
    ax.set_xlim(20, 210)
    ax.set_ylim(0.50, 0.86)

    ax.grid(True, alpha=0.25)

    out = C.FIGURE_DIR / f"{C.FINAL_PREFIX}fig_annual_return_vs_turnover.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def write_report_note(summary: pd.DataFrame) -> Path:
    path = Path(__file__).resolve().parents[2] / "reports" / "main_final_turnover_cost_report_note.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# 회전율·거래비용 점검 보고서 삽입문\n")
    lines.append("본 절은 강사님 피드백 중 슬리피지, 거래비용, 회전율, 기간별 성과를 함께 확인해야 한다는 지적을 반영한 추가 검증이다.\n")
    lines.append("본 프로젝트는 실제 호가 스프레드, 시장충격비용, 체결 실패 가능성을 직접 모델링하지 않았다. 대신 Turnover × 비용률 방식으로 0bp, 5bp, 10bp, 20bp 비용 민감도를 적용하였다. 따라서 비용 결과는 실거래 비용의 정확한 추정치가 아니라, 회전율이 높은 전략이 비용에 얼마나 취약한지 확인하기 위한 민감도 분석으로 해석한다.\n")
    lines.append("전략별 연도별 Turnover를 계산하여 특정 연도에 매매가 과도하게 집중되는지 확인하였다. 강사님 피드백에 따라 연간 Turnover 100%와 200%를 점검 기준으로 두었다. 100% 미만은 비교적 안정적인 수준으로 해석하고, 100~200% 구간은 주의, 200% 이상은 실전 적용 신뢰도 측면에서 보수적으로 해석한다.\n")
    lines.append("\n## 10bp 비용차감 요약\n")
    lines.append(summary.round(3).to_markdown(index=False))
    lines.append("\n\n## 보고서 해석 문장\n")
    lines.append("주요 후보 전략은 성과지표뿐 아니라 평균 Turnover와 연도별 Turnover를 함께 기준으로 검토하였다. 성과가 비슷한 전략이라도 회전율이 높으면 실제 운용에서는 거래비용과 슬리피지에 더 취약할 수 있기 때문이다. 반대로 회전율이 낮더라도 CAGR, MDD, Calmar가 부진하면 실전 후보로 보기 어렵다.\n")
    lines.append("따라서 본 보고서에서는 CAGR만으로 후보를 선택하지 않고, OOS 10bp 비용차감 성과, MDD, tail-month 방어력, 평균 Turnover, 연도별 Turnover를 함께 확인하였다. 이 절차는 백테스트 성과가 과도한 매매 빈도나 사후적 후보 선택에서 나온 것이 아닌지 점검하기 위한 것이다.\n")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    C.FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    returns = X.load_monthly_returns()
    target_w = X.load_target_weights()

    backtests = {}
    for name, lu, ld in STRATEGIES:
        backtests[name] = run_strategy(name, lu, ld, returns, target_w)

    annual = make_annual_table(backtests)
    cost_summary = make_cost_summary(backtests)
    sanity = make_sanity_summary(annual, cost_summary)

    annual_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}annual_turnover_return_check.csv"
    cost_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}turnover_cost_by_cost_bp.csv"
    sanity_path = C.TABLE_DIR / f"{C.FINAL_PREFIX}turnover_cost_sanity_summary.csv"

    annual.to_csv(annual_path, index=False, encoding="utf-8-sig")
    cost_summary.to_csv(cost_path, index=False, encoding="utf-8-sig")
    sanity.to_csv(sanity_path, index=False, encoding="utf-8-sig")

    fig1 = plot_annual_turnover(annual)
    fig2 = plot_return_vs_turnover(sanity)
    note = write_report_note(sanity)

    print("[완료] 36_turnover_cost_sanity_check")
    print(f"- annual table: {annual_path}")
    print(f"- cost summary: {cost_path}")
    print(f"- sanity summary: {sanity_path}")
    print(f"- annual turnover fig: {fig1}")
    print(f"- return vs turnover fig: {fig2}")
    print(f"- report note: {note}")

    print("\n[10bp 비용차감 회전율 점검 요약]")
    print(sanity.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
