"""
새 파이프라인 전용 설정.

공통 상수는 common.config 재사용. 여기서는 Lambda/Macro/BM/거래비용/선별 기준 등
리포트(10·15·17·20~23) 기준의 파라미터를 관리한다.
값은 리포트 및 조원 20_select 스크립트 기준이며 팀 합의로 조정한다.
"""

from common.config import ASSETS, WEIGHT_COLS  # noqa: F401 (재노출)

# --- Lambda 부분조정 (리포트 10) ---
LAMBDA_CANDIDATES = [0.1, 0.3, 0.5, 0.7, 1.0]
PRIMARY_LAMBDA_CANDIDATES = [0.1, 0.3]
BASELINE_LAMBDA = 1.0  # 즉시비중 = HSI baseline

# --- Macro soft overlay (리포트 15) ---
MACRO_SCALES = [0.25, 0.50, 0.75]

# --- 벤치마크 (리포트 17) ---
FIXED_BM_WEIGHTS = {"069500": 0.70, "114260": 0.20, "153130": 0.10}

# --- 거래비용 그리드 (리포트 20~23 / 조원 20_select) ---
COST_RATE_GRID = {
    "cost_0bp": 0.0000,
    "cost_5bp": 0.0005,
    "cost_10bp": 0.0010,
    "cost_20bp": 0.0020,
}
FINAL_COST_LABEL = "cost_10bp"

# --- Turnover 후보 필터 (%) ---
STRICT_AVG_TURNOVER_PCT = 10.0
STRICT_MAX_TURNOVER_PCT = 40.0
FLEX_AVG_TURNOVER_PCT = 15.0
FLEX_MAX_TURNOVER_PCT = 50.0

# --- 방어형 후보 판단 기준 ---
MIN_MONTHS_RATIO = 0.90
MDD_WORSE_THAN_EW_ALLOWANCE_PCT = 3.0
MIN_SHARPE = 0.70
MIN_CALMAR = 0.45
MIN_CAGR_GAP_VS_EW_PCT = 0.0
MAX_COST_DRAG_20BP_PCT = 1.0

# --- selection_score 가중치 (percentile 기반) ---
SELECTION_SCORE_WEIGHTS = {
    "CAGR_pct": 0.22,
    "MDD_pct": 0.26,
    "Calmar": 0.20,
    "Sharpe": 0.16,
    "avg_turnover_pct": 0.16,
}

REBALANCE = "monthly"

# --- 팩터 로딩 (stage_factor) ---
FACTOR_SET = ["market", "bond", "vkospi", "liquidity", "downside_risk"]
FACTOR_ROLLING_WINDOW = 36           # 기본 rolling window(개월). 24는 부록 민감도.
FACTOR_STANDARDIZE = "expanding_z"   # 룩어헤드 차단: 전체표본 아닌 expanding z-score
FACTOR_MIN_PERIODS = 12              # 표준화/회귀 최소 관측
FACTOR_LAG = {                       # 발표 시차/룩어헤드 차단용 lag(개월)
    "vkospi": 0,
    "liquidity": 0,
    "us_spillover": 1,
    "macro": 1,
    "credit_spread": 1,
}
FACTOR_CORR_THRESHOLD = 0.80         # 상관 중복 경고 임계
FACTOR_VIF_THRESHOLD = 5.0           # 다중공선성 경고 임계

# --- 동적 lambda (감마) : 실험용, 기본 비활성 ---
# lambda_t = clip(lam_min, lam_max, lambda_base + gamma * risk_score_t)
# gamma 부호는 경제적 근거로 a priori 고정(위험↑ -> lambda↓ 이면 gamma<0).
# 반드시 train/validation/test 또는 walk-forward 로 검증 후 사용.
DYNAMIC_LAMBDA = {
    "enabled": False,
    "lambda_base": 0.3,
    "gamma": -0.05,
    "lam_min": 0.10,
    "lam_max": 0.50,
    "risk_score": "composite",  # 예: 표준화 realized_vol/stock_bond_corr 합성
}

# --- E30-M 규칙 기반 동적 lambda (기본 0.3 + 고위험/안정완화 예외) ---
# 값은 E28 단일 λ 실험에서 의미가 확인된 후보(0.1/0.3/0.5)에서만 가져온다(과적합 방지).
# 우선순위: 고위험 > 안정완화 > 기본. threshold는 IS에서만 결정할 것.
DYNAMIC_LAMBDA_RULE = {
    "lam_default": 0.3,        # 기본(균형형 후보) = 과적합 방지 기준 속도
    "lam_high_risk": 0.1,      # 고위험 시(방어형 후보로 느리게)
    "lam_easing": 0.5,         # 안정 완화 확인 시(반영 가속)
    "vol_z_high": 1.0,         # volatility_z > 1
    "drawdown_low": -0.10,     # rolling_drawdown < -10%
    "macro_risk_high": 2,      # macro_risk_score >= 2 (rate_up + fx_up >= 2)
    "relief_persist_months": 3,  # risk_relief 3개월 이상 지속
}

# --- IS/OOS 분리 (보고서 §9) ---
IS_END = "2020-12-31"       # IS: 2012-04 ~ 2020-12
OOS_START = "2021-01-01"    # OOS: 2021-01 ~ 2026-06

# --- Adoption decision: 사전등록 비열등 4조건 (보고서 §13 표7, OOS 10bp net) ---
# Score식이 아니라 4조건 AND 통과(비열등)로 채택 판정.
ADOPTION = {
    "cost_bp": 10,
    "calmar_ratio_min": 0.90,      # ① Calmar_net >= 대칭 최우수 Calmar × 0.90
    "mdd_worsen_allow_pct": 2.0,   # ② MDD가 대칭 λ=0.1 대비 2.0%p 이상 악화 금지
    "tail_worsen_allow_pct": 0.3,  # ③ tail-month 평균수익이 λ=0.1 대비 0.3%p 이상 악화 금지
    "turnover_mult_max": 1.5,      # ④ 평균 Turnover <= 대칭 λ=0.3 × 1.5
    "tail_quantile": 0.10,         # tail-month = 위험자산(069500) 하위 10% 손실월
}

# --- 비대칭 λ 후보 (보고서 E29, up/down) ---
ASYM_CANDIDATES = [(0.1, 0.3), (0.1, 0.5), (0.2, 0.3)]  # (lam_up, lam_down)

# --- Walk-forward 검증 (보고서 §3.9) ---
WALK_FORWARD = {"train": 60, "test": 12, "step": 12}  # 개월
