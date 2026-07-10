from pathlib import Path


"""
final_project_config.py

HSI 기반 ETF 방어형 자산배분 프로젝트
최종 재현 파이프라인 공통 설정 파일

최종 기준
---------
- 데이터 담당 최종 모듈: HSI_data_pipeline_0629_5.py
- 후속 실험 기준 입력: hsi_data_bundle.xlsx
- 백테스트 수익률 기준: monthly_return_decimal 시트
- 보고서 확인용 수익률 기준: monthly_return_pct 시트

역할
----
이 파일은 계산을 많이 하는 파일이 아니다.
00~11번 최종 실험 파일들이 공통으로 사용할 경로, 시트명, 상태명,
티커, 수익률 단위, 리밸런싱 규칙, 사건균형지표와 외부 사건 달력의 역할을 고정한다.
"""


# ============================================================
# 1. 프로젝트 경로
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"

OUTPUT_DIR = PROJECT_ROOT / "output"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"

DOCS_DIR = PROJECT_ROOT / "docs"


# ============================================================
# 2. 최종 데이터 담당 산출물
# ============================================================

FINAL_DATA_PIPELINE_FILE = SRC_DIR / "HSI_data_pipeline_0629_5.py"

# 데이터 담당자님 코드 실행 결과 기본 위치
FINAL_DATA_BUNDLE = TABLE_DIR / "hsi_data_bundle.xlsx"

# 혹시 사용자가 직접 루트에 복사해 둔 경우까지 후보로 둔다.
DATA_BUNDLE_CANDIDATES = [
    TABLE_DIR / "hsi_data_bundle.xlsx",
    PROJECT_ROOT / "hsi_data_bundle.xlsx",
    DATA_DIR / "hsi_data_bundle.xlsx",
    PROCESSED_DIR / "hsi_data_bundle.xlsx",
]


# ============================================================
# 3. 외부 사건 달력
# ============================================================

# 현재 사용자 작업폴더에는 shock_calendar.py가 프로젝트 루트에 있다고 했다.
# 최종 권장명은 src/market_event_calendar.py 이지만,
# 00번에서는 현재 파일 존재 여부를 먼저 확인한다.
SHOCK_CALENDAR_DRAFT = PROJECT_ROOT / "shock_calendar.py"
MARKET_EVENT_CALENDAR_FILE = SRC_DIR / "market_event_calendar.py"


# ============================================================
# 4. 최종 ETF 유니버스
# ============================================================

RISK_TICKER = "069500"
BOND_TICKER = "114260"
CASH_TICKER = "153130"

TICKERS = [
    RISK_TICKER,
    BOND_TICKER,
    CASH_TICKER,
]

TICKER_NAME_MAP = {
    "069500": "KODEX 200",
    "114260": "KODEX 국고채3년",
    "153130": "KODEX 단기채권PLUS",
}

TICKER_ROLE_MAP = {
    "069500": "위험자산",
    "114260": "방어 채권",
    "153130": "현금성 방어자산",
}

BENCHMARK_TICKER = RISK_TICKER
DATA_START_DATE = "2012-03-07"


# ============================================================
# 5. hsi_data_bundle.xlsx 필수 시트
# ============================================================

REQUIRED_BUNDLE_SHEETS = [
    "meta",
    "input_structure",
    "output_structure",
    "etf_info",
    "asset_class",
    "monthly_price",
    "monthly_return_pct",
    "monthly_return_decimal",
    "signal_inputs",
    "hsi_scaled_scores",
    "hsi_direction",
    "hsi_signal",
    "signal_direction_map",
    "snapshot",
    "data_period",
    "missing_summary",
    "liquidity_check",
    "exclusions",
]

# 후속 실험에서 특히 많이 쓰는 핵심 시트
CORE_EXPERIMENT_SHEETS = [
    "asset_class",
    "monthly_price",
    "monthly_return_decimal",
    "monthly_return_pct",
    "signal_inputs",
    "hsi_scaled_scores",
    "hsi_direction",
    "signal_direction_map",
]


# ============================================================
# 6. 수익률 단위 규칙
# ============================================================

RETURN_UNIT_RULE = {
    "monthly_return_pct": "percent",
    "monthly_return_decimal": "decimal",
}

BACKTEST_RETURN_SHEET = "monthly_return_decimal"
REPORT_RETURN_SHEET = "monthly_return_pct"

MONTHLY_RETURN_DECIMAL_NOTE = (
    "hsi_data_bundle.xlsx의 monthly_return_decimal 시트는 백테스트 계산용 decimal 단위이다. "
    "예: 2.5%는 0.025로 저장한다."
)

MONTHLY_RETURN_PERCENT_NOTE = (
    "hsi_data_bundle.xlsx의 monthly_return_pct 시트는 사람이 확인하기 위한 percent 단위이다. "
    "예: 2.5%는 2.5로 저장한다."
)


# ============================================================
# 7. HSI 상태명
# ============================================================

HSI_STATES = [
    "risk_relief",
    "neutral_watch",
    "conflict",
    "risk_warning",
    "accident_zone",
    "insufficient_data",
]

HSI_STATE_KR = {
    "risk_relief": "위험 완화 우세",
    "neutral_watch": "중립 관찰",
    "conflict": "신호 충돌",
    "risk_warning": "위험 악화 우세",
    "accident_zone": "강한 위험 구간",
    "insufficient_data": "자료 부족",
}


# ============================================================
# 8. 최종 baseline 리밸런싱 규칙
# ============================================================

FINAL_ALLOCATION_RULE_NAME = "final_baseline_state_target_weights_v1"

FINAL_BASELINE_ALLOCATION_RULES = {
    "risk_relief": {
        RISK_TICKER: 0.70,
        BOND_TICKER: 0.20,
        CASH_TICKER: 0.10,
        "state_kr": "위험 완화 우세",
        "rule_note": "위험 완화 우세. 위험자산 비중을 높이고 방어자산 비중을 낮춘다.",
    },
    "neutral_watch": {
        RISK_TICKER: 0.50,
        BOND_TICKER: 0.35,
        CASH_TICKER: 0.15,
        "state_kr": "중립 관찰",
        "rule_note": "중립 관찰. 위험자산과 방어자산을 균형 있게 배분한다.",
    },
    "conflict": {
        RISK_TICKER: 0.35,
        BOND_TICKER: 0.40,
        CASH_TICKER: 0.25,
        "state_kr": "신호 충돌",
        "rule_note": "위험 완화와 위험 악화 신호가 충돌하는 상태로 보고 중간 방어 비중을 적용한다.",
    },
    "risk_warning": {
        RISK_TICKER: 0.20,
        BOND_TICKER: 0.45,
        CASH_TICKER: 0.35,
        "state_kr": "위험 악화 우세",
        "rule_note": "위험 악화 우세. 위험자산 비중을 줄이고 채권·현금성 방어자산을 확대한다.",
    },
    "accident_zone": {
        RISK_TICKER: 0.00,
        BOND_TICKER: 0.30,
        CASH_TICKER: 0.70,
        "state_kr": "강한 위험 구간",
        "rule_note": "강한 위험 구간. 위험자산 비중을 제거하고 현금성 방어자산 중심으로 대기한다.",
    },
}


REBALANCING_RULE_DESIGN_PRINCIPLES = {
    "단조성": "위험 상태가 강해질수록 위험자산 비중은 감소한다.",
    "방어성": "위험 악화 상태에서는 채권·현금성 자산 비중을 높인다.",
    "비예측성": "HSI 상태를 미래수익률 예측값으로 보지 않는다.",
    "시점 정합성": "월말 HSI 상태를 다음 달 수익률에 적용한다.",
    "과잉매매 제한": "Turnover가 과도하게 커지지 않도록 λ 또는 turnover cap을 검토한다.",
    "해석 가능성": "상태별 비중 변화가 사람이 이해 가능한 구조여야 한다.",
}

ALIGNMENT_RULE = "signal_month_t_to_return_month_t_plus_1"


# ============================================================
# 9. 사건균형지표 / 상대속도 / θ / λ 역할 정의
# ============================================================

HSI_EVENT_BALANCE_ROLE = (
    "HSI 사건균형지표는 외부 사건 달력이 아니라, "
    "HSI 입력 신호의 과거 분포를 기준으로 위험 사건과 완화 사건의 반복 정도를 계산한 내부 보조지표이다. "
    "위험 사건은 과거 80분위수 이상, 완화 사건은 과거 20분위수 이하로 정의한다."
)

RELATIVE_SPEED_ROLE = (
    "상대속도 실험은 선행/후행 예측 실험이 아니라, "
    "빠른 신호와 느린 신호가 위험 악화 또는 위험 완화 방향으로 움직이는 속도 차이를 진단하는 실험이다."
)

MARKET_EVENT_CALENDAR_ROLE = (
    "시장 사건 달력은 HSI 계산이나 비중 결정에 직접 사용하지 않는다. "
    "HSI 상태와 백테스트 결과를 먼저 산출한 뒤, 주요 시장 사건 구간과 사후적으로 대조하는 "
    "해석·검증·시각화 보조 자료로 사용한다."
)

THETA_EXPERIMENT_ROLE = (
    "θ 실험은 최고 CAGR을 찾는 최적화가 아니라, HSI 상태분류 민감도 변화에도 "
    "상태분포, MDD, Turnover, Sharpe, Calmar가 안정적으로 유지되는지 확인하는 민감도 검증이다."
)

LAMBDA_EXPERIMENT_ROLE = (
    "λ 실험은 목표 비중으로 한 번에 이동할지 일부만 이동할지 결정하는 포트폴리오 관성 실험이다. "
    "Turnover와 방어 성과 사이의 균형을 확인한다."
)


# ============================================================
# 10. 후속 실험 파일 흐름
# ============================================================

FINAL_PIPELINE_STEPS = [
    ("00_final_project_config_check.py", "최종 기준 파일·번들·시트·단위·역할 확인"),
    ("01_load_bundle_and_make_structure_tables.py", "hsi_data_bundle.xlsx 로드 및 입력·출력 구조표 생성"),
    ("02_build_hsi_event_balance_indicator.py", "20/80 분위수 기반 사건균형·위험누적지표 생성"),
    ("03_prepare_monthly_signal_inputs.py", "일별 HSI 신호를 월말 기준으로 정리"),
    ("04_build_hsi_state5_baseline.py", "HSI 5상태 기준선 생성"),
    ("05_backtest_baseline_allocation_rule.py", "최종 상태별 목표 비중표 기준 baseline 백테스트"),
    ("06_build_relative_speed_diagnostics.py", "빠른 신호·느린 신호·상대속도 진단"),
    ("07_run_signal_combo_backtests.py", "기본 신호·확장 신호·상대속도 보조 조합 비교"),
    ("08_event_balance_state_diagnostic.py", "HSI 5상태와 사건균형지표 정합성 확인"),
    ("09_event_balance_filter_backtest.py", "사건균형지표를 보조 필터로 넣은 전략 실험"),
    ("10_inertia_lambda_experiment.py", "λ 기반 부분 조정·Turnover·거래비용 실험"),
    ("11_theta_sensitivity_experiment.py", "θ 민감도 검증"),
]

MARKET_EVENT_PIPELINE_STEPS = [
    ("50_build_market_event_calendar_table.py", "외부 사건 달력을 표준 CSV로 변환"),
    ("51_align_hsi_state_with_market_events.py", "HSI 상태와 시장 사건 구간을 사후 대조"),
    ("52_plot_event_annotated_hsi_timeline.py", "사건 주석 HSI 타임라인 생성"),
]


# ============================================================
# 11. 최종 산출물 경로
# ============================================================

FINAL_CONFIG_NOTE = DOCS_DIR / "main_final_project_config_note.md"
FINAL_BUNDLE_CHECK_TABLE = OUTPUT_DIR / "tables" / "main_final_bundle_check.csv"
FINAL_ALLOCATION_RULE_TABLE = OUTPUT_DIR / "tables" / "main_final_allocation_rule_table.csv"
FINAL_PIPELINE_STEP_TABLE = OUTPUT_DIR / "tables" / "main_final_pipeline_steps.csv"
FINAL_BUNDLE_SHEET_MAP = OUTPUT_DIR / "tables" / "main_final_bundle_sheet_map.csv"


# ============================================================
# 12. 공통 유틸 함수
# ============================================================

def ensure_final_directories() -> None:
    """
    최종 프로젝트에 필요한 기본 폴더를 생성한다.
    """
    for path in [
        SRC_DIR,
        DATA_DIR,
        RAW_DIR,
        PROCESSED_DIR,
        REFERENCE_DIR,
        OUTPUT_DIR,
        TABLE_DIR,
        FIGURE_DIR,
        DOCS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def require_file(path: Path, label: str = "") -> None:
    """
    필수 파일 존재 여부를 확인한다.
    """
    if not path.exists():
        prefix = f"{label}: " if label else ""
        raise FileNotFoundError(f"{prefix}필수 파일을 찾을 수 없습니다: {path}")


def find_data_bundle() -> Path:
    """
    hsi_data_bundle.xlsx 후보 위치 중 실제 존재하는 경로를 반환한다.
    """
    for path in DATA_BUNDLE_CANDIDATES:
        if path.exists():
            return path

    candidate_text = "\n".join([f"- {p}" for p in DATA_BUNDLE_CANDIDATES])
    raise FileNotFoundError(
        "hsi_data_bundle.xlsx를 찾지 못했습니다. 아래 후보 위치 중 하나에 파일을 두세요.\n"
        f"{candidate_text}"
    )


def ticker_list_text() -> str:
    """
    최종 ETF 유니버스 문자열 요약.
    """
    return ", ".join([f"{t}({TICKER_NAME_MAP.get(t, '')})" for t in TICKERS])


def print_config_summary() -> None:
    """
    최종 설정 요약을 콘솔에 출력한다.
    """
    print("=" * 80)
    print("최종 HSI 프로젝트 공통 설정")
    print("=" * 80)
    print(f"PROJECT_ROOT                 : {PROJECT_ROOT}")
    print(f"FINAL_DATA_PIPELINE_FILE      : {FINAL_DATA_PIPELINE_FILE}")
    print(f"FINAL_DATA_BUNDLE             : {FINAL_DATA_BUNDLE}")
    print(f"TICKERS                       : {ticker_list_text()}")
    print(f"BENCHMARK_TICKER              : {BENCHMARK_TICKER}")
    print(f"DATA_START_DATE               : {DATA_START_DATE}")
    print()
    print("[수익률 단위]")
    print(f"- monthly_return_decimal      : {RETURN_UNIT_RULE['monthly_return_decimal']}")
    print(f"- monthly_return_pct          : {RETURN_UNIT_RULE['monthly_return_pct']}")
    print()
    print("[역할 구분]")
    print("- hsi_event_balance_indicator : 내부 HSI 신호 기반 보조지표")
    print("- relative_speed_diagnostics  : 빠른/느린 신호 반응 속도 진단")
    print("- market_event_calendar       : 전략 입력 아님, 사후 해석용")
    print("=" * 80)