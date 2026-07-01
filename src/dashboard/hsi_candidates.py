from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from .paths import HSI_CANDIDATE_DATA_DIR, HSI_CANDIDATE_OUTPUT_DIR


TS_FILE = "23_main_final_report_candidate_timeseries_subset_dedup.csv"
SHORTLIST_FILE = "23_main_final_report_candidate_shortlist.csv"
COST_FILE = "23_main_final_report_candidate_cost_pivot.csv"

DISPLAY_STRATEGIES = [
    "EW",
    "HSI_final_baseline_overlay",
    "lambda_0.1",
    "lambda_0.3",
    "lambda_0.5",
    "HSI_event_balance_filter_overlay",
]

LABEL_MAP = {
    "EW": "EW",
    "HSI_final_baseline_overlay": "HSI Baseline",
    "lambda_0.1": "Lambda 0.1",
    "lambda_0.3": "Lambda 0.3",
    "lambda_0.5": "Lambda 0.5",
    "HSI_event_balance_filter_overlay": "Event Filter",
}

ROLE_MAP = {
    "EW": "Sharpe가 가장 높은 단순 비교 기준",
    "HSI_final_baseline_overlay": "최종 후보가 아닌 기준선",
    "lambda_0.1": "MDD와 Turnover 완화 후보",
    "lambda_0.3": "수익성, Calmar, Turnover 균형 후보",
    "lambda_0.5": "중간 부분조정 후보",
    "HSI_event_balance_filter_overlay": "진단 및 보조 필터 후보",
}

COLOR_MAP = {
    "EW": "#4C566A",
    "HSI Baseline": "#C44E52",
    "Lambda 0.1": "#55A868",
    "Lambda 0.3": "#1F77B4",
    "Lambda 0.5": "#8172B2",
    "Event Filter": "#DD8452",
}


@st.cache_data
def read_candidate_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ts = pd.read_csv(HSI_CANDIDATE_DATA_DIR / TS_FILE, encoding="utf-8-sig")
    shortlist = pd.read_csv(HSI_CANDIDATE_DATA_DIR / SHORTLIST_FILE, encoding="utf-8-sig")
    cost = pd.read_csv(HSI_CANDIDATE_DATA_DIR / COST_FILE, encoding="utf-8-sig")

    ts["year_month"] = pd.to_datetime(ts["year_month"])
    for frame in (ts, shortlist, cost):
        frame["strategy_label"] = frame["strategy_name"].map(LABEL_MAP).fillna(frame["strategy_name"])
    return ts, shortlist, cost


def filter_display(frame: pd.DataFrame, selected_labels: list[str] | None = None) -> pd.DataFrame:
    out = frame[frame["strategy_name"].isin(DISPLAY_STRATEGIES)].copy()
    out["strategy_name"] = pd.Categorical(out["strategy_name"], DISPLAY_STRATEGIES, ordered=True)
    if selected_labels:
        out = out[out["strategy_label"].isin(selected_labels)]

    sort_cols = ["strategy_name"]
    if "year_month" in out.columns:
        sort_cols.append("year_month")
    if "cost_bps" in out.columns:
        sort_cols.append("cost_bps")
    return out.sort_values(sort_cols)


def common_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left"},
        template="plotly_white",
        hovermode="x unified",
        legend_title_text="전략",
        margin={"l": 44, "r": 24, "t": 62, "b": 42},
        font={"family": "Arial, Malgun Gothic, sans-serif", "size": 13},
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#ECEFF4")
    return fig


def cumulative_return_fig(ts: pd.DataFrame) -> go.Figure:
    fig = px.line(
        ts,
        x="year_month",
        y="cumulative_return",
        color="strategy_label",
        color_discrete_map=COLOR_MAP,
        labels={"year_month": "월", "cumulative_return": "누적수익 지수", "strategy_label": "전략"},
        hover_data={
            "strategy_label": False,
            "year_month": "|%Y-%m",
            "cumulative_return": ":.3f",
            "strategy_return": ":.2%",
            "drawdown": ":.2%",
            "turnover": ":.2%",
        },
    )
    fig.update_yaxes(tickformat=".2f")
    return common_layout(fig, "누적수익률")


def drawdown_fig(ts: pd.DataFrame) -> go.Figure:
    fig = px.line(
        ts,
        x="year_month",
        y="drawdown",
        color="strategy_label",
        color_discrete_map=COLOR_MAP,
        labels={"year_month": "월", "drawdown": "Drawdown", "strategy_label": "전략"},
        hover_data={
            "strategy_label": False,
            "year_month": "|%Y-%m",
            "drawdown": ":.2%",
            "cumulative_return": ":.3f",
            "strategy_return": ":.2%",
            "turnover": ":.2%",
        },
    )
    fig.update_yaxes(tickformat=".0%")
    return common_layout(fig, "Drawdown")


def metric_summary_fig(shortlist: pd.DataFrame) -> go.Figure:
    metrics = shortlist.copy()
    metrics["MDD_abs_pct"] = metrics["MDD_pct"].abs()

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("CAGR", "MDD 절대값", "Calmar", "평균 Turnover"),
        horizontal_spacing=0.1,
        vertical_spacing=0.18,
    )
    panels = [
        ("CAGR_pct", "CAGR (%)", 1, 1),
        ("MDD_abs_pct", "|MDD| (%)", 1, 2),
        ("Calmar", "Calmar", 2, 1),
        ("avg_turnover_pct", "평균 Turnover (%)", 2, 2),
    ]
    colors = [COLOR_MAP.get(label, "#2563eb") for label in metrics["strategy_label"]]
    for col_name, trace_name, row, col in panels:
        fig.add_trace(
            go.Bar(
                x=metrics["strategy_label"],
                y=metrics[col_name],
                marker_color=colors,
                name=trace_name,
                text=[f"{value:.2f}" for value in metrics[col_name]],
                textposition="outside",
                showlegend=False,
            ),
            row=row,
            col=col,
        )
        fig.update_yaxes(title_text=trace_name, gridcolor="#ECEFF4", row=row, col=col)
    fig.update_xaxes(tickangle=-18)
    fig.update_layout(
        title={"text": "성과, 위험, 회전율 요약", "x": 0.01, "xanchor": "left"},
        template="plotly_white",
        height=680,
        margin={"l": 44, "r": 24, "t": 74, "b": 62},
        font={"family": "Arial, Malgun Gothic, sans-serif", "size": 13},
    )
    return fig


def calmar_turnover_fig(shortlist: pd.DataFrame) -> go.Figure:
    metrics = shortlist.copy()
    metrics["MDD_abs_pct"] = metrics["MDD_pct"].abs()
    metrics["role_note"] = metrics["strategy_name"].map(ROLE_MAP)
    fig = px.scatter(
        metrics,
        x="avg_turnover_pct",
        y="Calmar",
        size="CAGR_pct",
        color="strategy_label",
        text="strategy_label",
        color_discrete_map=COLOR_MAP,
        labels={
            "avg_turnover_pct": "평균 Turnover (%)",
            "Calmar": "Calmar",
            "strategy_label": "전략",
            "CAGR_pct": "CAGR (%)",
        },
        hover_data={"CAGR_pct": ":.2f", "MDD_abs_pct": ":.2f", "Sharpe": ":.3f", "role_note": True},
    )
    fig.update_traces(textposition="top center", marker={"line": {"width": 1, "color": "white"}})
    return common_layout(fig, "Calmar와 Turnover 관점 후보 비교")


def cost_sensitivity_fig(cost: pd.DataFrame) -> go.Figure:
    fig = px.line(
        cost,
        x="cost_bps",
        y="CAGR_pct_after_cost_est",
        color="strategy_label",
        markers=True,
        color_discrete_map=COLOR_MAP,
        labels={
            "cost_bps": "거래비용 가정 (bps)",
            "CAGR_pct_after_cost_est": "비용 반영 후 추정 CAGR (%)",
            "strategy_label": "전략",
        },
        hover_data={
            "CAGR_pct_before_cost": ":.2f",
            "avg_turnover_pct": ":.2f",
            "annual_cost_drag_pct_est": ":.3f",
            "CAGR_pct_after_cost_est": ":.2f",
        },
    )
    fig.update_yaxes(ticksuffix="%")
    return common_layout(fig, "거래비용 민감도")


def turnover_fig(ts: pd.DataFrame) -> go.Figure:
    fig = px.line(
        ts,
        x="year_month",
        y="turnover",
        color="strategy_label",
        color_discrete_map=COLOR_MAP,
        labels={"year_month": "월", "turnover": "월별 Turnover", "strategy_label": "전략"},
        hover_data={"year_month": "|%Y-%m", "turnover": ":.2%", "strategy_return": ":.2%"},
    )
    fig.update_yaxes(tickformat=".0%")
    return common_layout(fig, "월별 Turnover")


def render_metric_cards(shortlist: pd.DataFrame) -> None:
    cols = st.columns(3)
    lambda_03 = shortlist[shortlist["strategy_name"] == "lambda_0.3"].iloc[0]
    lambda_01 = shortlist[shortlist["strategy_name"] == "lambda_0.1"].iloc[0]
    ew = shortlist[shortlist["strategy_name"] == "EW"].iloc[0]

    cols[0].metric("Lambda 0.3 CAGR", f"{lambda_03['CAGR_pct']:.2f}%", f"Calmar {lambda_03['Calmar']:.3f}")
    cols[1].metric("Lambda 0.1 Avg Turnover", f"{lambda_01['avg_turnover_pct']:.2f}%", "낮은 회전율 후보")
    cols[2].metric("EW Sharpe", f"{ew['Sharpe']:.3f}", "Sharpe 최고 기준")


def render_file_links() -> None:
    dashboard = HSI_CANDIDATE_OUTPUT_DIR / "hsi_candidate_visual_dashboard.html"
    with st.expander("정리된 파일 위치"):
        st.write(f"데이터: `{HSI_CANDIDATE_DATA_DIR}`")
        st.write(f"HTML 산출물: `{HSI_CANDIDATE_OUTPUT_DIR}`")
        if dashboard.exists():
            st.link_button("HTML 대시보드 열기", Path(dashboard).as_uri())


def render() -> None:
    ts, shortlist, cost = read_candidate_data()

    labels = [LABEL_MAP[name] for name in DISPLAY_STRATEGIES]
    selected_labels = st.sidebar.multiselect("표시 전략", labels, default=labels)

    plot_ts = filter_display(ts, selected_labels)
    plot_shortlist = filter_display(shortlist, selected_labels)
    plot_cost = filter_display(cost, selected_labels)

    st.title("HSI 후보 전략 대시보드")
    st.caption("최종 후보 검토용 Streamlit 시작 페이지")

    st.info(
        "HSI Baseline은 최종 후보가 아니라 기준선입니다. Lambda 0.1과 Lambda 0.3은 Baseline 대비 "
        "MDD와 Turnover를 완화한 후보이며, EW는 Sharpe가 가장 높으므로 Lambda 후보가 모든 지표에서 "
        "우수하다고 표현하지 않는 것이 안전합니다."
    )

    render_metric_cards(filter_display(shortlist))

    chart_tabs = st.tabs(["성과 흐름", "후보 비교", "비용/회전율", "데이터"])
    with chart_tabs[0]:
        st.plotly_chart(cumulative_return_fig(plot_ts), use_container_width=True)
        st.plotly_chart(drawdown_fig(plot_ts), use_container_width=True)
    with chart_tabs[1]:
        st.plotly_chart(metric_summary_fig(plot_shortlist), use_container_width=True)
        st.plotly_chart(calmar_turnover_fig(plot_shortlist), use_container_width=True)
    with chart_tabs[2]:
        st.plotly_chart(cost_sensitivity_fig(plot_cost), use_container_width=True)
        st.plotly_chart(turnover_fig(plot_ts), use_container_width=True)
    with chart_tabs[3]:
        display_cols = [
            "shortlist_rank",
            "strategy_label",
            "presentation_role",
            "CAGR_pct",
            "MDD_pct",
            "Sharpe",
            "Calmar",
            "avg_turnover_pct",
            "goldfriend_judgement",
        ]
        st.dataframe(
            filter_display(shortlist)[display_cols].round(3),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"중복 제거 시계열: {len(ts):,} rows, 중복 pair {ts.duplicated(['strategy_name', 'year_month']).sum():,}")
        render_file_links()

