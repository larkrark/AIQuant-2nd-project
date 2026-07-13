import streamlit as st

st.set_page_config(
    page_title="HSI 기반 ETF 방어형 RoboAdvisor",
    page_icon="📊",
    layout="wide",
)

from tab.home import render_home
from tab.experiments import render_experiments

DRIVE_URL = (
    "https://drive.google.com/drive/folders/"
    "1jG4h1_-EZi40-aIPqgahfH7EyJT2zXtU?usp=drive_link"
)

PAGES = {
    "메인": render_home,
    "실험결과": render_experiments,
}

with st.sidebar:
    st.markdown("## HSI RoboAdvisor")
    page = st.radio("페이지", list(PAGES.keys()), label_visibility="collapsed")
    st.link_button("📄 문서 (Google Drive)", DRIVE_URL, use_container_width=True)
    st.divider()
    st.caption(
        "시장상태 해석(HSI) × 실행속도 조절(λ)로\n"
        "낙폭을 관리하는 방어형 ETF 오버레이"
    )

PAGES[page]()
