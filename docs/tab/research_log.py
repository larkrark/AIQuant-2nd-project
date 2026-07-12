import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def make_research_progress_data() -> pd.DataFrame:
    """
    HSI 연구 진행도 요약 그래프용 데이터.
    completed: 완료된 실험 수
    planned: 예정 실험 수
    """
    data = [
        {
            "block": "00~05 데이터·상태분류·baseline",
            "short_label": "00~05\n데이터·상태분류·baseline",
            "completed": 6,
            "planned": 0,
            "experiments": "00, 01, 02, 03, 04, 05",
            "purpose": "최종 데이터 기준 정리, HSI 입력 신호 생성, HSI 5상태 분류, baseline 백테스트 수행",
            "hsi_relation": "HSI가 ETF 비중 조절로 연결되는 기본 구조를 만든 단계",
            "status": "완료",
        },
        {
            "block": "06~09 진단·조합·event filter",
            "short_label": "06~09\n진단·조합·event filter",
            "completed": 4,
            "planned": 0,
            "experiments": "06, 07, 08, 09",
            "purpose": "상대속도, 신호 조합, 사건균형지표, event filter를 통해 HSI 상태분류를 진단",
            "hsi_relation": "HSI 상태가 어떤 신호 균형과 조합에서 나왔는지 확인하는 보조 검증 단계",
            "status": "완료",
        },
        {
            "block": "10·11·20·21·23 λ·θ 모델 셀렉션",
            "short_label": "10·11·20·21·23\nλ·θ 모델 셀렉션",
            "completed": 5,
            "planned": 0,
            "experiments": "10, 11, 20, 21, 23",
            "purpose": "λ 부분조정, θ 민감도, 거래비용, Turnover를 고려해 발표·보고서용 후보를 선별",
            "hsi_relation": "HSI 상태별 목표비중으로 이동하는 속도와 민감도를 조절해 운용 가능성을 검토",
            "status": "완료",
        },
        {
            "block": "12~13 macro companion 진단",
            "short_label": "12~13\nmacro companion 진단",
            "completed": 2,
            "planned": 0,
            "experiments": "12, 13",
            "purpose": "금리·환율·GDP 기반 매크로 보조장치를 만들고 HSI 위험상태와의 겹침을 진단",
            "hsi_relation": "HSI를 대체하지 않고, HSI 위험상태를 외부 거시환경으로 보조 해석",
            "status": "완료",
        },
        {
            "block": "14 macro overlay backtest",
            "short_label": "14\nmacro overlay backtest",
            "completed": 0,
            "planned": 1,
            "experiments": "14",
            "purpose": "macro companion 보조값을 실제 ETF 비중 조절에 소폭 반영하는 후속 백테스트",
            "hsi_relation": "HSI baseline 비중은 유지하고, 위험자산 비중만 작은 폭으로 조정하는 soft overlay 실험",
            "status": "예정",
        },
    ]

    return pd.DataFrame(data)


def make_experiment_log_data() -> pd.DataFrame:
    """
    연구일지 상세 표.
    팀원 공유용으로 실험 번호, 연구목적, HSI와의 관계를 함께 정리한다.
    """
    rows = [
        {
            "번호": "00",
            "실험명": "final project config check",
            "연구목적": "ETF 코드, 경로, 상태명, 수익률 단위, 공통 파라미터 확인",
            "HSI와의 관계": "HSI 전체 실험의 기준 설정",
            "진행상태": "완료",
        },
        {
            "번호": "01",
            "실험명": "build final data artifacts",
            "연구목적": "ETF 유니버스, 월말 가격, 월간 수익률, 자산군 표 생성",
            "HSI와의 관계": "HSI 계산과 백테스트의 입력 데이터 생성",
            "진행상태": "완료",
        },
        {
            "번호": "02",
            "실험명": "build hsi event balance indicator",
            "연구목적": "위험 사건과 완화 사건의 균형지표 생성",
            "HSI와의 관계": "HSI 상태분류의 내부 보조 진단",
            "진행상태": "완료",
        },
        {
            "번호": "03",
            "실험명": "prepare monthly signal inputs",
            "연구목적": "월말 기준 HSI 입력 신호 정렬",
            "HSI와의 관계": "월말 신호를 다음 달 수익률에 연결하기 위한 정렬 단계",
            "진행상태": "완료",
        },
        {
            "번호": "04",
            "실험명": "build hsi state5 baseline",
            "연구목적": "HSI 5상태 분류표 생성",
            "HSI와의 관계": "프로젝트 핵심 상태분류 결과",
            "진행상태": "완료",
        },
        {
            "번호": "05",
            "실험명": "backtest baseline allocation rule",
            "연구목적": "HSI 상태별 ETF 비중 규칙 백테스트",
            "HSI와의 관계": "HSI가 실제 자산배분으로 연결되는지 확인",
            "진행상태": "완료",
        },
        {
            "번호": "06~09",
            "실험명": "diagnostics and event filter",
            "연구목적": "상대속도, 신호 조합, 사건균형, event filter 진단",
            "HSI와의 관계": "HSI 상태분류의 정합성과 보조 필터 가능성 확인",
            "진행상태": "완료",
        },
        {
            "번호": "10",
            "실험명": "inertia lambda experiment",
            "연구목적": "목표 비중으로 즉시 이동하지 않고 일부만 조정하는 λ 실험",
            "HSI와의 관계": "HSI 상태별 목표비중 전환 속도 조절",
            "진행상태": "완료",
        },
        {
            "번호": "11",
            "실험명": "theta sensitivity experiment",
            "연구목적": "θ 기준 변화에 따른 상태분포와 성과 안정성 확인",
            "HSI와의 관계": "HSI 상태분류 민감도 점검",
            "진행상태": "완료",
        },
        {
            "번호": "20",
            "실험명": "select final candidates with cost and turnover",
            "연구목적": "거래비용, Turnover, 성과지표를 함께 고려해 후보 선별",
            "HSI와의 관계": "HSI 기반 전략 후보를 운용 가능성 기준으로 압축",
            "진행상태": "완료",
        },
        {
            "번호": "21",
            "실험명": "build candidate report tables and figures",
            "연구목적": "후보 전략별 보고서용 표와 그림 생성",
            "HSI와의 관계": "HSI 후보 전략을 발표 가능한 산출물로 정리",
            "진행상태": "완료",
        },
        {
            "번호": "23",
            "실험명": "build report candidate tables goldfriend",
            "연구목적": "shortlist, 비용 민감도, λ family 표 정리",
            "HSI와의 관계": "HSI 기반 모델 셀렉션 결과를 보고서용 후보로 정리",
            "진행상태": "완료",
        },
        {
            "번호": "12",
            "실험명": "build macro companion layer",
            "연구목적": "금리·환율·GDP 기반 매크로 보조장치 생성",
            "HSI와의 관계": "HSI 상태를 외부 거시환경으로 보조 해석",
            "진행상태": "완료",
        },
        {
            "번호": "13",
            "실험명": "hsi macro companion diagnostic",
            "연구목적": "HSI 위험상태와 macro 위험신호의 겹침 확인",
            "HSI와의 관계": "HSI 위험 판단이 거시환경 위험과 얼마나 일치하는지 진단",
            "진행상태": "완료",
        },
        {
            "번호": "14",
            "실험명": "macro companion overlay backtest",
            "연구목적": "macro companion을 실제 비중 조절에 소폭 반영",
            "HSI와의 관계": "HSI baseline 위에 작은 방어 보정값을 얹는 후속 실험",
            "진행상태": "예정",
        },
    ]

    return pd.DataFrame(rows)


def build_progress_bar_chart(progress_df: pd.DataFrame) -> go.Figure:
    """
    연구 진행도 수평 막대그래프.
    hovertemplate으로 커서를 올렸을 때 설명이 뜨도록 구성한다.
    selected/unselected 스타일을 넣어 클릭 선택 시 테두리가 강조되도록 한다.
    """
    # 화면 위에서 00~05가 먼저 보이도록 역순 사용
    df = progress_df.iloc[::-1].copy()

    customdata_completed = df[
        ["experiments", "purpose", "hsi_relation", "status"]
    ].to_numpy()

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="완료",
            y=df["short_label"],
            x=df["completed"],
            orientation="h",
            customdata=customdata_completed,
            marker=dict(
                color="#5B9DF9",
                line=dict(color="rgba(255,255,255,0.85)", width=1.5),
            ),
            # plotly 스펙상 bar.selected.marker는 color/opacity만 지원 (line 불가)
            selected=dict(
                marker=dict(opacity=1.0)
            ),
            unselected=dict(
                marker=dict(opacity=0.45)
            ),
            hovertemplate=(
                "<b>%{y}</b><br><br>"
                "완료 실험 수: <b>%{x}개</b><br>"
                "실험 번호: %{customdata[0]}<br><br>"
                "<b>연구목적</b><br>%{customdata[1]}<br><br>"
                "<b>HSI와의 관계</b><br>%{customdata[2]}<br><br>"
                "상태: %{customdata[3]}"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Bar(
            name="예정",
            y=df["short_label"],
            x=df["planned"],
            orientation="h",
            customdata=customdata_completed,
            marker=dict(
                color="#6BCB77",
                line=dict(color="rgba(255,255,255,0.85)", width=1.5),
            ),
            # plotly 스펙상 bar.selected.marker는 color/opacity만 지원 (line 불가)
            selected=dict(
                marker=dict(opacity=1.0)
            ),
            unselected=dict(
                marker=dict(opacity=0.45)
            ),
            hovertemplate=(
                "<b>%{y}</b><br><br>"
                "예정 실험 수: <b>%{x}개</b><br>"
                "실험 번호: %{customdata[0]}<br><br>"
                "<b>연구목적</b><br>%{customdata[1]}<br><br>"
                "<b>HSI와의 관계</b><br>%{customdata[2]}<br><br>"
                "상태: %{customdata[3]}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>HSI 연구 블록별 진행도</b><br>"
                 "<sup>실험 번호 기준으로 완료된 연구 블록과 다음 예정 작업을 정리한 그래프입니다.</sup>",
            x=0.0,
            xanchor="left",
        ),
        barmode="group",
        bargap=0.35,
        height=520,
        margin=dict(l=40, r=40, t=90, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Malgun Gothic, Apple SD Gothic Neo, Arial, sans-serif",
            size=14,
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.08,
            xanchor="center",
            x=0.5,
            title_text="",
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Malgun Gothic, Apple SD Gothic Neo, Arial, sans-serif",
        ),
        xaxis=dict(
            title="실험 수",
            range=[0, 8],
            dtick=2,
            gridcolor="rgba(160,160,160,0.25)",
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            automargin=True,
        ),
    )

    return fig


def render_research_log() -> None:
    st.header("연구 진행도 요약 그래프")
    st.caption(
        "커서를 막대 위에 올리면 연구목적과 HSI와의 관계가 표시됩니다. "
        "막대를 클릭하면 선택 정보가 아래에 표시됩니다."
    )

    progress_df = make_research_progress_data()
    log_df = make_experiment_log_data()

    fig = build_progress_bar_chart(progress_df)

    # Streamlit 버전에 따라 on_select가 지원되지 않을 수 있으므로 안전하게 처리
    try:
        selected_state = st.plotly_chart(
            fig,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
            key="research_progress_chart",
        )
    except TypeError:
        st.plotly_chart(
            fig,
            use_container_width=True,
            key="research_progress_chart_fallback",
        )
        selected_state = None

    selected_points = []

    if selected_state is not None:
        try:
            selected_points = selected_state.selection.points
        except Exception:
            selected_points = []

    if selected_points:
        point = selected_points[0]
        selected_label = point.get("y")

        selected_row = progress_df[
            progress_df["short_label"] == selected_label
        ]

        if not selected_row.empty:
            row = selected_row.iloc[0]

            st.success(f"선택한 연구 블록: {row['block']}")

            col1, col2, col3 = st.columns(3)
            col1.metric("완료 실험 수", int(row["completed"]))
            col2.metric("예정 실험 수", int(row["planned"]))
            col3.metric("진행상태", row["status"])

            st.markdown("**연구목적**")
            st.write(row["purpose"])

            st.markdown("**HSI와의 관계**")
            st.write(row["hsi_relation"])
    else:
        st.info("막대를 클릭하면 해당 연구 블록의 상세 설명이 아래에 표시됩니다.")

    st.divider()

    st.subheader("연구일지 상세 표")
    st.dataframe(
        log_df,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("팀 공유용 요약 문장")
    st.markdown(
        """
현재 연구일지는 크게 **① HSI 입력·상태분류·baseline 구축**,
**② event balance와 신호 조합 진단**,
**③ λ·θ 조정 및 모델 셀렉션**,
**④ 금리·환율·GDP 기반 macro companion 진단**,
**⑤ macro overlay 예정 실험**으로 정리했습니다.

00~05번은 HSI가 실제 ETF 비중으로 연결되는 기본 구조를 만든 단계이고,
06~09번은 그 상태분류가 신호 균형과 조합 측면에서 납득 가능한지 확인한 단계입니다.
10·11·20·21·23번은 λ 부분조정과 θ 민감도를 이용해 운용 가능한 후보를 고르는 모델 셀렉션 단계입니다.
12~13번은 HSI 위험상태가 금리·환율·GDP 위험환경과 얼마나 겹치는지 보는 보조 진단 단계이고,
14번은 이 macro companion을 실제 비중 조절에 소폭 반영하는 후속 실험입니다.
        """
    )