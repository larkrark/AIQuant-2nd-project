"""
대시보드 페이지: 팩터 로딩 · 성과 기여도.

output/tables 의 stage_factor/stage_attribution 산출물이 있으면 그것을,
없으면 데모(합성) 데이터로 차트 레이아웃을 미리보기한다.
차트 로직은 dashboard.factor_charts(순수/plotly)로 분리.

[2026-07-08 추가] HSI 방향(①) vs 변동성 기반 λ(②) 기여 분리(Ablation) 탭.
근거: docs/섹션C_HSI_람다_기여분리_ablation_보고서이식본_2026-07-08.md
데이터: output/tables/main_v2_{monthly,daily}_ablation_hsi_vs_lambda.csv
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import factor_charts as fc
from dashboard.paths import LEGACY_TABLE_DIR

FILES = {
    "loading_summary": "factor_loading_summary.csv",
    "rolling_ts": "factor_loading_timeseries.csv",
    "attr_summary": "attribution_summary.csv",
    "attr_cumulative": "attribution_cumulative.csv",
}

ABLATION_FILES = {
    "월별 (본 수치, 2014-04~2026-06)": "main_v2_monthly_ablation_hsi_vs_lambda.csv",
    "일별 (검증용)": "main_v2_daily_ablation_hsi_vs_lambda.csv",
}

ARM_COLORS = {
    "A": "#9aa3ad",
    "B": "#c3c7cd",
    "E": "#DD8452",
    "C": "#55A868",
    "D": "#4C9F70",
    "F": "#1F77B4",
}


def _load_real() -> dict | None:
    """실제 산출물이 모두 있으면 로드, 아니면 None."""
    data = {}
    for key, fname in FILES.items():
        p = LEGACY_TABLE_DIR / fname
        if not p.exists():
            return None
        df = pd.read_csv(p, encoding="utf-8-sig")
        for c in ("Date",):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c])
        data[key] = df
    # VIF는 선택적(있으면 로드)
    vif_p = LEGACY_TABLE_DIR / "factor_vif.csv"
    if vif_p.exists():
        data["vif"] = pd.read_csv(vif_p, encoding="utf-8-sig")
    # v2 대안 분해(HSI 평균비중 앵커)는 선택적(있으면 로드)
    for key, fname in [("attr_summary_v2", "attribution_summary_v2.csv"),
                       ("attr_cumulative_v2", "attribution_cumulative_v2.csv")]:
        p = LEGACY_TABLE_DIR / fname
        if p.exists():
            df = pd.read_csv(p, encoding="utf-8-sig")
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
            data[key] = df
    return data


# ---------------------------------------------------------------- Ablation


@st.cache_data
def _load_ablation(fname: str) -> pd.DataFrame | None:
    p = LEGACY_TABLE_DIR / fname
    if not p.exists():
        return None
    df = pd.read_csv(p, encoding="utf-8-sig")
    df["arm_key"] = df["arm"].str.strip().str[0]
    return df


def _arm_value(df: pd.DataFrame, key: str, col: str) -> float:
    return float(df.loc[df["arm_key"] == key, col].iloc[0])


def _ablation_mdd_calmar_fig(df: pd.DataFrame) -> go.Figure:
    order = [k for k in ["A", "B", "E", "C", "D", "F"] if k in set(df["arm_key"])]
    d = df.set_index("arm_key").loc[order].reset_index()
    colors = [ARM_COLORS.get(k, "#888") for k in d["arm_key"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=d["arm"],
            y=d["MDD_pct"],
            name="MDD (%)",
            marker_color=colors,
            text=[f"{v:.1f}" for v in d["MDD_pct"]],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=d["arm"],
            y=d["Calmar"],
            name="Calmar",
            yaxis="y2",
            mode="lines+markers+text",
            text=[f"{v:.2f}" for v in d["Calmar"]],
            textposition="top center",
            textfont=dict(size=10),
            line=dict(color="#111827", width=1.5),
            marker=dict(size=8),
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=430,
        title=dict(text="Ablation — MDD(막대, 좌축) · Calmar(선, 우축)", font=dict(size=14)),
        yaxis=dict(title="MDD (%)"),
        yaxis2=dict(title="Calmar", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=10, r=10, t=70, b=10),
        xaxis=dict(tickfont=dict(size=10)),
    )
    return fig


def _render_ablation_tab() -> None:
    st.markdown("#### HSI 방향(①) vs 변동성 기반 λ(②) — 기여 분리 실험")
    st.caption(
        "발표 질의 \"HSI 없이 변동성만 봐도 되지 않나?\"에 답하는 ablation. "
        "①과 ②를 껐다 켜며 6개 후보(arm)를 비교합니다. "
        "출처: docs/섹션C_HSI_람다_기여분리_ablation_보고서이식본_2026-07-08.md"
    )

    freq = st.radio("기준", list(ABLATION_FILES), horizontal=True, label_visibility="collapsed")
    df = _load_ablation(ABLATION_FILES[freq])
    if df is None:
        st.warning(f"output/tables/{ABLATION_FILES[freq]} 를 찾을 수 없습니다. src/34·35 스크립트를 먼저 실행하세요.")
        return

    have = set(df["arm_key"])
    if {"F", "E", "C"} <= have:
        mdd_hsi = _arm_value(df, "F", "MDD_pct") - _arm_value(df, "E", "MDD_pct")
        mdd_lam = _arm_value(df, "F", "MDD_pct") - _arm_value(df, "C", "MDD_pct")
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "① HSI 방향 기여 (F−E, MDD)",
            f"{mdd_hsi:+.1f}%p",
            help="풀버전(F)과 HSI 없이 vol 방어만 한 후보(E)의 MDD 차이. 양수 = HSI가 낙폭을 그만큼 더 통제.",
        )
        c2.metric(
            "② 동적 λ 기여 (F−C, MDD)",
            f"{mdd_lam:+.1f}%p",
            help="풀버전(F)과 HSI+고정 λ0.3(C)의 MDD 차이. 동적 λ의 한계 기여.",
        )
        c3.metric("결론", "① 이 주동력", help="낙폭 통제의 주된 동력은 HSI 방향이며, 동적 λ는 부가적 정교화.")

    st.plotly_chart(_ablation_mdd_calmar_fig(df), use_container_width=True)

    show = df.drop(columns=["arm_key"]).copy()
    num_cols = [c for c in show.columns if c != "arm" and c != "months"]
    st.dataframe(
        show.style.format({c: "{:.2f}" for c in num_cols}),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "A·B: 기준선(HSI×, 방어×) / E: 변동성·drawdown만으로 방어(②만) / "
        "C·D: HSI + 고정 λ(①만) / F: dynamic_v1 풀버전(①+②). "
        "월별 수치는 일별 가격에서 복원한 월수익률 기준 — 정본 monthly_returns.csv 확보 시 재산출 권장."
    )


def render() -> None:
    st.title("팩터 로딩 · 성과 기여도")
    st.caption("RA 요구사항: 팩터 분석/로딩 + 성과 기여도(attribution)")

    real = _load_real()
    if real is None:
        st.info(
            "아직 stage_factor / stage_attribution 산출물(output/tables)이 없습니다. "
            "팩터 데이터 인제스트 후 파이프라인을 실행하면 실제 값으로 채워집니다. "
            "아래는 **데모(합성) 미리보기**로, 차트 구성과 해석 방식을 보여줍니다."
        )
        data = fc.demo_bundle()
        data.setdefault("vif", None)
    else:
        data = real
        data.setdefault("vif", None)

    tabs = st.tabs(["팩터 로딩", "Rolling 노출", "상관·VIF", "성과 기여도", "HSI vs λ 분리(Ablation)"])

    with tabs[0]:
        st.plotly_chart(fc.factor_loading_heatmap_fig(data["loading_summary"]), use_container_width=True)
        st.caption("β>0: 해당 팩터에 양의 노출. alpha 행은 팩터로 설명되지 않는 초과수익.")
        st.dataframe(data["loading_summary"], use_container_width=True, hide_index=True)

    with tabs[1]:
        factors = fc.rolling_factor_columns(data["rolling_ts"])
        if factors:
            sel = st.selectbox("팩터 선택", factors, index=0)
            st.plotly_chart(fc.rolling_exposure_fig(data["rolling_ts"], sel), use_container_width=True)
            st.caption("36개월 rolling 회귀 β. 시간에 따른 노출 변화를 본다.")
        else:
            st.warning("rolling 시계열에 팩터 컬럼(_beta)이 없습니다.")

    with tabs[2]:
        if data.get("vif") is not None:
            st.plotly_chart(fc.vif_bar_fig(data["vif"]), use_container_width=True)
            st.caption("VIF가 임계(기본 5)를 넘으면 다중공선성 → 중복 팩터 제거 검토(팀검토 반영).")
        else:
            st.info("VIF 표(factor_vif.csv)가 없어 생략했습니다. screen_factors로 생성할 수 있습니다.")

    with tabs[3]:
        has_v2 = "attr_summary_v2" in data and "attr_cumulative_v2" in data
        if has_v2:
            ver = st.radio(
                "분해 기준",
                ["v1 — 70/20/10 앵커 (SAA·상태 타이밍)", "v2 — HSI 평균비중 앵커 (익스포저·순수 타이밍)"],
                horizontal=True,
            )
            use_v2 = ver.startswith("v2")
        else:
            use_v2 = False
            st.caption("v2 대안 분해 테이블(attribution_summary_v2.csv)이 없어 v1만 표시합니다. data_bridge 재실행 시 생성됩니다.")
        summary = data["attr_summary_v2"] if use_v2 else data["attr_summary"]
        cumulative = data["attr_cumulative_v2"] if use_v2 else data["attr_cumulative"]
        st.plotly_chart(fc.attribution_waterfall_fig(summary), use_container_width=True)
        if use_v2:
            st.caption(
                "EW 대비 초과수익 = 익스포저(HSI 평균 방어비중) + 순수 타이밍(공분산) + λ smoothing + 비용. "
                "70/20/10 앵커가 만들던 'SAA↑/타이밍↓' 상쇄 착시를 제거한 분해 — 셔플 검정과 일관된 구조."
            )
        else:
            st.caption(
                "EW 대비 초과수익 = SAA + 타이밍 + λ smoothing + 비용 (가법 분해). "
                "주의: '상태 타이밍'에는 70/20/10 대비 평균 비중 격차(익스포저)가 포함됨 — v2 참고."
            )
        st.plotly_chart(fc.attribution_cumulative_fig(cumulative), use_container_width=True)
        st.dataframe(summary, use_container_width=True, hide_index=True)

    with tabs[4]:
        _render_ablation_tab()
