"""
Stage B (리포트 02~05): HSI 신호·5상태 분류·baseline 목표비중.

가격 기반 신호 → HSI 5상태 → 상태별 위험/방어 목표비중(baseline_rebalance_weights).
baseline(즉시비중)은 Stage D lambda=1.0 에 해당한다.
참고: legacy/10_build_hsi_signal_inputs.py, legacy/16_main_v2_build_hsi_state5_table.py
리포트 데이터: main_final_baseline_rebalance_weights.csv (현재 repo에 없음)
"""

import pandas as pd


def build_signal_inputs(monthly: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("build_signal_inputs: HSI 입력 신호 로직 이식 필요.")


def classify_hsi_states(signal_inputs: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("classify_hsi_states: 5상태 분류 기준 확정 후 구현.")


def baseline_target_weights(states: pd.DataFrame) -> pd.DataFrame:
    """HSI 상태 → 위험/방어 목표비중(Date + *_weight, 합 1.0). Stage D lambda 입력."""
    raise NotImplementedError("baseline_target_weights: 상태별 목표비중 규칙 구현 필요.")
