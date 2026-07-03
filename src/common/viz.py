"""
시각화 공통 설정 (한글 폰트, 전략 표시명).
"""

import matplotlib.pyplot as plt

STRATEGY_LABEL_MAP = {
    "EW": "EW",
    "HSI_final_baseline_overlay": "HSI baseline (즉시비중)",
    "lambda_0.1": "Lambda 0.1 (방어형)",
    "lambda_0.3": "Lambda 0.3 (균형형)",
    "Fixed_70_20_10_BM": "Fixed 70/20/10 BM",
}


def set_korean_font() -> None:
    """Windows 환경에서 한글 깨짐을 줄이기 위한 설정."""
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
