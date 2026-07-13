"""문서 페이지 — 보고서·발표자료 다운로드 (구글 드라이브 공유링크).

링크 교체 방법: 아래 DOCS 리스트의 url을 실제 드라이브 공유링크로 바꾸고 push.
드라이브 링크는 '링크가 있는 모든 사용자 보기 가능'으로 설정할 것.
"""

import streamlit as st

# TODO: url을 실제 구글 드라이브 공유링크로 교체
DOCS = [
    {
        "title": "최종 발표자료",
        "file": "HSI_Overlay_RoboAdvisor_발표자료_final.pptx",
        "desc": "24장 · 문제의식부터 placebo 검정, 한계까지 최종 발표 슬라이드",
        "url": None,
    },
    {
        "title": "최종보고서",
        "file": "main_final_hsi_overlay_report_draft.pdf",
        "desc": "방법론·검증 절차·성과 분석 전체 (표 5·8·13 등 대시보드 수치의 원 출처)",
        "url": None,
    },
    {
        "title": "방법론 수식전개 검증 정리본 v2",
        "file": "HSI_방법론_수식전개_검증_방어형_정리본_v2.pdf",
        "desc": "HSI 계산식 · 상태판정 규칙 · λ 부분조정식의 수학적 전개와 검증",
        "url": None,
    },
    {
        "title": "Shuffle Placebo 검정 보고서",
        "file": "main_final_38b_hsi_shuffle_placebo_report_section.md",
        "desc": "HSI 목표비중 시점 배치 유효성 — 1,000회 블록 셔플 검정",
        "url": None,
    },
    {
        "title": "HSI·λ 기여분리 Ablation 보고서",
        "file": "섹션C_HSI_람다_기여분리_ablation_보고서이식본.md",
        "desc": "변동성-only 방어 대비 HSI 방향의 낙폭 통제 기여 (+4.6%p)",
        "url": None,
    },
]


def render_documents() -> None:
    st.title("문서")
    st.caption("프로젝트 보고서와 발표자료를 다운로드할 수 있습니다.")

    for doc in DOCS:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.subheader(doc["title"])
                st.markdown(f"`{doc['file']}`  \n{doc['desc']}")
            with col2:
                if doc["url"]:
                    st.link_button("다운로드", doc["url"], use_container_width=True)
                else:
                    st.button(
                        "준비 중", disabled=True,
                        key=f"btn_{doc['file']}", use_container_width=True,
                    )
        st.divider()

    st.info(
        "소스코드와 실험 노트 전체는 GitHub 저장소에서 확인할 수 있습니다: "
        "[larkrark/AIQuant-2nd-project](https://github.com/larkrark/AIQuant-2nd-project)"
    )
