"""
Stage C (리포트 06~09): HSI 진단 보조 layer.

event balance, signal combo, relative speed, 상태 분포. 최종 매매신호가 아니라
해석·검증 보조 layer. 참고: legacy/04·06·07·08·09.
"""

import pandas as pd


def event_balance_diagnostic(states: pd.DataFrame, event_calendar: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("event_balance_diagnostic: 진단 로직 구현 필요.")


def signal_combo_relative_speed(signal_inputs: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("signal_combo_relative_speed: 진단 로직 구현 필요.")
