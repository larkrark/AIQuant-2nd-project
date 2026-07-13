"""메인 페이지 — 프로젝트 소개 · 최신 HSI 상태 · 5상태 분류 체험기."""

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent
TS_PATH = DATA_DIR / "23_main_final_report_candidate_timeseries_subset.csv"

# 상태 정의 (판정 우선순위 순) — 최종보고서 표1 기준
STATE_INFO = {
    "risk_relief": ("위험 완화", "🟢", (70, 20, 10), "위험자산 참여 확대"),
    "neutral_watch": ("중립 관찰", "🔵", (50, 35, 15), "기존 비중 유지"),
    "conflict": ("신호 충돌", "🟡", (35, 40, 25), "방어 비중 확대"),
    "risk_warning": ("위험 경고", "🟠", (20, 45, 35), "위험자산 축소"),
    "accident_zone": ("사고 구간", "🔴", (0, 30, 70), "현금성 방어 강화"),
}

# 실측 컷오프 (전체 표본 172개월 분위수 기준)
NEUTRAL_BAND = 0.15
INTENSITY_CUT = 0.566   # intensity 75% 분위
ACCIDENT_CUT = 0.472    # direction 85% 분위


@st.cache_data
def load_latest_state():
    ts = pd.read_csv(TS_PATH, encoding="utf-8-sig")
    valid = ts[ts["hsi_state"].isin(STATE_INFO.keys())]
    latest_month = valid["year_month"].max()
    row = valid[valid["year_month"] == latest_month].iloc[0]
    return latest_month, row["hsi_state"]


def classify_demo(direction: float, intensity: float, etf_conflict: bool) -> str:
    """slide/코드와 동일한 판정 우선순위 (stage_b_hsi.classify_state5_row 준용)."""
    if etf_conflict:
        return "conflict"
    if abs(direction) <= NEUTRAL_BAND and intensity >= INTENSITY_CUT:
        return "conflict"
    if direction >= ACCIDENT_CUT and intensity >= INTENSITY_CUT:
        return "accident_zone"
    if direction > NEUTRAL_BAND:
        return "risk_warning"
    if direction < -NEUTRAL_BAND:
        return "risk_relief"
    return "neutral_watch"


def render_home() -> None:
    st.title("HSI 기반 ETF 방어형 RoboAdvisor")
    st.markdown(
        "**시장상태 해석(HSI) × 실행속도 조절(λ)로 낙폭을 관리하는 동적 자산배분 전략**"
    )
    st.markdown(
        "\\[이스트캠프\\] AI 퀀트 3회차 과정 2차 프로젝트 · 3조 · 권보성 · 김근형 · 추주원 · 김민호  \n"
        "데이터 2012.04 – 2026.06 (171개월) | KODEX 200 · 국고채3년 · 단기채권PLUS"
    )

    st.divider()

    # ── 최신 시장상태 ──────────────────────────────────
    st.header("최신 시장상태")
    try:
        latest_month, state = load_latest_state()
    except Exception:
        latest_month, state = None, None

    if state:
        kr, icon, (w_risk, w_bond, w_cash), action = STATE_INFO[state]
        st.caption(
            f"HSI는 월말 데이터로 산출되므로, 표시되는 상태는 분석 데이터의 "
            f"마지막 월({latest_month}) 기준입니다."
        )
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 2])
        c1.metric(f"{latest_month} 월말 기준", f"{icon} {kr}")
        c2.metric("KODEX 200", f"{w_risk}%")
        c3.metric("국고채 3년", f"{w_bond}%")
        c4.metric("단기채권PLUS", f"{w_cash}%")
        c5.metric("대응", action)
        st.caption(
            "HSI는 미래를 예측하지 않습니다 — 월말 가격 신호로 '지금'의 시장상태를 "
            "5가지로 해석하고, 상태별 사전 고정 목표비중으로 번역합니다."
        )
    else:
        st.warning("상태 데이터를 불러오지 못했습니다.")

    st.divider()

    # ── 5상태 분류 체험기 ──────────────────────────────
    st.header("HSI 5상태 분류 체험하기")
    st.markdown(
        "HSI는 여러 가격 신호를 위험 **악화 힘(V+)**과 **완화 힘(V−)**으로 종합해 "
        "두 스칼라를 만듭니다 — **direction**(누가 이기나 = 차이)과 "
        "**intensity**(얼마나 격렬한가 = 합). 아래 슬라이더로 직접 판정해 보세요."
    )

    col_in, col_out = st.columns([1, 1])

    with col_in:
        direction = st.slider(
            "direction (−1 완화 우세 ~ +1 악화 우세)",
            -0.7, 0.7, 0.0, 0.01,
        )
        intensity = st.slider(
            "intensity (0 조용함 ~ 0.8 격렬함)",
            0.0, 0.8, 0.3, 0.01,
        )
        etf_conflict = st.checkbox(
            "ETF 간 신호 충돌 (buy·caution 공존)", value=False,
            help="위험·방어 ETF의 신호가 서로 반대 방향을 가리키는 경우 — direction과 무관하게 conflict로 판정",
        )

    result = classify_demo(direction, intensity, etf_conflict)
    kr, icon, (w_risk, w_bond, w_cash), action = STATE_INFO[result]

    with col_out:
        st.subheader(f"{icon} {kr} ({result})")
        st.markdown(f"**목표비중** — KODEX 200 **{w_risk}%** / 국고채 **{w_bond}%** / 단기채권 **{w_cash}%**")
        st.markdown(f"**대응** — {action}")

        if result == "conflict" and not etf_conflict:
            st.info("방향은 애매한데(|direction| ≤ 0.15) 강도가 상위 25% — '조용한 중립'이 아니라 '격렬한 충돌'입니다.")
        elif result == "accident_zone":
            st.info("방향 상위 15% + 강도 상위 25% — 위험이 한꺼번에 켜진 구간, 위험자산 전량 축소.")
        elif result == "neutral_watch" and intensity < INTENSITY_CUT:
            st.info("방향도 강도도 뚜렷하지 않음 — 조용한 중립.")

    st.caption(
        f"판정 규칙: 우선순위 conflict → accident_zone → risk_warning → risk_relief → neutral_watch · "
        f"중립 밴드 ±{NEUTRAL_BAND} · intensity 컷 {INTENSITY_CUT}(표본 75%분위) · "
        f"accident 방향 컷 {ACCIDENT_CUT}(표본 85%분위). 실제 파이프라인과 동일한 로직이며, "
        "컷오프는 전체 표본 분위수의 실측값입니다."
    )
