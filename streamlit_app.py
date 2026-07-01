from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dashboard import hsi_candidates, midterm  # noqa: E402


PAGES = {
    "candidates": ("HSI 후보 전략", hsi_candidates.render),
    "midterm": ("기존 중간발표 자료", midterm.render),
}


def configure_page() -> None:
    st.set_page_config(
        page_title="AIQuant HSI Dashboard",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2.25rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.45rem;
        }
        [data-testid="stMetricLabel"] {
            color: #475569;
        }
        div[data-testid="stAlert"] {
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    configure_page()

    with st.sidebar:
        st.header("AIQuant HSI")
        st.caption("새 후보전략 자료를 시작 페이지로 통일하고, 기존 중간발표 자료는 보존 페이지에서 참조합니다.")

    page_key = st.query_params.get("page", "candidates")
    if page_key not in PAGES:
        page_key = "candidates"

    active_style = "font-weight:700; color:#1f77b4;"
    inactive_style = "color:#475569;"
    st.markdown(
        (
            f"<a href='?page=candidates' style='{active_style if page_key == 'candidates' else inactive_style}'>"
            "HSI 후보 전략</a>"
            "<span style='color:#cbd5e1; padding:0 0.75rem;'>|</span>"
            f"<a href='?page=midterm' style='{active_style if page_key == 'midterm' else inactive_style}'>"
            "기존 중간발표 자료</a>"
        ),
        unsafe_allow_html=True,
    )
    st.divider()
    PAGES[page_key][1]()


if __name__ == "__main__":
    main()
