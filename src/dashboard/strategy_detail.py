from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from .paths import HSI_CANDIDATE_DATA_DIR


TS_FILE = "23_main_final_report_candidate_timeseries_subset_dedup.csv"
SHORTLIST_FILE = "23_main_final_report_candidate_shortlist.csv"

# λ=0.7은 shortlist에 없어 docs/main_final_lambda_experiment_note.md 성과 표 값을 사용
LAMBDA_07_ROW = {
    "lambda_value": 0.7,
    "CAGR_pct": 8.0646,
    "MDD_pct": -19.9646,
    "Sharpe": 0.6819,
    "Calmar": 0.4039,
}

LAMBDA_METRICS = {
    "CAGR (%)": ("CAGR_pct", "높을수록 좋음"),
    "누적수익률 (%)": ("cumulative_pct", "높을수록 좋음"),
    "Sharpe": ("Sharpe", "높을수록 좋음"),
    "MDD (%)": ("MDD_pct", "0에 가까울수록 좋음"),
    "Calmar": ("Calmar", "높을수록 좋음"),
}

STRATEGY_LABELS = {
    "lambda_0.3": "Lambda 0.3",
    "lambda_0.1": "Lambda 0.1",
    "lambda_0.5": "Lambda 0.5",
    "HSI_final_baseline_overlay": "HSI Baseline",
    "HSI_event_balance_filter_overlay": "Event Filter",
    "EW": "EW",
}
DEFAULT_STRATEGY = "lambda_0.3"
BENCHMARK = "EW"

ASSETS = {
    "069500": ("KODEX 200 (주식)", "#2ca02c"),
    "114260": ("KODEX 국고채 (채권)", "#1f77b4"),
    "153130": ("KODEX 단기채권 (현금성)", "#f2a65e"),
}

STATE_ORDER = ["insufficient_data", "risk_relief", "neutral_watch", "conflict", "risk_warning", "accident_zone"]
STATE_KR = {
    "insufficient_data": "데이터 부족",
    "risk_relief": "위험 완화",
    "neutral_watch": "관찰 중립",
    "conflict": "충돌",
    "risk_warning": "위험 악화",
    "accident_zone": "강한 위험 악화",
    "EW": "해당 없음",
}
STATE_COLOR = {
    "risk_relief": "#55A868",
    "neutral_watch": "#8C8C8C",
    "conflict": "#8172B2",
    "risk_warning": "#DD8452",
    "accident_zone": "#C44E52",
    "insufficient_data": "#CCCCCC",
    "EW": "#CCCCCC",
}

INITIAL_CAPITAL = 1_000_000


@st.cache_data
def load_timeseries() -> pd.DataFrame:
    df = pd.read_csv(HSI_CANDIDATE_DATA_DIR / TS_FILE)
    df["date"] = pd.to_datetime(df["year_month"])
    return df.sort_values("date")


def strategy_frame(df: pd.DataFrame, name: str) -> pd.DataFrame:
    return df[df["strategy_name"] == name].reset_index(drop=True)


def compute_metrics(frame: pd.DataFrame) -> dict[str, float]:
    ret = frame["strategy_return"]
    n_months = len(frame)
    total = frame["cumulative_return"].iloc[-1]
    cagr = total ** (12 / n_months) - 1 if n_months > 0 else np.nan
    vol = ret.std() * np.sqrt(12)
    sharpe = ret.mean() / ret.std() * np.sqrt(12) if ret.std() > 0 else np.nan
    mdd = frame["drawdown"].min()
    calmar = cagr / abs(mdd) if mdd < 0 else np.nan
    return {
        "누적수익률": (total - 1) * 100,
        "CAGR": cagr * 100,
        "연 변동성": vol * 100,
        "MDD": mdd * 100,
        "Sharpe": sharpe,
        "Calmar": calmar,
        "최종금액": total * INITIAL_CAPITAL,
    }


# ---------------------------------------------------------------- 왼쪽: 과정


def process_fig(frame: pd.DataFrame, label: str) -> go.Figure:
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.045,
        row_heights=[0.32, 0.18, 0.16, 0.34],
        subplot_titles=(
            "리밸런싱별 구성종목 비중 (%)",
            "HSI 상태 이력",
            "월별 Turnover (%)",
            "종목별 수익 기여도 (%)",
        ),
    )
    x = frame["date"]

    # 1) 비중 스택
    for code, (name, color) in ASSETS.items():
        fig.add_trace(
            go.Scatter(
                x=x,
                y=frame[f"weight_{code}"] * 100,
                name=name,
                stackgroup="w",
                mode="lines",
                line=dict(width=0.4, color=color),
                legendgroup=name,
            ),
            row=1,
            col=1,
        )

    # 2) HSI 상태 이력 (상태를 단계값으로)
    state_idx = frame["hsi_state"].map({s: i for i, s in enumerate(STATE_ORDER)}).fillna(0)
    fig.add_trace(
        go.Scatter(
            x=x,
            y=state_idx,
            mode="lines+markers",
            line=dict(shape="hv", color="#94a3b8", width=1),
            marker=dict(size=5, color=[STATE_COLOR.get(s, "#ccc") for s in frame["hsi_state"]]),
            customdata=frame["hsi_state"].map(STATE_KR),
            hovertemplate="%{x|%Y-%m}<br>상태: %{customdata}<extra></extra>",
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    fig.update_yaxes(
        tickvals=list(range(len(STATE_ORDER))),
        ticktext=[STATE_KR[s] for s in STATE_ORDER],
        tickfont=dict(size=9),
        row=2,
        col=1,
    )

    # 3) Turnover
    fig.add_trace(
        go.Bar(x=x, y=frame["turnover"] * 100, marker_color="#64748b", showlegend=False),
        row=3,
        col=1,
    )

    # 4) 종목별 수익 기여도 + 총합
    for code, (name, color) in ASSETS.items():
        contrib = frame[f"weight_{code}"] * frame[f"return_{code}"] * 100
        fig.add_trace(
            go.Bar(x=x, y=contrib, name=name, marker_color=color, legendgroup=name, showlegend=False),
            row=4,
            col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=frame["strategy_return"] * 100,
            name="전략 월수익률",
            mode="lines",
            line=dict(color="#111827", width=1),
        ),
        row=4,
        col=1,
    )

    fig.update_layout(
        barmode="relative",
        height=860,
        template="plotly_white",
        title=dict(text=f"{label} — OOS 리밸런싱별 비중 / HSI 상태 / 수익 기여도", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.08, font=dict(size=10)),
        margin=dict(l=10, r=10, t=70, b=10),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="비중 (%)", range=[0, 100], row=1, col=1)
    fig.update_yaxes(title_text="기여도 (%)", row=4, col=1)
    return fig


# ---------------------------------------------------------------- 오른쪽: 결과


def result_fig(frame: pd.DataFrame, bench: pd.DataFrame, label: str, metrics: dict[str, float]) -> go.Figure:
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.32, 0.18, 0.22, 0.28],
        specs=[[{}], [{}], [{}], [{"secondary_y": True}]],
        subplot_titles=(
            "누적수익 (초기 100)",
            "드로다운 (%)",
            "구성 비중 (%)",
            "Rolling 1년(12개월) 수익률·변동성·Sharpe",
        ),
    )
    x = frame["date"]

    # 1) 누적수익 vs 벤치마크
    fig.add_trace(
        go.Scatter(x=x, y=frame["cumulative_return"] * 100, name=label, line=dict(color="#1F77B4", width=1.8)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=bench["date"],
            y=bench["cumulative_return"] * 100,
            name="EW Buy&Hold",
            line=dict(color="#9ca3af", width=1.2, dash="dot"),
        ),
        row=1,
        col=1,
    )
    stats_text = (
        f"누적수익률 {metrics['누적수익률']:.1f}%<br>"
        f"CAGR {metrics['CAGR']:.2f}%<br>"
        f"연 변동성 {metrics['연 변동성']:.2f}%<br>"
        f"MDD {metrics['MDD']:.2f}%<br>"
        f"Sharpe {metrics['Sharpe']:.2f}<br>"
        f"Calmar {metrics['Calmar']:.2f}"
    )
    fig.add_annotation(
        xref="x domain",
        yref="y domain",
        x=0.02,
        y=0.98,
        text=stats_text,
        showarrow=False,
        align="left",
        font=dict(size=10),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#cbd5e1",
        borderwidth=1,
        row=1,
        col=1,
    )

    # 2) 드로다운
    fig.add_trace(
        go.Scatter(
            x=x,
            y=frame["drawdown"] * 100,
            name="드로다운",
            fill="tozeroy",
            line=dict(color="#C44E52", width=0.8),
            fillcolor="rgba(196,78,82,0.35)",
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # 3) 비중 스택
    for code, (name, color) in ASSETS.items():
        fig.add_trace(
            go.Scatter(
                x=x,
                y=frame[f"weight_{code}"] * 100,
                name=name,
                stackgroup="rw",
                mode="lines",
                line=dict(width=0.4, color=color),
                showlegend=False,
            ),
            row=3,
            col=1,
        )

    # 4) Rolling 12M
    ret = frame["strategy_return"]
    roll_ret = (1 + ret).rolling(12).apply(np.prod, raw=True) - 1
    roll_vol = ret.rolling(12).std() * np.sqrt(12)
    roll_sharpe = ret.rolling(12).mean() / ret.rolling(12).std() * np.sqrt(12)
    fig.add_trace(
        go.Scatter(x=x, y=roll_ret * 100, name="1Y 수익률 (%)", line=dict(color="#1F77B4", width=1.2)),
        row=4,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=x, y=roll_vol * 100, name="1Y 변동성 (%)", line=dict(color="#DD8452", width=1.2)),
        row=4,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=x, y=roll_sharpe, name="1Y Sharpe", line=dict(color="#55A868", width=1.2, dash="dash")),
        row=4,
        col=1,
        secondary_y=True,
    )

    fig.update_layout(
        height=860,
        template="plotly_white",
        title=dict(
            text=f"{label} 시뮬레이션 — 초기 {INITIAL_CAPITAL:,.0f} → 최종 {metrics['최종금액']:,.0f}",
            font=dict(size=15),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.08, font=dict(size=10)),
        margin=dict(l=10, r=10, t=70, b=10),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="지수", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)
    fig.update_yaxes(title_text="비중 (%)", range=[0, 100], row=3, col=1)
    fig.update_yaxes(title_text="%", row=4, col=1)
    fig.update_yaxes(title_text="Sharpe", row=4, col=1, secondary_y=True)
    return fig


# ---------------------------------------------------------------- λ 민감도


@st.cache_data
def load_lambda_family() -> tuple[pd.DataFrame, pd.Series]:
    """shortlist의 λ 지점(0.1/0.3/0.5/1.0) + 노트 문서의 λ=0.7을 합친 λ 패밀리 표."""
    sl = pd.read_csv(HSI_CANDIDATE_DATA_DIR / SHORTLIST_FILE)
    ew = sl[sl["strategy_name"] == "EW"].iloc[0]

    fam = sl[sl["lambda_value"].notna()][
        ["lambda_value", "CAGR_pct", "MDD_pct", "Sharpe", "Calmar", "months", "final_cumulative_return"]
    ].copy()
    fam["cumulative_pct"] = (fam["final_cumulative_return"] - 1) * 100

    row = dict(LAMBDA_07_ROW)
    months = int(fam["months"].iloc[0])
    row["cumulative_pct"] = ((1 + row["CAGR_pct"] / 100) ** (months / 12) - 1) * 100
    fam = pd.concat([fam, pd.DataFrame([row])], ignore_index=True)
    return fam.sort_values("lambda_value").reset_index(drop=True), ew


def lambda_sensitivity_fig(fam: pd.DataFrame, ew: pd.Series, metric_label: str) -> go.Figure:
    col, _ = LAMBDA_METRICS[metric_label]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=fam["lambda_value"],
            y=fam[col],
            mode="lines+markers+text",
            text=[f"{v:.2f}" for v in fam[col]],
            textposition="top center",
            textfont=dict(size=10),
            line=dict(color="#1F77B4", width=2),
            marker=dict(size=9),
            name=metric_label,
            hovertemplate="λ = %{x}<br>" + metric_label + " = %{y:.3f}<extra></extra>",
        )
    )
    ew_map = {
        "CAGR_pct": ew["CAGR_pct"],
        "cumulative_pct": (ew["final_cumulative_return"] - 1) * 100,
        "Sharpe": ew["Sharpe"],
        "MDD_pct": ew["MDD_pct"],
        "Calmar": ew["Calmar"],
    }
    fig.add_hline(
        y=ew_map[col],
        line=dict(color="#9ca3af", dash="dot", width=1.2),
        annotation_text=f"EW {ew_map[col]:.2f}",
        annotation_font_size=10,
    )
    best_idx = fam[col].idxmin() if col == "MDD_pct" else fam[col].idxmax()
    fig.add_trace(
        go.Scatter(
            x=[fam.loc[best_idx, "lambda_value"]],
            y=[fam.loc[best_idx, col]],
            mode="markers",
            marker=dict(size=15, color="rgba(85,168,104,0.4)", line=dict(color="#55A868", width=2)),
            name="최적점" if col != "MDD_pct" else "최저점",
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=380,
        title=dict(text=f"λ 민감도 — {metric_label}", font=dict(size=15)),
        xaxis=dict(title="λ (부분조정 계수)", tickvals=fam["lambda_value"].tolist()),
        yaxis=dict(title=metric_label),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, font=dict(size=10)),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


# ---------------------------------------------------------------- 페이지


def render() -> None:
    st.title("전략 상세 분석")
    st.caption("왼쪽은 전략이 어떻게 움직였는지(과정), 오른쪽은 얼마나 잘했는지(결과)를 보여줍니다.")

    df = load_timeseries()
    options = [s for s in STRATEGY_LABELS if s in df["strategy_name"].unique()]
    selected = st.selectbox(
        "분석할 전략",
        options,
        index=options.index(DEFAULT_STRATEGY) if DEFAULT_STRATEGY in options else 0,
        format_func=lambda s: STRATEGY_LABELS.get(s, s),
    )

    frame = strategy_frame(df, selected)
    bench = strategy_frame(df, BENCHMARK)
    if frame.empty:
        st.warning("선택한 전략의 데이터가 없습니다.")
        return

    label = STRATEGY_LABELS.get(selected, selected)
    metrics = compute_metrics(frame)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("누적수익률", f"{metrics['누적수익률']:.1f}%")
    c2.metric("CAGR", f"{metrics['CAGR']:.2f}%")
    c3.metric("MDD", f"{metrics['MDD']:.2f}%")
    c4.metric("Sharpe", f"{metrics['Sharpe']:.2f}")
    c5.metric("Calmar", f"{metrics['Calmar']:.2f}")

    left, right = st.columns(2)
    with left:
        st.plotly_chart(process_fig(frame, label), width="stretch")
    with right:
        st.plotly_chart(result_fig(frame, bench, label, metrics), width="stretch")

    if selected == "EW":
        st.info("EW는 동일가중 기준선이므로 HSI 상태 이력이 표시되지 않습니다.")

    st.divider()
    st.subheader("λ 민감도 분석")
    st.caption(
        "부분조정 계수 λ에 따른 성과 변화입니다. λ=0.7은 shortlist에 없어 "
        "docs/main_final_lambda_experiment_note.md의 성과 표 값을 사용했습니다."
    )
    fam, ew_row = load_lambda_family()
    metric_label = st.radio(
        "y축 지표",
        list(LAMBDA_METRICS),
        horizontal=True,
        label_visibility="collapsed",
    )
    st.plotly_chart(lambda_sensitivity_fig(fam, ew_row, metric_label), width="stretch")
    st.caption(f"해석 기준: {LAMBDA_METRICS[metric_label][1]}. 점선은 EW 기준선.")

    with st.expander("데이터 원본 보기"):
        st.dataframe(frame, width="stretch", height=320)
