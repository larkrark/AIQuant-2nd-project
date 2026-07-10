import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# 1. 현재까지의 모델 셀렉션 데이터
# ============================================================

def make_current_candidate_data() -> pd.DataFrame:
    """
    현재까지 공유된 HSI Overlay 실험 결과를 모델 셀렉션용 표로 정리한다.

    수치 출처:
    - EW, HSI baseline, Event filter, λ=0.3: 전략 비교 시각화 자료 기준
    - Lambda 0.1, Lambda 0.3 최종 후보표: 20·21·23번 후보 선별 보고서 기준

    주의:
    - Lambda 0.3은 시각화 요약표와 후보 선별표에서 약간 다른 값이 존재할 수 있으므로,
      최종 모델 셀렉션 점수 계산에는 후보 선별표 기준 값을 사용한다.
    """
    rows = [
        {
            "model_id": "EW Benchmark",
            "family": "benchmark",
            "stage": "current",
            "decision": "benchmark",
            "cagr": 6.51,
            "mdd": -13.57,
            "abs_mdd": 13.57,
            "sharpe": 0.832,
            "calmar": 0.480,
            "avg_turnover": 0.00,
            "max_turnover": 0.00,
            "cost_drag_20bp": 0.000,
            "hsi_relation": "HSI 상태 정보를 사용하지 않는 단순 동일비중 비교 기준입니다.",
            "interpretation": "Sharpe는 가장 높지만 HSI Overlay 구조를 사용하지 않는 benchmark입니다.",
            "source_note": "20·21·23 후보 선별표 기준",
        },
        {
            "model_id": "HSI baseline",
            "family": "hsi_baseline",
            "stage": "current",
            "decision": "baseline_reference",
            "cagr": 7.73,
            "mdd": -23.46,
            "abs_mdd": 23.46,
            "sharpe": 0.611,
            "calmar": 7.73 / 23.46,
            "avg_turnover": 22.09,
            "max_turnover": np.nan,
            "cost_drag_20bp": np.nan,
            "hsi_relation": "HSI 5상태를 ETF 목표비중에 즉시 연결한 기준선입니다.",
            "interpretation": "CAGR은 EW보다 높지만 MDD와 Turnover 부담이 커서 최종 후보보다는 기준선으로 해석합니다.",
            "source_note": "전략 비교 시각화 기준",
        },
        {
            "model_id": "Event filter",
            "family": "event_filter",
            "stage": "current",
            "decision": "diagnostic_candidate",
            "cagr": 7.14,
            "mdd": -23.04,
            "abs_mdd": 23.04,
            "sharpe": 0.600,
            "calmar": 7.14 / 23.04,
            "avg_turnover": 21.92,
            "max_turnover": np.nan,
            "cost_drag_20bp": np.nan,
            "hsi_relation": "HSI 상태를 대체하지 않고 사건균형지표를 보조 필터로 사용한 실험입니다.",
            "interpretation": "MDD를 소폭 개선했지만 Turnover 부담이 남아 최종 후보보다는 보조 진단 후보로 둡니다.",
            "source_note": "전략 비교 시각화 기준",
        },
        {
            "model_id": "Lambda 0.1",
            "family": "lambda",
            "stage": "current",
            "decision": "final_candidate",
            "cagr": 8.62,
            "mdd": -14.79,
            "abs_mdd": 14.79,
            "sharpe": 0.791,
            "calmar": 0.583,
            "avg_turnover": 2.52,
            "max_turnover": 6.02,
            "cost_drag_20bp": 0.065,
            "hsi_relation": "HSI 상태별 목표비중으로 매우 천천히 이동하는 λ 부분조정 후보입니다.",
            "interpretation": "저회전·보수형 후보입니다. 비용 훼손이 작고 Turnover 부담이 낮습니다.",
            "source_note": "20·21·23 후보 선별표 기준",
        },
        {
            "model_id": "Lambda 0.3",
            "family": "lambda",
            "stage": "current",
            "decision": "final_candidate",
            "cagr": 8.99,
            "mdd": -15.33,
            "abs_mdd": 15.33,
            "sharpe": 0.775,
            "calmar": 0.587,
            "avg_turnover": 6.95,
            "max_turnover": 20.01,
            "cost_drag_20bp": 0.181,
            "hsi_relation": "HSI 상태별 목표비중으로 천천히 이동하는 λ 부분조정 후보입니다.",
            "interpretation": "수익성과 방어력의 균형 후보입니다. Lambda 0.1보다 비용 부담은 크지만 CAGR과 Calmar가 높습니다.",
            "source_note": "20·21·23 후보 선별표 기준",
        },
    ]

    return pd.DataFrame(rows)


def make_future_experiment_data() -> pd.DataFrame:
    """
    후속 실험 슬롯.
    아직 성과 수치가 없으므로 모델 셀렉션 점수 계산에는 포함하지 않고,
    로드맵 그래프와 표에만 표시한다.
    """
    rows = [
        {
            "experiment_id": "14",
            "experiment_name": "Macro companion overlay",
            "purpose": "금리·환율·GDP 기반 macro companion을 HSI baseline 비중에 소폭 반영",
            "hsi_relation": "HSI 상태는 그대로 두고, macro_defense_addon으로 위험자산 비중만 작게 조정",
            "status": "next",
            "expected_output": "baseline vs macro overlay 성과 비교",
        },
        {
            "experiment_id": "15 후보",
            "experiment_name": "Regime robustness check",
            "purpose": "상승기·하락기·위험구간별 후보 성과 안정성 확인",
            "hsi_relation": "HSI 상태별로 Lambda 후보가 어느 구간에서 강하고 약한지 확인",
            "status": "idea",
            "expected_output": "상태별 CAGR, MDD, 승률, Turnover 표",
        },
        {
            "experiment_id": "16 후보",
            "experiment_name": "Turnover cap overlay",
            "purpose": "월별 Turnover 상한을 둔 경우 후보 성과가 안정되는지 확인",
            "hsi_relation": "HSI 상태 변화가 너무 잦을 때 실제 운용 가능성을 높이는 제한 장치",
            "status": "idea",
            "expected_output": "Turnover cap별 성과 민감도 표",
        },
    ]

    return pd.DataFrame(rows)


def make_decision_distribution_data() -> pd.DataFrame:
    """
    20번 최종 후보 선별 결과.
    """
    return pd.DataFrame(
        [
            {"decision": "exclude_turnover", "count": 15},
            {"decision": "benchmark", "count": 5},
            {"decision": "final_candidate", "count": 2},
            {"decision": "exclude_risk_metric", "count": 1},
        ]
    )


# ============================================================
# 2. 점수 계산
# ============================================================

def normalize_metric(s: pd.Series, higher_is_better: bool = True) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")

    if s.notna().sum() <= 1:
        return pd.Series(0.5, index=s.index)

    min_v = s.min(skipna=True)
    max_v = s.max(skipna=True)

    if pd.isna(min_v) or pd.isna(max_v) or max_v == min_v:
        return pd.Series(0.5, index=s.index)

    score = (s - min_v) / (max_v - min_v)

    if not higher_is_better:
        score = 1 - score

    return score.fillna(0.0)


def calculate_model_score(
    df: pd.DataFrame,
    w_cagr: float,
    w_mdd: float,
    w_sharpe: float,
    w_calmar: float,
    w_turnover: float,
    w_cost: float,
) -> pd.DataFrame:
    out = df.copy()

    out["score_cagr"] = normalize_metric(out["cagr"], higher_is_better=True)
    out["score_mdd"] = normalize_metric(out["abs_mdd"], higher_is_better=False)
    out["score_sharpe"] = normalize_metric(out["sharpe"], higher_is_better=True)
    out["score_calmar"] = normalize_metric(out["calmar"], higher_is_better=True)
    out["score_turnover"] = normalize_metric(out["avg_turnover"], higher_is_better=False)

    # cost_drag_20bp가 없는 baseline/event filter는 비교 불완전하므로 0점 처리
    out["score_cost"] = normalize_metric(out["cost_drag_20bp"], higher_is_better=False)

    total_weight = w_cagr + w_mdd + w_sharpe + w_calmar + w_turnover + w_cost

    if total_weight == 0:
        out["selection_score"] = 0.0
    else:
        out["selection_score"] = (
            out["score_cagr"] * w_cagr
            + out["score_mdd"] * w_mdd
            + out["score_sharpe"] * w_sharpe
            + out["score_calmar"] * w_calmar
            + out["score_turnover"] * w_turnover
            + out["score_cost"] * w_cost
        ) / total_weight

    out["selection_score"] = out["selection_score"].round(4)

    return out.sort_values("selection_score", ascending=False).reset_index(drop=True)


# ============================================================
# 3. Plotly 그래프
# ============================================================

def build_risk_return_scatter(scored_df: pd.DataFrame) -> go.Figure:
    df = scored_df.copy()

    color_map = {
        "benchmark": "#7A7A7A",
        "baseline_reference": "#0B3A75",
        "diagnostic_candidate": "#20A39E",
        "final_candidate": "#F28E2B",
    }

    fig = go.Figure()

    for decision, sub in df.groupby("decision"):
        marker_size = 16 + sub["avg_turnover"].fillna(0) * 0.7
        marker_size = marker_size.clip(lower=14, upper=34)

        fig.add_trace(
            go.Scatter(
                x=sub["abs_mdd"],
                y=sub["cagr"],
                mode="markers+text",
                name=decision,
                text=sub["model_id"],
                textposition="top center",
                marker=dict(
                    size=marker_size,
                    color=color_map.get(decision, "#999999"),
                    opacity=0.88,
                    line=dict(color="white", width=1.5),
                ),
                selected=dict(
                    marker=dict(
                        opacity=1.0,
                        line=dict(color="rgba(255,255,255,1)", width=4),
                    )
                ),
                unselected=dict(
                    marker=dict(opacity=0.35)
                ),
                customdata=sub[
                    [
                        "model_id",
                        "decision",
                        "sharpe",
                        "calmar",
                        "avg_turnover",
                        "cost_drag_20bp",
                        "selection_score",
                        "hsi_relation",
                        "interpretation",
                    ]
                ].to_numpy(),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br><br>"
                    "CAGR: <b>%{y:.2f}%</b><br>"
                    "절대 MDD: <b>%{x:.2f}%</b><br>"
                    "Sharpe: %{customdata[2]:.3f}<br>"
                    "Calmar: %{customdata[3]:.3f}<br>"
                    "평균 Turnover: %{customdata[4]:.2f}%<br>"
                    "20bp 비용 훼손: %{customdata[5]:.3f}%p<br>"
                    "동적 선택 점수: <b>%{customdata[6]:.4f}</b><br><br>"
                    "<b>HSI와의 관계</b><br>%{customdata[7]}<br><br>"
                    "<b>해석</b><br>%{customdata[8]}"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(
            text="<b>모델 셀렉션 후보맵: CAGR vs MDD</b><br>"
                 "<sup>점의 크기는 평균 Turnover를 반영합니다. 커서를 올리면 HSI와의 관계가 표시됩니다.</sup>",
            x=0.0,
            xanchor="left",
        ),
        height=560,
        margin=dict(l=30, r=30, t=90, b=50),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, Arial, sans-serif", size=13),
        xaxis=dict(
            title="절대 MDD (%) - 낮을수록 안정적",
            gridcolor="rgba(150,150,150,0.25)",
            zeroline=False,
        ),
        yaxis=dict(
            title="CAGR (%) - 높을수록 수익성 우수",
            gridcolor="rgba(150,150,150,0.25)",
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.22,
            xanchor="center",
            x=0.5,
            title_text="",
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Malgun Gothic, Apple SD Gothic Neo, Arial, sans-serif",
        ),
    )

    return fig


def build_score_bar(scored_df: pd.DataFrame) -> go.Figure:
    df = scored_df.sort_values("selection_score", ascending=True).copy()

    fig = go.Figure(
        go.Bar(
            x=df["selection_score"],
            y=df["model_id"],
            orientation="h",
            marker=dict(
                color=np.where(df["decision"] == "final_candidate", "#F28E2B", "#4E79A7"),
                line=dict(color="white", width=1.5),
            ),
            customdata=df[
                [
                    "model_id",
                    "decision",
                    "cagr",
                    "abs_mdd",
                    "sharpe",
                    "calmar",
                    "avg_turnover",
                    "cost_drag_20bp",
                    "interpretation",
                ]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br><br>"
                "동적 선택 점수: <b>%{x:.4f}</b><br>"
                "판정: %{customdata[1]}<br>"
                "CAGR: %{customdata[2]:.2f}%<br>"
                "절대 MDD: %{customdata[3]:.2f}%<br>"
                "Sharpe: %{customdata[4]:.3f}<br>"
                "Calmar: %{customdata[5]:.3f}<br>"
                "평균 Turnover: %{customdata[6]:.2f}%<br>"
                "20bp 비용 훼손: %{customdata[7]:.3f}%p<br><br>"
                "%{customdata[8]}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>가중치 기반 동적 모델 선택 점수</b><br>"
                 "<sup>좌측 슬라이더의 가중치에 따라 점수가 다시 계산됩니다.</sup>",
            x=0.0,
            xanchor="left",
        ),
        height=440,
        margin=dict(l=30, r=30, t=90, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, Arial, sans-serif", size=13),
        xaxis=dict(
            title="선택 점수",
            range=[0, 1.05],
            gridcolor="rgba(150,150,150,0.25)",
            zeroline=False,
        ),
        yaxis=dict(title=""),
        hoverlabel=dict(bgcolor="white"),
    )

    return fig


def build_metric_comparison_bar(scored_df: pd.DataFrame, selected_models: list[str]) -> go.Figure:
    if not selected_models:
        selected_models = ["EW Benchmark", "Lambda 0.1", "Lambda 0.3"]

    df = scored_df[scored_df["model_id"].isin(selected_models)].copy()

    fig = go.Figure()

    metrics = [
        ("cagr", "CAGR (%)"),
        ("abs_mdd", "절대 MDD (%)"),
        ("avg_turnover", "평균 Turnover (%)"),
        ("cost_drag_20bp", "20bp 비용 훼손 (%p)"),
    ]

    for col, label in metrics:
        fig.add_trace(
            go.Bar(
                name=label,
                x=df["model_id"],
                y=df[col],
                customdata=df[["model_id", "interpretation"]].to_numpy(),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    f"{label}: " + "%{y:.3f}<br><br>"
                    "%{customdata[1]}"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(
            text="<b>선택 후보 핵심 지표 비교</b>",
            x=0.0,
            xanchor="left",
        ),
        barmode="group",
        height=430,
        margin=dict(l=30, r=30, t=70, b=50),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, Arial, sans-serif", size=13),
        yaxis=dict(title="값", gridcolor="rgba(150,150,150,0.25)", zeroline=False),
        xaxis=dict(title=""),
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
        hoverlabel=dict(bgcolor="white"),
    )

    return fig


def build_decision_donut(decision_df: pd.DataFrame) -> go.Figure:
    total = int(decision_df["count"].sum())

    fig = go.Figure(
        go.Pie(
            labels=decision_df["decision"],
            values=decision_df["count"],
            hole=0.55,
            textinfo="label+percent",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "개수: %{value}<br>"
                "비중: %{percent}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>후보 판단 분포</b><br>"
                 f"<sup>전체 후보 {total}개 중 최종 후보는 2개입니다.</sup>",
            x=0.0,
            xanchor="left",
        ),
        annotations=[
            dict(
                text=f"전체<br>{total}",
                x=0.5,
                y=0.5,
                font_size=18,
                showarrow=False,
            )
        ],
        height=430,
        margin=dict(l=30, r=30, t=90, b=30),
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, Arial, sans-serif", size=13),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
        hoverlabel=dict(bgcolor="white"),
    )

    return fig


def build_future_roadmap(future_df: pd.DataFrame) -> go.Figure:
    status_order = {"next": 2, "idea": 1}
    df = future_df.copy()
    df["priority"] = df["status"].map(status_order).fillna(0)

    fig = go.Figure(
        go.Bar(
            x=df["priority"],
            y=df["experiment_name"],
            orientation="h",
            marker=dict(
                color=np.where(df["status"] == "next", "#6BCB77", "#A0A0A0"),
                line=dict(color="white", width=1.5),
            ),
            customdata=df[
                ["experiment_id", "purpose", "hsi_relation", "expected_output", "status"]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br><br>"
                "실험 번호: %{customdata[0]}<br>"
                "상태: %{customdata[4]}<br><br>"
                "<b>연구목적</b><br>%{customdata[1]}<br><br>"
                "<b>HSI와의 관계</b><br>%{customdata[2]}<br><br>"
                "<b>예상 산출물</b><br>%{customdata[3]}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>후속 실험 로드맵</b><br>"
                 "<sup>14번은 바로 다음 실험, 나머지는 추가 확장 후보입니다.</sup>",
            x=0.0,
            xanchor="left",
        ),
        height=360,
        margin=dict(l=30, r=30, t=90, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, Arial, sans-serif", size=13),
        xaxis=dict(
            title="우선순위",
            showticklabels=False,
            gridcolor="rgba(150,150,150,0.25)",
            zeroline=False,
        ),
        yaxis=dict(title="", automargin=True),
        hoverlabel=dict(bgcolor="white"),
        showlegend=False,
    )

    return fig


# ============================================================
# 4. Streamlit 렌더링
# ============================================================

def render_model_selection_dynamic() -> None:
    st.header("동적 모델 셀렉션 보드")
    st.caption(
        "현재까지의 HSI Overlay 후보를 CAGR, MDD, Sharpe, Calmar, Turnover, 거래비용 민감도로 비교합니다. "
        "가중치를 바꾸면 모델 선택 점수가 동적으로 바뀝니다."
    )

    current_df = make_current_candidate_data()
    future_df = make_future_experiment_data()
    decision_df = make_decision_distribution_data()

    st.sidebar.markdown("## 모델 선택 가중치")
    st.sidebar.caption("높게 둘수록 해당 기준을 더 중요하게 반영합니다.")

    w_cagr = st.sidebar.slider("CAGR 중요도", 0.0, 5.0, 2.0, 0.5)
    w_mdd = st.sidebar.slider("MDD 안정성 중요도", 0.0, 5.0, 3.0, 0.5)
    w_sharpe = st.sidebar.slider("Sharpe 중요도", 0.0, 5.0, 1.5, 0.5)
    w_calmar = st.sidebar.slider("Calmar 중요도", 0.0, 5.0, 2.5, 0.5)
    w_turnover = st.sidebar.slider("Turnover 억제 중요도", 0.0, 5.0, 3.0, 0.5)
    w_cost = st.sidebar.slider("거래비용 민감도 중요도", 0.0, 5.0, 2.0, 0.5)

    scored_df = calculate_model_score(
        current_df,
        w_cagr=w_cagr,
        w_mdd=w_mdd,
        w_sharpe=w_sharpe,
        w_calmar=w_calmar,
        w_turnover=w_turnover,
        w_cost=w_cost,
    )

    top_model = scored_df.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재 1순위", top_model["model_id"])
    col2.metric("선택 점수", f"{top_model['selection_score']:.4f}")
    col3.metric("CAGR", f"{top_model['cagr']:.2f}%")
    col4.metric("평균 Turnover", f"{top_model['avg_turnover']:.2f}%")

    st.info(
        "주의: 이 점수는 최종 확정값이 아니라, 현재까지의 후보를 비교하기 위한 동적 의사결정 보드입니다. "
        "후속 14번 macro overlay 결과가 나오면 같은 표에 새 후보로 추가해 다시 비교합니다."
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "후보맵",
            "동적 점수",
            "후보 판단 분포",
            "후속 실험",
        ]
    )

    with tab1:
        fig_scatter = build_risk_return_scatter(scored_df)

        try:
            selected = st.plotly_chart(
                fig_scatter,
                use_container_width=True,
                on_select="rerun",
                selection_mode="points",
                key="model_selection_scatter",
            )
        except TypeError:
            st.plotly_chart(
                fig_scatter,
                use_container_width=True,
                key="model_selection_scatter_fallback",
            )
            selected = None

        selected_model = None

        if selected is not None:
            try:
                points = selected.selection.points
                if points:
                    selected_model = points[0].get("customdata", [None])[0]
            except Exception:
                selected_model = None

        if selected_model:
            row = scored_df[scored_df["model_id"] == selected_model].iloc[0]

            st.success(f"선택한 후보: {row['model_id']}")
            st.markdown("**HSI와의 관계**")
            st.write(row["hsi_relation"])
            st.markdown("**현재 해석**")
            st.write(row["interpretation"])

        selected_models = st.multiselect(
            "비교할 후보를 선택하세요.",
            options=scored_df["model_id"].tolist(),
            default=["EW Benchmark", "Lambda 0.1", "Lambda 0.3"],
        )

        st.plotly_chart(
            build_metric_comparison_bar(scored_df, selected_models),
            use_container_width=True,
        )

    with tab2:
        st.plotly_chart(
            build_score_bar(scored_df),
            use_container_width=True,
        )

        show_cols = [
            "model_id",
            "decision",
            "selection_score",
            "cagr",
            "mdd",
            "sharpe",
            "calmar",
            "avg_turnover",
            "max_turnover",
            "cost_drag_20bp",
            "source_note",
        ]

        st.dataframe(
            scored_df[show_cols],
            use_container_width=True,
            hide_index=True,
        )

    with tab3:
        st.plotly_chart(
            build_decision_donut(decision_df),
            use_container_width=True,
        )

        st.markdown(
            """
**해석:** 전체 후보 중 다수가 Turnover 기준에서 제외되었습니다.  
따라서 현재 모델 셀렉션의 핵심은 단순히 수익률이 높은 후보를 고르는 것이 아니라,  
HSI 상태 변화가 실제 ETF 비중 변화로 이어질 때 **회전율과 비용을 감당할 수 있는지**를 함께 보는 것입니다.
            """
        )

        st.dataframe(
            decision_df,
            use_container_width=True,
            hide_index=True,
        )

    with tab4:
        st.plotly_chart(
            build_future_roadmap(future_df),
            use_container_width=True,
        )

        st.markdown(
            """
### 다음 해석 방향

현재까지는 **Lambda 0.1**과 **Lambda 0.3**이 후보로 남아 있습니다.  
하지만 우리 쪽에 남은 14번 실험에서는 금리·환율·GDP 기반 `macro companion`을 이용해  
기존 HSI baseline 또는 Lambda 후보 위에 소폭 방어 보정을 얹을 수 있습니다.

즉, 다음 비교 구조는 이렇게 됩니다.

```text
EW Benchmark
vs HSI baseline
vs Lambda 0.1
vs Lambda 0.3
vs Macro companion overlay```
"""
        )

