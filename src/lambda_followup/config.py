# -*- coding: utf-8 -*-
"""
config.py — 사전 등록(pre-registration) 고정 설정

근거 문서: HSI_RA_비대칭람다_상세수행문서_v2 §1.5(frozen), §1.6(grid), §3.9(IS/OOS)
원칙: 결과를 본 뒤 이 파일의 grid·threshold·기간을 바꾸지 않는다.
변경이 불가피하면 CHANGES 주석에 사유·일자를 기록한다. (게이트 ⑦ 누수 audit 항목)
"""

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]  # src/lambda_followup 구조에 맞춤
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
TABLE_DIR = PROJECT_DIR / "output" / "tables"
FIGURE_DIR = PROJECT_DIR / "output" / "figures"
REPORT_DIR = PROJECT_DIR / "reports"

# ------------------------------------------------------------
# 입력 파일 (기존 Git 산출물 규약)
# ------------------------------------------------------------
# main_final_monthly_return_decimal.csv:
#   index=월말 Date, columns=["069500","114260","153130"], 값=decimal 월수익률
RETURNS_FILE = PROCESSED_DIR / "main_final_monthly_return_decimal.csv"

# main_final_baseline_rebalance_weights.csv:
#   index=신호월 Date(월말), 필요 열: hsi_state 또는 (w_star_069500, w_star_114260, w_star_153130)
WEIGHTS_FILE = PROCESSED_DIR / "main_final_baseline_rebalance_weights.csv"

# E24용(선택): 팩터 월시계열. 없으면 E24는 건너뛴다.
FACTORS_FILE = PROCESSED_DIR / "factor_inputs_monthly.csv"

# ------------------------------------------------------------
# 고정 요소 (frozen) — v2 §1.5
# ------------------------------------------------------------
TICKERS = ["069500", "114260", "153130"]  # 위험 / 채권형 방어 / 현금성 방어
RISK_TICKER = "069500"

# HSI 상태별 목표비중 w* (069500 / 114260 / 153130)
STATE_TARGET_WEIGHTS = {
    "risk_relief":       [0.70, 0.20, 0.10],
    "neutral_watch":     [0.50, 0.35, 0.15],
    "conflict":          [0.35, 0.40, 0.25],
    "risk_warning":      [0.20, 0.45, 0.35],
    "accident_zone":     [0.00, 0.30, 0.70],
    # insufficient_data: 직전 실제비중 유지(신호 없음 처리). 첫 달이면 중립.
    "insufficient_data": None,
}
NEUTRAL_STATE = "neutral_watch"

FIXED_BM_WEIGHTS = [0.70, 0.20, 0.10]   # 메인 BM
EW_WEIGHTS = [1 / 3, 1 / 3, 1 / 3]      # 보조 BM

PERIODS_PER_YEAR = 12

# 거래비용 민감도 (편도 아님: Turnover=Σ|Δw|/2 에 곱하는 비율)
COST_BPS_GRID = [0, 5, 10, 20]

# ------------------------------------------------------------
# 사전 등록 grid — v2 §1.6 (결과 후 변경 금지)
# ------------------------------------------------------------
E28_LAMBDA_GRID = [0.00, 0.10, 0.20, 0.30, 0.50, 0.70, 1.00]
E28_LAMBDA_GRID_FINE = [round(x * 0.05, 2) for x in range(0, 21)]  # 보조(0.05 간격)

E29_LAMBDA_UP_GRID = [0.10, 0.20, 0.30, 0.50]
E29_LAMBDA_DOWN_GRID = [0.10, 0.20, 0.30, 0.50]

# E30 규칙 v1 (threshold는 IS에서만 결정 — 아래 값은 문서상 v1 초기값)
E30_RULE_V1 = {
    "lambda_base": 0.30,
    "lambda_high_risk": 0.10,
    "lambda_stable_relief": 0.50,
    # 고위험 조건
    "volatility_z_high": 1.0,        # volatility_z > 1
    "drawdown_low": -0.10,           # rolling_drawdown < -10%
    "macro_risk_high": 2,            # macro_risk_score >= 2 (macro 없으면 조건 비활성)
    # 안정 완화 조건
    "relief_persist_months": 3,      # risk_relief 3개월 이상 지속
    "volatility_z_calm": 0.0,        # volatility_z < 0
    "momentum_z_positive": 0.0,      # momentum_z > 0
    # 상태변수 계산 창 (IS에서 확정할 값 — 초기값 기록)
    "vol_window": 12,                # 12개월 rolling 변동성
    "z_window": 36,                  # z-score용 36개월 rolling 평균·표준편차
    "drawdown_window": 12,           # 12개월 rolling 낙폭 (위험자산 069500 기준)
    "momentum_lookback": 12,         # 12-1 모멘텀
    "momentum_skip": 1,
}

# ------------------------------------------------------------
# IS / OOS / Walk-forward — v2 §3.9
# ------------------------------------------------------------
IS_START, IS_END = "2012-04-30", "2020-12-31"
OOS_START, OOS_END = "2021-01-31", "2026-06-30"
WF_TRAIN_MONTHS = 60
WF_TEST_MONTHS = 12
WF_STEP_MONTHS = 12

# robustness 기간분할 — v2 §3.8 게이트 ④
ROBUSTNESS_SPLITS = {
    "2012-2015": ("2012-04-30", "2015-12-31"),
    "2016-2019": ("2016-01-31", "2019-12-31"),
    "2020-2022": ("2020-01-31", "2022-12-31"),
    "2023-2026": ("2023-01-31", "2026-06-30"),
}

# ------------------------------------------------------------
# 성과 기준선 (게이트 ① 재현·검산용) — v2 §1.5 주의(버전 정합성)
# convention A = 실험 10·20~23 계열(공식 채택), convention B = 16·17번 표
# ------------------------------------------------------------
BASELINE_REFERENCE = {
    "A(exp10/20-23)": {"EW": {"cagr": 6.51, "mdd": -13.57},
                       "lambda_0.1": {"cagr": 8.66, "mdd": -14.74},
                       "lambda_0.3": {"cagr": 9.09, "mdd": -15.22},
                       "hsi_baseline": {"cagr": 7.73, "mdd": -23.46}},
    "B(exp16/17)":     {"EW": {"cagr": 6.59, "mdd": -13.57},
                       "lambda_0.1": {"cagr": 8.69, "mdd": -14.74},
                       "lambda_0.3": {"cagr": 9.15, "mdd": -15.22},
                       "hsi_baseline": {"cagr": 7.83, "mdd": -23.46}},
}

# 파일명 접두 규약 (README_for_Bosung §9)
FINAL_PREFIX = "main_final_"     # 최종 보고용
INTERIM_PREFIX = "flex_"         # 중간·검토용

# ------------------------------------------------------------
# 사전등록 채택 결정규칙 (v3 추가) — 결과를 본 뒤 마진을 바꾸지 않는다
# ------------------------------------------------------------
# 프레이밍: RA는 시장 상태에 따라 매 시점 전략을 제시할 의무가 있다.
#   따라서 동적·비대칭 λ(시변 실행 layer)가 아래 비열등(non-inferiority) 기준과
#   8게이트를 통과하면 '기본 추천 layer'로 채택하고,
#   고정 λ(0.1/0.3)는 게이트 미통과 시의 차선책(fallback)으로만 유지한다.
#   fallback 시에도 HSI 상태가 매월 w*를 바꾸므로 배분은 시변 적응 전략이다(1차 적응).
ADOPTION_RULE = {
    "segment": "OOS",              # 판정 구간
    "cost_bp": 10,                 # 판정용 비용 가정 (보수적 중간값)
    "calmar_ratio_min": 0.90,      # Calmar_net10bp ≥ 대칭 최우수 × 0.90
    "mdd_worsen_max_pp": 2.0,      # MDD 악화 ≤ 대칭 λ=0.1 대비 2%p
    "tail_worsen_max_pp": 0.3,     # tail-month 평균수익 악화 ≤ 0.3%p (대칭 λ=0.1 대비)
    "turnover_cap_mult": 1.5,      # avg Turnover ≤ 대칭 λ=0.3 × 1.5
}
