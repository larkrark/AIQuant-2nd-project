from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dashboard import home, hsi_candidates, midterm  # noqa: E402
from dashboard.paths import HSI_CANDIDATE_OUTPUT_DIR  # noqa: E402


PAGES = {
    "home": ("HSI란 무엇인가?", home.render),
    "candidates": ("후보 전략 시각화", hsi_candidates.render),
    "midterm": ("중간발표 아카이브", midterm.render),
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
        .nav-link {
            display: block;
            padding: 0.45rem 0.55rem;
            margin: 0.12rem 0;
            border-radius: 8px;
            text-decoration: none;
            color: #475569 !important;
        }
        .nav-link-active {
            background: #eff6ff;
            color: #1f77b4 !important;
            font-weight: 700;
        }
        .top-nav a {
            text-decoration: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_link(page_key: str, active_key: str) -> str:
    label = PAGES[page_key][0]
    active_class = " nav-link-active" if page_key == active_key else ""
    return f"<a class='nav-link{active_class}' href='?page={page_key}'>{label}</a>"


def render_sidebar(active_key: str) -> None:
    dashboard_html = HSI_CANDIDATE_OUTPUT_DIR / "hsi_candidate_visual_dashboard.html"

    with st.sidebar:
        st.header("AIQuant HSI")
        st.caption("프로젝트 개념과 시각화 자료를 한 곳에서 확인합니다.")
        st.markdown("**페이지 이동**")
        st.markdown(
            "\n".join(
                [
                    page_link("home", active_key),
                    page_link("candidates", active_key),
                    page_link("midterm", active_key),
                ]
            ),
            unsafe_allow_html=True,
        )

        if dashboard_html.exists():
            st.divider()
            st.markdown("**자료 다운로드**")
            st.download_button(
                "정적 HTML 대시보드",
                data=dashboard_html.read_bytes(),
                file_name=dashboard_html.name,
                mime="text/html",
                use_container_width=True,
            )


def render_top_nav(active_key: str) -> None:
    links = []
    for key, (label, _) in PAGES.items():
        color = "#1f77b4" if key == active_key else "#475569"
        weight = "700" if key == active_key else "500"
        links.append(f"<a href='?page={key}' style='color:{color}; font-weight:{weight};'>{label}</a>")
    separator = ' <span style="color:#cbd5e1; padding:0 0.6rem;">|</span> '
    st.markdown(
        f"<div class='top-nav'>{separator.join(links)}</div>",
        unsafe_allow_html=True,
    )
    st.divider()


def main() -> None:
    configure_page()

    page_key = st.query_params.get("page", "home")
    if page_key not in PAGES:
        page_key = "home"

    render_sidebar(page_key)
    render_top_nav(page_key)
    PAGES[page_key][1]()


if __name__ == "__main__":
    main()
