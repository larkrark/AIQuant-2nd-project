from __future__ import annotations

import streamlit as st
from streamlit_mermaid import st_mermaid

from .paths import MIDTERM_FIGURE_DIR, ROOT


STATE_ROWS = [
    ("risk_relief", "위험 완화 추세", "회복 신호가 우세하고 위험 신호가 약한 구간"),
    ("neutral_watch", "관찰 중립", "어느 방향도 강하지 않아 관찰이 필요한 구간"),
    ("conflict", "충돌 상태", "위험 신호와 회복/과열 신호가 동시에 강한 구간"),
    ("risk_warning", "위험 악화 추세", "위험 신호가 회복 신호보다 뚜렷하게 강한 구간"),
    ("accident_zone", "강한 위험 악화", "큰 하락 사건과 높은 위험 점수가 동시에 나타나는 구간"),
]


SIGNAL_FLOW = """
flowchart LR
    A["ETF 가격"] --> B["일별 수익률"]
    B --> C["60거래일 기준<br/>사건 크기 분류"]
    C --> D["상승/하락<br/>사건 카운트"]
    A --> E["모멘텀, 이동평균 괴리<br/>변동성, 상대강도"]
    D --> F["risk / overheat / recovery<br/>3개 점수"]
    E --> F
    F --> G["5상태 HSI"]
    G --> H["시장상태 해석 및<br/>비중 조절 overlay"]
"""


def render_signal_flow() -> None:
    st.subheader("가격 신호가 HSI가 되는 흐름")
    st_mermaid(
        SIGNAL_FLOW,
        height="360px",
        show_controls=False,
        key="hsi_signal_flow",
    )
    st.caption("가격에서 출발한 사건 신호와 보조 지표를 점수화하고, 최종적으로 해석 가능한 5상태 HSI로 압축합니다.")


def render_state_table() -> None:
    st.subheader("HSI 5상태")
    st.dataframe(
        [
            {"상태": code, "표시명": label, "해석": note}
            for code, label, note in STATE_ROWS
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_hourglass_image() -> None:
    path = MIDTERM_FIGURE_DIR / "fig00_hsi_hourglass_concept.png"
    if not path.exists():
        return
    st.subheader("모래시계 구조")
    st.image(str(path), use_container_width=True)
    st.caption("위쪽은 위험 악화 신호, 아래쪽은 위험 완화/회복 신호, 가운데는 중립 또는 충돌 판단 구간으로 해석합니다.")


def render() -> None:
    st.title("HSI란 무엇인가?")
    st.caption("Hourglass Signal Index: 가격 기반 신호를 해석 가능한 시장상태로 바꾸는 구조화 지표")

    st.markdown(
        """
HSI는 ETF 가격을 그대로 매수/매도 신호로 바꾸는 예측 모델이 아닙니다.
가격에서 파생한 여러 신호를 위험 악화, 과열/충돌, 회복 방향으로 나누고,
그 상대적인 강도와 충돌 여부를 바탕으로 현재 시장상태를 5개 상태로 분류하는 해석 지표입니다.

핵심 아이디어는 모래시계 구조입니다. 위쪽에는 큰 하락, 음의 모멘텀,
추세 약화, 변동성 확대처럼 위험이 커지는 신호가 쌓입니다. 아래쪽에는
양의 모멘텀, 추세 회복, 상대강도 개선, 위험 사건 감소처럼 위험이 완화되는
신호가 쌓입니다. 가운데에서는 두 방향의 신호가 약하면 중립, 동시에 강하면
충돌 상태로 판단합니다.
        """
    )

    cols = st.columns(3)
    cols[0].metric("입력", "가격 기반 신호", "수익률, 추세, 변동성")
    cols[1].metric("중간 구조", "3개 점수", "risk / overheat / recovery")
    cols[2].metric("출력", "5상태 HSI", "시장상태 label")

    render_signal_flow()

    left, right = st.columns([0.95, 1.05])
    with left:
        st.subheader("점수 구조")
        st.markdown(
            """
- `risk_score`: 큰 하락, 음의 모멘텀, 추세 약화, 변동성 확대가 강할수록 증가합니다.
- `overheat_score`: 큰 상승, 강한 상승 압력, 과도한 추세 괴리가 강할수록 증가합니다.
- `recovery_score`: 양의 모멘텀, 추세 회복, 상대강도 개선, 위험 사건 감소가 강할수록 증가합니다.
            """
        )
    with right:
        st.subheader("사용 방식")
        st.markdown(
            """
- Feature: 상태 label 또는 점수를 다른 모델의 입력 변수로 사용합니다.
- Regime split: 상태별로 수익률, 변동성, MDD, 승률을 비교합니다.
- Overlay: `risk_warning`, `accident_zone`에서 위험자산 비중 축소를 검토합니다.
- Validation: 사건 구간과 백테스트에서 상태 해석력이 유지되는지 확인합니다.
            """
        )

    render_state_table()
    render_hourglass_image()

    with st.expander("참고 문서"):
        st.write(f"원문 메모: `{ROOT / 'docs' / 'HSI_price_signal_to_structure_visual_note.md'}`")
        st.write("이 홈 화면은 해당 메모의 핵심 개념을 발표용 첫 화면에 맞게 요약한 것입니다.")
