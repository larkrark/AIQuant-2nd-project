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
