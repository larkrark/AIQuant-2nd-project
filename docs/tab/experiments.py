"""실험결과 페이지 — 현재 기준 유효한 최종 결과 요약.

모든 수치는 최종보고서(main_final_hsi_overlay_report_draft)·38b placebo 보고서·
섹션C ablation 보고서 기준 (2026-07 검증 완료).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

FONT = "Malgun Gothic, Apple SD Gothic Neo, Arial, sans-serif"

# FULL 구간 성과-위험 (최종보고서 표5)
PERF = pd.DataFrame([
    # 전략, CAGR, MDD, Calmar, 구분, 해석
    ["FixedBM 70/20/10", 10.99, -25.67, 0.43, "벤치마크", "수익 1위, 낙폭 최악"],
    ["EW (동일비중)",      6.55, -13.57, 0.48, "벤치마크", "단순 분산 기준"],
    ["lambda_0.1",        8.64, -14.74, 0.59, "고정 λ",   "저회전 · 보수적 이동"],
    ["lambda_0.3",        9.09, -15.22, 0.60, "고정 λ",   "빠른 반응 · 회전율 증가"],
    ["asym_up0.1_down0.3", 6.84, -8.98, 0.76, "비대칭 λ", "방어 최강, 참여 과소"],
    ["dynamic_v1 ★",      9.73, -12.63, 0.77, "최종 후보", "Calmar 1위 — 방어·참여 균형"],
    ["dynamic_v1_macro",  9.65, -12.76, 0.76, "확장안",   "저회전 보수 확장안 (미채택)"],
], columns=["전략", "CAGR(%)", "MDD(%)", "Calmar", "구분", "해석"])

# 비열등 판정 (OOS · 10bp net, 사전등록 4조건)
ADOPTION = pd.DataFrame([
    ["Calmar_net", "대칭 최우수 × 0.90 이상", "1.471", "통과"],
    ["MDD", "대칭 λ=0.1 대비 악화 ≤ 2.0%p", "−12.63%", "통과"],
    ["tail-month 방어력", "평균수익 악화 ≤ 0.3%p", "−4.71%", "통과"],
    ["평균 Turnover(월)", "대칭 λ=0.3 × 1.5 이하", "4.835%", "통과"],
], columns=["기준", "사전등록 조건", "dynamic_v1", "판정"])

# Shuffle placebo (OOS · Net10bp, 1,000회 · 4개월 블록)
PLACEBO = pd.DataFrame([
    ["Calmar", "1.471", "0.815", "96.4%ile", "0.037"],
    ["MDD", "−12.63%", "−18.44%", "94.4%ile", "0.057"],
    ["CAGR", "18.58%", "15.23%", "93.5%ile", "0.066"],
    ["Sharpe", "1.031", "0.937", "90.4%ile", "0.097"],
    ["연환산 변동성", "18.12%", "16.27%", "22.4%ile", "0.776"],
    ["월 승률", "56.06%", "56.06%", "54.7%ile", "1.000"],
], columns=["지표", "실제값", "placebo 중앙값", "유리 백분위", "단측 p"])

# Ablation (섹션C — HSI vs 변동성-only)
ABLATION = pd.DataFrame([
    ["A. EW", "×", "×", -13.51, 0.55],
    ["B. FixedBM 70/20/10", "×", "×", -25.56, 0.51],
    ["E. VolOnly de-risk", "×", "○ (방향까지 vol로)", -16.17, 0.45],
    ["C. HSI + λ=0.3 고정", "○", "×", -11.85, 0.53],
    ["D. HSI + λ=0.1 고정", "○", "×", -11.54, 0.56],
    ["F. dynamic_v1 (풀)", "○", "○", -11.53, 0.56],
], columns=["후보", "HSI 방향", "vol 기반 λ", "MDD(%)", "Calmar"])


def build_candidate_map() -> go.Figure:
    df = PERF.copy()
    df["abs_mdd"] = df["MDD(%)"].abs()
    color_map = {"벤치마크": "#7A7A7A", "고정 λ": "#4E79A7",
                 "비대칭 λ": "#20A39E", "최종 후보": "#F28E2B", "확장안": "#B6A6CA"}

    fig = go.Figure()
    for grp, sub in df.groupby("구분"):
        fig.add_trace(go.Scatter(
            x=sub["abs_mdd"], y=sub["CAGR(%)"],
            mode="markers+text", name=grp,
            text=sub["전략"], textposition="top center",
            marker=dict(size=16 + sub["Calmar"] * 14,
                        color=color_map.get(grp, "#999"),
                        opacity=0.9, line=dict(color="white", width=1.5)),
            customdata=sub[["전략", "Calmar", "해석"]].to_numpy(),
            hovertemplate=("<b>%{customdata[0]}</b><br>"
                           "CAGR: %{y:.2f}%<br>절대 MDD: %{x:.2f}%<br>"
                           "Calmar: %{customdata[1]:.2f}<br><br>%{customdata[2]}"
                           "<extra></extra>"),
        ))

    fig.update_layout(
        title=dict(text="<b>후보맵 — CAGR vs 절대 MDD (FULL 2012.04–2026.06)</b><br>"
                        "<sup>점 크기 = Calmar. 왼쪽 위일수록 '덜 잃고 잘 버는' 전략.</sup>",
                   x=0.0, xanchor="left"),
        height=520, margin=dict(l=30, r=30, t=90, b=50),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13),
        xaxis=dict(title="절대 MDD (%) — 낮을수록 안정", gridcolor="rgba(150,150,150,0.25)"),
        yaxis=dict(title="CAGR (%)", gridcolor="rgba(150,150,150,0.25)"),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
        hoverlabel=dict(bgcolor="white", font_family=FONT),
    )
    return fig


def render_experiments() -> None:
    st.title("실험결과 — 최종 요약")
    st.caption("현재 기준 유효한 최종 결과만 정리했습니다. 수치는 최종보고서·검증 보고서 기준.")

    # ── 최종 후보 헤드라인 ────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("최종 후보", "dynamic_v1")
    c2.metric("CAGR (FULL)", "9.73%", "-1.26%p vs BM", delta_color="inverse")
    c3.metric("MDD (FULL)", "−12.63%", "+13.04%p 개선")
    c4.metric("Calmar", "0.77", "+0.34 vs BM")
    st.markdown(
        "> **수익률 알파는 없습니다. 그러나 낙폭 통제 엣지는 있습니다** — "
        "FixedBM 대비 CAGR은 1.26%p 낮지만, MDD 13.04%p 개선 · 변동성 4.09%p 감소 · "
        "Sharpe +0.10 · Calmar +0.34. 방어형 위험조정 성과가 이 전략의 정체성입니다."
    )

    st.plotly_chart(build_candidate_map(), use_container_width=True)

    st.subheader("FULL 구간 성과-위험 요약")
    st.dataframe(PERF, use_container_width=True, hide_index=True)

    st.divider()

    tab1, tab2, tab3 = st.tabs(["비열등 판정", "Shuffle Placebo", "Ablation (HSI 기여)"])

    with tab1:
        st.markdown(
            "**Adoption Decision** — '이기는가'가 아니라 '크게 밀리지 않는가'. "
            "기준은 결과를 보기 전에 사전등록했고, OOS · 10bp 비용차감 기준 4조건 모두 통과. "
            "3년 rolling 음수 누적수익 반복 없음도 확인."
        )
        st.dataframe(ADOPTION, use_container_width=True, hide_index=True)

    with tab2:
        st.markdown(
            "**HSI 목표비중의 시점 배치가 우연인가?** — λ 경로는 고정하고 HSI 목표비중 "
            "배치만 4개월 블록으로 무작위 셔플, 1,000회 반복 (OOS · Net10bp)."
        )
        st.dataframe(PLACEBO, use_container_width=True, hide_index=True)
        st.caption(
            "방어 지표(Calmar·MDD·CAGR)에서 상위권, 명목 p값은 Calmar만 0.05 미만. "
            "Bonferroni 보정 후 유의 지표 없음 — 강한 통계적 확정이 아니라 "
            "방어 지표에서 유리했을 가능성을 보여주는 보조 근거."
        )

    with tab3:
        st.markdown(
            "**성과가 λ 덕인가, HSI 신호 덕인가?** — HSI를 제거하고 변동성·drawdown만으로 "
            "방어한 E는 MDD −16.2% · Calmar 0.45로, HSI를 쓴 C·D·F(−11.5~−11.9% · 0.53~0.56)보다 "
            "나빴습니다. HSI 방향의 추가 기여는 F−E ≈ **+4.6%p** (낙폭 방어), "
            "동적 λ의 추가 기여는 F−C ≈ +0.3%p로 한계적."
        )
        st.dataframe(ABLATION, use_container_width=True, hide_index=True)
        st.caption(
            "주의: E는 λ=0.3 고정이 아니라 vol 신호가 방향·속도를 모두 담당하는 설계 — "
            "'HSI 완전 제거 vs HSI 사용' 비교입니다. EW 대비 Calmar 우위는 얇으며(0.56 vs 0.55) "
            "HSI의 승부처는 낙폭(MDD) 방어입니다."
        )

    st.divider()
    with st.expander("한계 — 증명하지 못한 것"):
        st.markdown(
            "- HSI 단독 기여 미분리 (셔플 검정은 λ 경로 고정 조건)\n"
            "- 명목 p값 Calmar 0.037만 통과, Bonferroni 보정 후 유의 없음\n"
            "- EW 대비 Calmar 우위 얇음 — 강점은 낙폭 통제에 집중\n"
            "- 슬리피지·세금·시장충격비용 미반영\n"
            "- 고위험에서 λ를 낮추면 방어 전환 속도도 느려지는 구조적 딜레마"
        )
