"""
시각화 공통 설정.

기존 plot 스크립트마다 동일하게 복제돼 있던 한글 폰트 설정을 통합한다.
"""

import matplotlib.pyplot as plt

# EW / main_v2 / main_v2b 전략 표시명 (EW 포함 전체 버전)
STRATEGY_LABEL_MAP = {
    "EW": "EW",
    "HSI_state5_overlay": "main_v2: conflict 방어",
    "HSI_state5_overlay_v2b": "main_v2b: conflict 관찰",
}


def set_korean_font() -> None:
    """
    Windows 환경에서 한글 깨짐을 줄이기 위한 설정.
    """
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
