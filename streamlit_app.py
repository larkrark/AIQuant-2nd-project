from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
TABLE_DIR = ROOT / "output" / "tables"
FIGURE_DIR = ROOT / "output" / "figures"

STATE_COLORS = {
    "강한 위험악화": "#c2410c",
    "위험악화": "#ef4444",
    "고변동성 혼합구간": "#f59e0b",
    "불안정 과열": "#d946ef",
    "과열 후보": "#8b5cf6",
    "중립/혼조": "#64748b",
    "회복 후보": "#22c55e",
    "안정적 회복 후보": "#0f766e",
}

CORE_FIGURES = [
    (
        "HSI 상태 점수와 사건 주석",
        "fig14_hsi_state_score_with_event_annotations.png",
        "주요 사건 구간에서 위험악화·과열·회복 점수가 어떻게 움직였는지 확인한다.",
    ),
    (
        "P파/S파 사건 압력과 사건 주석",
        "fig13_p_s_wave_with_event_annotations.png",
        "위험 신호와 회복·과열 신호가 동시에 존재하는 구조를 설명한다.",
    ),
    (
        "고변동성 혼합구간과 사건 주석",
        "fig15_mixed_zone_with_event_annotations.png",
        "단순 중립이 아니라 양방향 충격이 섞인 구간을 보여준다.",
    ),
    (
        "HSI 상태명 분포",
        "fig12_hsi_state_distribution.png",
        "전체 기간에서 각 상태명이 얼마나 자주 나타났는지 요약한다.",
    ),
]

SUPPORT_FIGURES = [
    ("P파/S파 사건 압력", "fig09_p_s_wave_event_pressure.png"),
    ("양방향 충격과 고변동성 혼합구간", "fig10_two_sided_shock_mixed_zone.png"),
    ("HSI 상태 점수 추이", "fig11_hsi_state_score_trend.png"),
]


st.set_page_config(
    page_title="AIQuant HSI Dashboard",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
    [data-testid="stMetricValue"] { font-size: 1.45rem; }
    [data-testid="stMetricLabel"] { color: #475569; }
    .section-note {
        border-left: 4px solid #2563eb;
        padding: 0.55rem 0.8rem;
        background: #eff6ff;
        color: #1e3a8a;
        margin: 0.35rem 0 1rem 0;
        border-radius: 0 6px 6px 0;
    }
    .small-caption { color: #64748b; font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_csv(filename: str) -> pd.DataFrame:
    path = TABLE_DIR / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def percent(series: pd.Series) -> pd.Series:
    return (series.astype(float) * 100).round(1)


def format_share_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["Share", "TopStateShare", "SecondStateShare"]:
        if col in out.columns:
            out[col] = percent(out[col]).astype(str) + "%"
    return out


def show_image(title: str, filename: str, caption: str | None = None) -> None:
    path = FIGURE_DIR / filename
    st.subheader(title)
    if path.exists():
        st.image(str(path), use_container_width=True)
        if caption:
            st.markdown(f"<div class='small-caption'>{caption}</div>", unsafe_allow_html=True)
    else:
        st.warning(f"그림 파일을 찾을 수 없습니다: {path}")


def make_state_chart(df: pd.DataFrame, value_col: str = "Count") -> None:
    if df.empty or "HSIStateLabel" not in df.columns or value_col not in df.columns:
        st.info("표시할 상태 분포 데이터가 없습니다.")
        return
    chart_df = df[["HSIStateLabel", value_col]].copy()
    chart_df[value_col] = pd.to_numeric(chart_df[value_col], errors="coerce").fillna(0)
    chart_df = chart_df.sort_values(value_col, ascending=False).set_index("HSIStateLabel")
    st.bar_chart(chart_df, color="#2563eb")


monthly_summary = load_csv("monthly_hsi_state_summary.csv")
event_summary = load_csv("event_hsi_interpretation_summary.csv")
event_distribution = load_csv("event_period_state_distribution.csv")
validation_state = load_csv("design_validation_state_summary.csv")
validation_wave = load_csv("design_validation_wave_summary.csv")

st.title("AIQuant HSI 시각화 대시보드")
st.caption("HSI 기반 ETF 자산배분 프로젝트의 발표용 결과와 검증 흐름")

with st.sidebar:
    st.header("필터")
    markets = sorted(event_summary["Market"].dropna().unique()) if "Market" in event_summary else []
    selected_markets = st.multiselect("시장", markets, default=markets)

    event_types = sorted(event_summary["EventType"].dropna().unique()) if "EventType" in event_summary else []
    selected_event_types = st.multiselect("사건 유형", event_types, default=event_types)

    states = sorted(monthly_summary["HSIStateLabel"].dropna().unique()) if "HSIStateLabel" in monthly_summary else []
    selected_states = st.multiselect("HSI 상태", states, default=states)

filtered_events = event_summary.copy()
if not filtered_events.empty:
    if selected_markets:
        filtered_events = filtered_events[filtered_events["Market"].isin(selected_markets)]
    if selected_event_types:
        filtered_events = filtered_events[filtered_events["EventType"].isin(selected_event_types)]

filtered_monthly = monthly_summary.copy()
if not filtered_monthly.empty and selected_states:
    filtered_monthly = filtered_monthly[filtered_monthly["HSIStateLabel"].isin(selected_states)]

total_state_count = int(monthly_summary["Count"].sum()) if "Count" in monthly_summary else 0
top_state = monthly_summary.iloc[0]["HSIStateLabel"] if not monthly_summary.empty else "-"
event_count = len(event_summary)
figure_count = sum((FIGURE_DIR / filename).exists() for _, filename, *_ in CORE_FIGURES)

metric_cols = st.columns(4)
metric_cols[0].metric("상태 관측치", f"{total_state_count:,}")
metric_cols[1].metric("최다 상태", top_state)
metric_cols[2].metric("사건 구간", f"{event_count:,}")
metric_cols[3].metric("핵심 그래프", f"{figure_count}/{len(CORE_FIGURES)}")

tabs = st.tabs(["개요", "사건 구간", "상태 분포", "설계/검증", "그래프 갤러리"])

with tabs[0]:
    st.markdown("<div class='section-note'>HSI는 기존 자산배분 전략을 대체하는 전략이 아니라, 시장상태 해석과 위험자산 비중 조절을 돕는 market timing 보조지표로 둔다.</div>", unsafe_allow_html=True)

    left, right = st.columns([1.1, 0.9])
    with left:
        st.subheader("발표 스토리라인")
        st.write(
            pd.DataFrame(
                [
                    ("1", "문제의식", "기존 전략만으로는 충돌하는 시장 신호를 설명하기 어렵다."),
                    ("2", "HSI 아이디어", "가격 기반 신호의 방향·강도·충돌도를 상태명으로 요약한다."),
                    ("3", "데이터", "한국 상장 ETF 가격 데이터와 주요 사건 구간을 사용한다."),
                    ("4", "실험설계", "입력 신호를 만들고 HSI 상태를 분류한 뒤 기간별 안정성을 확인한다."),
                    ("5", "결과 검증", "사건 구간 해석에서 출발해 백테스트 성과 검증으로 확장한다."),
                ],
                columns=["순서", "파트", "핵심 메시지"],
            )
        )
    with right:
        st.subheader("현재 발표 포지션")
        st.write(
            pd.DataFrame(
                [
                    ("완료", "HSI 상태 점수·사건 주석 그래프"),
                    ("완료", "사건 구간별 HSI 해석 요약표"),
                    ("완료", "설계/검증 기간 상태 분포"),
                    ("후속", "누적수익률·Drawdown 백테스트 그래프"),
                    ("후속", "HSI 적용 전후 리밸런싱 비중 변화"),
                ],
                columns=["상태", "산출물"],
            )
        )

    show_image(*CORE_FIGURES[0])

with tabs[1]:
    st.subheader("사건 구간별 HSI 해석")
    if filtered_events.empty:
        st.info("선택한 필터에 해당하는 사건 구간이 없습니다.")
    else:
        display_cols = [
            "Market",
            "EventName",
            "EventType",
            "StartMonth",
            "EndMonth",
            "TopState",
            "TopStateShare",
            "SecondState",
            "SecondStateShare",
            "Interpretation",
        ]
        display_cols = [col for col in display_cols if col in filtered_events.columns]
        st.dataframe(format_share_columns(filtered_events[display_cols]), use_container_width=True, hide_index=True)

    st.subheader("사건별 상태 분포")
    if event_distribution.empty:
        st.info("사건별 상태 분포 데이터가 없습니다.")
    else:
        event_names = filtered_events["EventName"].tolist() if "EventName" in filtered_events else []
        if event_names:
            selected_event = st.selectbox("사건", event_names)
            dist = event_distribution[event_distribution["EventName"] == selected_event].copy()
            if not dist.empty:
                dist["SharePercent"] = percent(dist["Share"])
                st.bar_chart(dist.set_index("HSIStateLabel")["SharePercent"], color="#ef4444")
                st.dataframe(format_share_columns(dist.drop(columns=["SharePercent"])), use_container_width=True, hide_index=True)
        else:
            st.info("사건 필터를 선택하면 상태 분포를 볼 수 있습니다.")

with tabs[2]:
    left, right = st.columns([0.95, 1.05])
    with left:
        st.subheader("전체 HSI 상태 분포")
        make_state_chart(filtered_monthly)
        st.dataframe(filtered_monthly, use_container_width=True, hide_index=True)
    with right:
        show_image(*CORE_FIGURES[3])

with tabs[3]:
    st.subheader("설계용 기간과 검증용 기간")
    if validation_wave.empty:
        st.info("설계/검증 요약 데이터가 없습니다.")
    else:
        wave_display = validation_wave.copy()
        numeric_cols = wave_display.select_dtypes(include="number").columns
        wave_display[numeric_cols] = wave_display[numeric_cols].round(3)
        st.dataframe(wave_display, use_container_width=True, hide_index=True)

    st.subheader("기간별 상태 분포")
    if validation_state.empty:
        st.info("기간별 상태 분포 데이터가 없습니다.")
    else:
        state_chart = validation_state.copy()
        state_chart["SharePercent"] = percent(state_chart["Share"])
        pivot = state_chart.pivot_table(
            index="HSIStateLabel",
            columns="Period",
            values="SharePercent",
            aggfunc="sum",
        ).fillna(0)
        st.bar_chart(pivot)
        st.dataframe(format_share_columns(validation_state), use_container_width=True, hide_index=True)

with tabs[4]:
    st.subheader("핵심 그래프")
    for title, filename, caption in CORE_FIGURES:
        show_image(title, filename, caption)
        st.divider()

    st.subheader("보조 그래프")
    cols = st.columns(3)
    for idx, (title, filename) in enumerate(SUPPORT_FIGURES):
        with cols[idx % 3]:
            path = FIGURE_DIR / filename
            if path.exists():
                st.image(str(path), caption=title, use_container_width=True)
            else:
                st.warning(f"누락: {filename}")
