import streamlit as st

st.set_page_config(
    page_title="HSI 연구 대시보드",
    page_icon="📊",
    layout="wide",
)

from tab.research_log import render_research_log
from tab.model_selection_dynamic import render_model_selection_dynamic
from tab.viz_hsi_candidate_tab import render_viz_hsi_candidate

st.title("HSI 기반 ETF 방어형 Overlay 연구 대시보드")

tab1, tab2, tab3 = st.tabs(
    ["연구일지", "동적 모델 셀렉션", "후보 전략 시각화"]
)

with tab1:
    render_research_log()

with tab2:
    render_model_selection_dynamic()

with tab3:
    render_viz_hsi_candidate()
