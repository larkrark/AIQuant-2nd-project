from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ============================================================
# 1. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TABLE_DIR = PROJECT_ROOT / "output" / "tables"
FIGURE_DIR = PROJECT_ROOT / "output" / "figures"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)


TS_PATH = TABLE_DIR / "23_main_final_report_candidate_timeseries_subset_dedup.csv"
LAMBDA_TABLE_PATH = TABLE_DIR / "23_main_final_report_lambda_family_table.csv"
SHORTLIST_PATH = TABLE_DIR / "23_main_final_report_candidate_shortlist.csv"
COST_PIVOT_PATH = TABLE_DIR / "23_main_final_report_candidate_cost_pivot.csv"


# ============================================================
# 2. 데이터 로드
# ============================================================

ts = pd.read_csv(TS_PATH, encoding="utf-8-sig")
lambda_table = pd.read_csv(LAMBDA_TABLE_PATH, encoding="utf-8-sig")
shortlist = pd.read_csv(SHORTLIST_PATH, encoding="utf-8-sig")
cost_pivot = pd.read_csv(COST_PIVOT_PATH, encoding="utf-8-sig")


# 혹시 전달 과정에서 중복이 다시 생겼을 경우를 대비한 안전장치
ts = (
    ts
    .sort_values(["strategy_name", "year_month"])
    .drop_duplicates(subset=["strategy_name", "year_month"], keep="last")
    .reset_index(drop=True)
)

ts["year_month"] = pd.to_datetime(ts["year_month"])


# ============================================================
# 3. 표시할 전략 선택
# ============================================================

DISPLAY_STRATEGIES = [
    "EW",
    "HSI_final_baseline_overlay",
    "lambda_0.1",
    "lambda_0.3",
    "lambda_0.5",
    "HSI_event_balance_filter_overlay",
]

available_strategies = ts["strategy_name"].unique().tolist()

selected_strategies = [
    s for s in DISPLAY_STRATEGIES
    if s in available_strategies
]

plot_ts = ts[ts["strategy_name"].isin(selected_strategies)].copy()


# ============================================================
# 4. 전략명 표시용 라벨
# ============================================================

LABEL_MAP = {
    "EW": "EW Benchmark",
    "HSI_final_baseline_overlay": "HSI Baseline",
    "HSI_event_balance_filter_overlay": "Event Filter",
    "lambda_0.1": "Lambda 0.1",
    "lambda_0.3": "Lambda 0.3",
    "lambda_0.5": "Lambda 0.5",
    "lambda_0.7": "Lambda 0.7",
    "lambda_1.0": "Lambda 1.0",
}

plot_ts["strategy_label"] = plot_ts["strategy_name"].map(LABEL_MAP).fillna(plot_ts["strategy_name"])
lambda_table["strategy_label"] = lambda_table["strategy_name"].map(LABEL_MAP).fillna(lambda_table["strategy_name"])


# ============================================================
# 5. 누적수익률 그래프
# ============================================================

fig_cum = px.line(
    plot_ts,
    x="year_month",
    y="cumulative_return",
    color="strategy_label",
    hover_data={
        "strategy_name": True,
        "year_month": "|%Y-%m",
        "cumulative_return": ":.3f",
        "strategy_return": ":.3%",
        "drawdown": ":.3%",
        "turnover": ":.3%",
    },
    title="HSI Overlay 후보 전략 누적수익률 비교",
    labels={
        "year_month": "월",
        "cumulative_return": "누적수익률 지수",
        "strategy_label": "전략",
    },
)

fig_cum.update_layout(
    hovermode="x unified",
    template="plotly_white",
    legend_title_text="전략",
)

fig_cum.update_xaxes(
    showspikes=True,
    spikecolor="blue",
    spikethickness=1,
    spikemode="across",
    spikesnap="cursor",
)

fig_cum.write_html(FIGURE_DIR / "hsi_candidate_cumulative_return.html")
fig_cum.show()


# ============================================================
# 6. Drawdown 그래프
# ============================================================

fig_dd = px.line(
    plot_ts,
    x="year_month",
    y="drawdown",
    color="strategy_label",
    hover_data={
        "strategy_name": True,
        "year_month": "|%Y-%m",
        "drawdown": ":.3%",
        "cumulative_return": ":.3f",
        "strategy_return": ":.3%",
        "turnover": ":.3%",
    },
    title="HSI Overlay 후보 전략 Drawdown 비교",
    labels={
        "year_month": "월",
        "drawdown": "Drawdown",
        "strategy_label": "전략",
    },
)

fig_dd.update_layout(
    hovermode="x unified",
    template="plotly_white",
    legend_title_text="전략",
)

fig_dd.update_yaxes(tickformat=".0%")

fig_dd.update_xaxes(
    showspikes=True,
    spikecolor="blue",
    spikethickness=1,
    spikemode="across",
    spikesnap="cursor",
)

fig_dd.write_html(FIGURE_DIR / "hsi_candidate_drawdown.html")
fig_dd.show()


# ============================================================
# 7. λ 후보 성과 비교 막대그래프
# ============================================================

lambda_plot = lambda_table[
    lambda_table["strategy_name"].isin([
        "EW",
        "HSI_final_baseline_overlay",
        "lambda_0.1",
        "lambda_0.3",
        "lambda_0.5",
        "lambda_0.7",
    ])
].copy()

fig_lambda = go.Figure()

fig_lambda.add_trace(
    go.Bar(
        x=lambda_plot["strategy_label"],
        y=lambda_plot["CAGR_pct"],
        name="CAGR",
        text=lambda_plot["CAGR_pct"].round(2).astype(str) + "%",
        textposition="outside",
    )
)

fig_lambda.add_trace(
    go.Bar(
        x=lambda_plot["strategy_label"],
        y=lambda_plot["MDD_pct"],
        name="MDD",
        text=lambda_plot["MDD_pct"].round(2).astype(str) + "%",
        textposition="outside",
    )
)

fig_lambda.add_trace(
    go.Bar(
        x=lambda_plot["strategy_label"],
        y=lambda_plot["avg_turnover_pct"],
        name="Avg Turnover",
        text=lambda_plot["avg_turnover_pct"].round(2).astype(str) + "%",
        textposition="outside",
    )
)

fig_lambda.update_layout(
    title="λ 부분조정 후보 성과 비교",
    xaxis_title="전략",
    yaxis_title="%",
    barmode="group",
    template="plotly_white",
    legend_title_text="지표",
)

fig_lambda.write_html(FIGURE_DIR / "hsi_lambda_family_bar.html")
fig_lambda.show()


# ============================================================
# 8. 비용 민감도 그래프
# ============================================================

cost_selected = cost_pivot[
    cost_pivot["strategy_name"].isin([
        "HSI_final_baseline_overlay",
        "lambda_0.1",
        "lambda_0.3",
        "lambda_0.5",
        "HSI_event_balance_filter_overlay",
    ])
].copy()

cost_selected["strategy_label"] = (
    cost_selected["strategy_name"]
    .map(LABEL_MAP)
    .fillna(cost_selected["strategy_name"])
)

fig_cost = px.line(
    cost_selected,
    x="cost_bps",
    y="CAGR_pct_after_cost_est",
    color="strategy_label",
    markers=True,
    hover_data={
        "strategy_name": True,
        "cost_bps": True,
        "CAGR_pct_before_cost": ":.2f",
        "avg_turnover_pct": ":.2f",
        "annual_cost_drag_pct_est": ":.3f",
        "CAGR_pct_after_cost_est": ":.2f",
    },
    title="거래비용 가정별 추정 CAGR 비교",
    labels={
        "cost_bps": "거래비용 가정 (bps)",
        "CAGR_pct_after_cost_est": "비용 반영 후 추정 CAGR (%)",
        "strategy_label": "전략",
    },
)

fig_cost.update_layout(
    hovermode="x unified",
    template="plotly_white",
    legend_title_text="전략",
)

fig_cost.write_html(FIGURE_DIR / "hsi_candidate_cost_sensitivity.html")
fig_cost.show()


print("시각화 파일 생성 완료")
print(FIGURE_DIR)