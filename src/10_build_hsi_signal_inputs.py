# -*- coding: utf-8 -*-
"""
Created on Sun Jun 28 22:46:53 2026

@author: user
"""

"""
HSI (Hourglass Signal Index) — 보조지표 입력 신호 계산 모듈
=============================================================
담당 역할: 데이터 확보·전처리 및 HSI 입력 신호 계산

흐름:
  1. ETF 후보군 정의 및 선정 기준 적용 → 최종 ETF_UNIVERSE 확정
  2. 확정된 ETF 종가 데이터 로드
  3. HSI 개별 지표 계산 (수익률 / 이동평균 / 모멘텀 / 변동성 / 상대강도)
  4. 표준화 → -10~+10 스코어 변환 → HSI direction / intensity 산출
  5. 그리드 서치로 파라미터 최적화
"""

import os
import warnings
import itertools

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
# --------------------------------------------------------------
# 0. 프로젝트 경로 설정
# --------------------------------------------------------------
# 이 파일 위치:
# AIQuant-2nd-project/src/10_build_hsi_signal_inputs.py
#
# PROJECT_ROOT:
# AIQuant-2nd-project
#
# 역할:
# - 입력 데이터 위치를 명확히 고정
# - 출력 CSV 저장 위치를 명확히 고정
# - Spyder, VS Code, PowerShell 어디서 실행해도 상대경로가 흔들리지 않게 관리

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"

OUTPUT_DIR = PROJECT_ROOT / "output"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"

# 출력 폴더가 없으면 자동 생성
TABLE_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────
# 1. ETF 후보군 정의 및 선정
#
#    선정 기준 (HSI 안내서 기반):
#      (A) 코스피(KRX 유가증권시장) 상장 종목
#      (B) 종가 데이터만으로 HSI 5개 지표 계산 가능 (거래량·재무 불필요)
#      (C) 자산군 다양성: 위험자산 / 안전자산 / 현금성 자산 각 1개 이상 포함
#      (D) 상장일 기준 현재(2026) 10년 이상 데이터 확보 가능
#      (E) 최종 선정 수: 3개 이하
#
#    함수 사용법:
#      candidates = build_etf_candidates()   # 후보군 생성
#      selected   = select_etf(candidates)   # 기준 적용 → 최종 선정
#      print_selection_report(candidates, selected)  # 결과 출력
# ──────────────────────────────────────────────────────────────

# 선정 기준 파라미터 (필요 시 변경)
SELECTION_CRITERIA = {
    "min_data_years":  10,          # 최소 데이터 연수 (상장일 기준)
    "reference_year":  2026,        # 현재 연도
    "max_etf_count":   3,           # 최종 선정 최대 수
    "required_asset_classes": ["equity", "bond", "money_market"],  # 자산군 다양성 조건
}

# 
def build_etf_candidates():
    """
    ETF 후보군을 딕셔너리 리스트로 반환.

    각 항목 구성:
      ticker        : KRX 종목코드 (6자리 문자열)
      name          : ETF 한글명
      asset_class   : "equity" | "bond" | "money_market"
      risk_group    : "high" | "mid" | "low" | "very_low"
      listing_date  : 코스피 상장일 (YYYY-MM-DD 문자열)
      hsi_coverage  : HSI 5개 지표 적용 가능 여부 딕셔너리
                      True=적용 가능, False=신뢰도 낮거나 해당 없음
      note          : 선정 근거 및 HSI 활용 시 주의사항
    """
    candidates = [
        {
            "ticker":       "069500",
            "name":         "KODEX 200",
            "asset_class":  "equity",
            "risk_group":   "high",
            "listing_date": "2002-10-14",
            "hsi_coverage": {
                "return":   True,
                "ma_pos":   True,
                "momentum": True,
                "vol":      True,
                "rs":       True,
            },
            "note": "국내 대표 주식형 ETF로, 위험자산 기준 ETF 및 상대강도 기준 벤치마크로 활용 가능.",
        },
        {
            "ticker":       "114260",
            "name":         "KODEX 국고채3년",
            "asset_class":  "bond",
            "risk_group":   "low",
            "listing_date": "2009-07-29",
            "hsi_coverage": {
                "return":   True,
                "ma_pos":   True,
                "momentum": True,
                "vol":      True,
                "rs":       True,
            },
            "note": "국내 채권형 ETF로, 안전자산 또는 방어자산 역할을 검토할 수 있음.",
        },
        {
            "ticker":       "153130",
            "name":         "KODEX 단기채권PLUS",
            "asset_class":  "money_market",
            "risk_group":   "very_low",
            "listing_date": "2012-03-07",
            "hsi_coverage": {
                "return":   True,
                "ma_pos":   False,
                "momentum": False,
                "vol":      True,
                "rs":       True,
            },
            "note": "단기채권형 ETF로 현금성 자산 역할을 검토할 수 있으나, 가격이 단조롭게 움직여 일부 추세 신호의 해석력은 낮을 수 있음.",
        },
        {
            "ticker":       "148020",
            "name":         "KOSEF 국고채10년",
            "asset_class":  "bond",
            "risk_group":   "low",
            "listing_date": "2012-05-10",
            "hsi_coverage": {
                "return":   True,
                "ma_pos":   True,
                "momentum": True,
                "vol":      True,
                "rs":       True,
            },
            "note": "장기국채형 ETF로 채권형 방어자산 후보이나, 최종 선정 수 제한에 따라 다른 채권 ETF와 비교 후 선택.",
        },
        {
            "ticker":       "395160",
            "name":         "TIGER KOFR금리액티브(합성)",
            "asset_class":  "money_market",
            "risk_group":   "very_low",
            "listing_date": "2022-04-12",
            "hsi_coverage": {
                "return":   True,
                "ma_pos":   False,
                "momentum": False,
                "vol":      True,
                "rs":       True,
            },
            "note": "금리연동형 현금성 ETF 후보이나, 2022년 상장으로 2026년 기준 10년 이상 데이터 조건을 충족하지 못할 가능성이 큼.",
        },
    ]

    return candidates


def select_etf(candidates, criteria=None):
    """
    후보군에 선정 기준을 적용해 최종 ETF 리스트를 반환.

    적용 순서:
      Step 1. 데이터 연수 필터 (기준 D)
      Step 2. 자산군 다양성 확보 (기준 C) — 자산군별 1개씩 우선 선택
              같은 자산군 내 후보가 여러 개면 hsi_coverage True 개수가 많은 쪽 선택
      Step 3. 최대 선정 수 초과 시 hsi_coverage 합계 기준으로 상위 N개 유지

    Parameters
    ----------
    candidates : build_etf_candidates() 반환값
    criteria   : 선정 기준 딕셔너리. None이면 SELECTION_CRITERIA 사용.

    Returns
    -------
    selected : 최종 선정된 ETF 딕셔너리 리스트
               각 항목에 "data_years"(상장 후 연수)와 "data_over_10y" 키가 추가됨.
    """
    if criteria is None:
        criteria = SELECTION_CRITERIA

    min_years   = criteria["min_data_years"]
    ref_year    = criteria["reference_year"]
    max_count   = criteria["max_etf_count"]
    req_classes = criteria["required_asset_classes"]

    # ── Step 1. 데이터 연수 계산 및 필터 ────────────────────────
    passed = []
    for etf in candidates:
        listing_year = int(etf["listing_date"].split("-")[0])
        data_years   = ref_year - listing_year
        etf = etf.copy()
        etf["data_years"]   = data_years
        etf["data_over_10y"] = data_years >= min_years

        if etf["data_over_10y"]:
            passed.append(etf)

    # ── Step 2. 자산군별 최우선 후보 1개씩 선택 ─────────────────
    #    기준: hsi_coverage에서 True 개수가 많은 ETF 우선
    def coverage_score(etf):
        return sum(1 for v in etf["hsi_coverage"].values() if v)

    selected_by_class = {}
    for etf in passed:
        ac = etf["asset_class"]
        if ac not in selected_by_class:
            selected_by_class[ac] = etf
        else:
            # 같은 자산군이면 coverage 높은 쪽 유지
            if coverage_score(etf) > coverage_score(selected_by_class[ac]):
                selected_by_class[ac] = etf

    # req_classes 순서대로 정렬 (명시된 자산군 우선 포함)
    selected = []
    for ac in req_classes:
        if ac in selected_by_class:
            selected.append(selected_by_class[ac])

    # req_classes에 없는 자산군도 슬롯이 남으면 추가
    for ac, etf in selected_by_class.items():
        if ac not in req_classes and len(selected) < max_count:
            selected.append(etf)

    # ── Step 3. 최대 선정 수 초과 시 trimming ───────────────────
    if len(selected) > max_count:
        selected = sorted(selected, key=coverage_score, reverse=True)[:max_count]

    return selected


def print_selection_report(candidates, selected):
    """
    후보군 전체와 최종 선정 결과를 비교해 출력.

    Parameters
    ----------
    candidates : build_etf_candidates() 반환값
    selected   : select_etf() 반환값
    """
    selected_tickers = [e["ticker"] for e in selected]

    print("=" * 70)
    print("ETF 선정 보고서")
    print("=" * 70)
    print()

    print("[선정 기준]")
    print("  (A) 코스피(KRX 유가증권시장) 상장")
    print("  (B) 종가 데이터만으로 HSI 5개 지표 계산 가능")
    print("  (C) 자산군 다양성: equity / bond / money_market 각 1개 이상")
    print("  (D) 상장일 기준 " + str(SELECTION_CRITERIA["reference_year"])
          + "년 현재 " + str(SELECTION_CRITERIA["min_data_years"]) + "년 이상 데이터 확보")
    print("  (E) 최종 선정 수: " + str(SELECTION_CRITERIA["max_etf_count"]) + "개 이하")
    print()

    # 후보군 요약표
    print("[후보군 현황]")
    header = "{:<8} {:<22} {:<14} {:<8} {:<6} {:<10} {:<6}".format(
        "ticker", "name", "asset_class", "risk", "연수", "10년이상", "선정")
    print(header)
    print("-" * 70)

    for etf in candidates:
        listing_year = int(etf["listing_date"].split("-")[0])
        data_years   = SELECTION_CRITERIA["reference_year"] - listing_year
        over10       = "✓" if data_years >= SELECTION_CRITERIA["min_data_years"] else "✗"
        chosen       = "★ 선정" if etf["ticker"] in selected_tickers else "  탈락"
        print("{:<8} {:<22} {:<14} {:<8} {:<6} {:<10} {:<6}".format(
            etf["ticker"], etf["name"], etf["asset_class"],
            etf["risk_group"], str(data_years) + "년", over10, chosen
        ))

    print()

    # 선정 ETF 상세
    print("[최종 선정 ETF — " + str(len(selected)) + "종목]")
    for i, etf in enumerate(selected, 1):
        cov_true  = [k for k, v in etf["hsi_coverage"].items() if v]
        cov_false = [k for k, v in etf["hsi_coverage"].items() if not v]
        print()
        print("  " + str(i) + ". [" + etf["ticker"] + "] " + etf["name"])
        print("     asset_class  : " + etf["asset_class"])
        print("     risk_group   : " + etf["risk_group"])
        print("     상장일        : " + etf["listing_date"]
              + "  (" + str(etf["data_years"]) + "년)")
        print("     HSI 지표 적용 가능 (" + str(len(cov_true)) + "/5): "
              + ", ".join(cov_true))
        if cov_false:
            print("     HSI 지표 제한  (" + str(len(cov_false)) + "/5): "
                  + ", ".join(cov_false))
        print("     note         : " + etf.get("note","특이사항 검토 후 작성"))
    print()


def build_etf_universe(selected):
    """
    select_etf() 결과를 이후 코드에서 사용하는 ETF_UNIVERSE 딕셔너리 형태로 변환.

    Returns
    -------
    universe : {ticker: etf_dict} 형태의 딕셔너리
    """
    universe = {}
    for etf in selected:
        universe[etf["ticker"]] = etf
    return universe


# ──────────────────────────────────────────────────────────────
# 2. ETF 메타데이터 (선정 결과 확정본)
#    — build_etf_universe()로 자동 생성되지만,
#      선정 과정 없이 바로 임포트해 쓸 수 있도록 하드코딩도 유지
# ──────────────────────────────────────────────────────────────

ETF_UNIVERSE = {
    "069500": {
        "ticker":        "069500",
        "name":          "KODEX 200",
        "asset_class":   "equity",        # equity | bond | money_market
        "risk_group":    "high",           # high | mid | low | very_low
        "listing_date":  "2002-10-14",
        "data_over_10y": True,             # 현재(2026) 기준 10년 이상 여부
    },
    "114260": {
        "ticker":        "114260",
        "name":          "KODEX 국고채3년",
        "asset_class":   "bond",
        "risk_group":    "low",
        "listing_date":  "2009-07-29",
        "data_over_10y": True,
    },
    "153130": {
        "ticker":        "153130",
        "name":          "KODEX 단기채권PLUS",
        "asset_class":   "money_market",
        "risk_group":    "very_low",
        "listing_date":  "2012-03-07",
        "data_over_10y": True,             # 2026 기준 약 14년
    },
}

BENCHMARK_TICKER = "069500"   # 상대강도 기준 티커


# ──────────────────────────────────────────────────────────────
# 3. 기본 HSI 파라미터
#    딕셔너리로 관리 — dataclass/field 미사용
#    그리드 서치 시 이 딕셔너리를 교체하거나 개별 값을 덮어씀
# ──────────────────────────────────────────────────────────────

DEFAULT_PARAMS = {
    # ----------------------------------------------------------
    # HSI 원신호 계산 기간
    # ----------------------------------------------------------
    "return_window":      20,
    "ma_windows":         [20, 60, 120],
    "momentum_windows":   [21, 63, 126],
    "vol_window":         20,
    "rs_window":          21,

    # ----------------------------------------------------------
    # 스케일링 방식
    # ----------------------------------------------------------
    # 기본 기준은 분위수 방식(rank)으로 둔다.
    # zscore는 비교용 보조 실험으로 Grid Search에서 함께 확인할 수 있다.
    "standardize":        "rank",      # "rank" 또는 "zscore"

    # ----------------------------------------------------------
    # rolling 표준화 기준
    # ----------------------------------------------------------
    "std_window":         252,
    "std_min_periods":    60,

    # ----------------------------------------------------------
    # 점수 변환 기준 - "zscore" 또는 "rank" ; 
    # ----------------------------------------------------------
    # zscore 방식: z값을 -clip_z ~ +clip_z 범위로 자른 뒤 -10~+10 변환
    # rank 방식: 분위수 변환값 -1~+1을 -10~+10 변환
    "clip_z":             2.5,
    "rank_clip":          1.0,

    # ----------------------------------------------------------
    # HSI 상태 판단 기준 - 매수/주의 경계값
    # ----------------------------------------------------------
    "direction_threshold": 0.3,
}



# ──────────────────────────────────────────────────────────────
# 4. 데이터 로더
# ──────────────────────────────────────────────────────────────

def load_price_data(tickers=None, start="2012-03-07", end=None,
                    source="yfinance", csv_dir="./data"):
    """
    종가(adjusted close) DataFrame 반환.
    컬럼 = ticker, 인덱스 = 날짜(DatetimeIndex).

    Parameters
    ----------
    tickers  : 로드할 티커 목록 (리스트). None이면 ETF_UNIVERSE 전체.
    start    : 시작일 문자열 'YYYY-MM-DD'
    end      : 종료일 문자열. None이면 오늘.
    source   : 'yfinance' 또는 'csv'
    csv_dir  : source='csv'일 때 파일 탐색 경로.
               파일명 규칙: {csv_dir}/{ticker}.csv, 컬럼 'Date','Close' 필수.
    """
    if tickers is None:
        tickers = list(ETF_UNIVERSE.keys())

    if source == "yfinance":
        try:
            import yfinance as yf
        except ImportError as e:
            raise ImportError("pip install yfinance 후 재시도하세요.") from e

        yf_tickers = [t + ".KS" for t in tickers]   # 한국 거래소 접미사
        raw = yf.download(yf_tickers, start=start, end=end,
                          auto_adjust=True, progress=False)

        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"].copy()
            close.columns = [c.replace(".KS", "") for c in close.columns]
        else:
            close = raw[["Close"]].copy()
            close.columns = [tickers[0]]

    elif source == "csv":
        frames = {}
        for t in tickers:
            path = os.path.join(csv_dir, t + ".csv")
            if not os.path.exists(path):
                raise FileNotFoundError("파일을 찾을 수 없습니다: " + path)
            df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
            frames[t] = df["Close"]
        close = pd.DataFrame(frames)

    else:
        raise ValueError("지원하지 않는 source: " + source)

    close.index = pd.to_datetime(close.index)
    close = close.sort_index()
    close = close.ffill()        # 공휴일 결측 전진 채움
    close = close.dropna(how="all")
    return close


# ──────────────────────────────────────────────────────────────
# 5. HSI 개별 지표 계산 함수
#    부호 규칙 (안내서 4절):
#      양호 방향 → 음수 / 위험 방향 → 양수
# ──────────────────────────────────────────────────────────────

def _sign_flip(df):
    """양호 신호(양수)를 음수로 반전해 '위험 방향=양수' 기준으로 통일."""
    return -df


def calc_return(prices, window=20):
    """
    최근 수익률 = (P_t / P_{t-window}) - 1
    높을수록 양호 → 부호 반전.
    """
    ret = prices.pct_change(window)
    return _sign_flip(ret)


def calc_ma_position(prices, windows=None):
    """
    이동평균 대비 위치 = (P_t / MA_t) - 1
    여러 이동평균의 평균을 반환.
    가격이 MA 위 → 양호 → 부호 반전.
    """
    if windows is None:
        windows = [20, 60, 120]
    signals = []
    for w in windows:
        ma = prices.rolling(w, min_periods=w).mean()
        signals.append((prices / ma) - 1)
    combined = pd.concat(signals).groupby(level=0).mean()
    return _sign_flip(combined)


def calc_momentum(prices, windows=None):
    """
    모멘텀 = n일 수익률 (1개월≈21, 3개월≈63, 6개월≈126 거래일).
    여러 기간 평균 사용. 양수=양호 → 부호 반전.
    """
    if windows is None:
        windows = [21, 63, 126]
    signals = []
    for w in windows:
        signals.append(prices.pct_change(w))
    combined = pd.concat(signals).groupby(level=0).mean()
    return _sign_flip(combined)


def calc_volatility(prices, window=20, annualize=True):
    """
    변동성 = 일간 수익률의 rolling 표준편차.
    높을수록 위험 → 양수=위험이므로 부호 반전 없이 반환.
    annualize=True이면 연환산(×√252).
    """
    daily_ret = prices.pct_change()
    vol = daily_ret.rolling(window, min_periods=window).std()
    if annualize:
        vol = vol * np.sqrt(252)
    return vol   # 부호 반전 없음


def calc_relative_strength(prices, benchmark=BENCHMARK_TICKER, window=21):
    """
    상대강도 = 종목 수익률(window) - 기준 수익률(window).
    기준보다 강하면 양호 → 부호 반전.
    """
    if benchmark not in prices.columns:
        raise ValueError(
            "benchmark 티커 '" + benchmark + "'가 prices 컬럼에 없습니다. "
            "사용 가능 컬럼: " + str(list(prices.columns))
        )
    ret    = prices.pct_change(window)
    bm_ret = ret[[benchmark]]
    rs     = ret.subtract(bm_ret.values, axis=0)
    return _sign_flip(rs)


# ──────────────────────────────────────────────────────────────
# 6. 표준화
# ──────────────────────────────────────────────────────────────

def standardize_zscore(signal, window=252, min_periods=60):
    """
    Rolling z-score 표준화 (미래 데이터 누출 방지).
    z = (x - rolling_mean) / rolling_std
    """
    roll_mean = signal.rolling(window, min_periods=min_periods).mean()
    roll_std  = signal.rolling(window, min_periods=min_periods).std()
    z = (signal - roll_mean) / roll_std.replace(0, np.nan)
    return z


def standardize_rank(signal, window=252, min_periods=60):
    """
    Rolling 분위수 표준화.
    현재 값이 과거 window 내에서 어느 분위에 있는지 계산 (0~1).
    이후 -1~+1로 선형 변환 (0.5=중립=0).
    """
    def _rank_pct(x):
        arr = pd.Series(x)
        if arr.isna().all():
            return np.nan
        return float(arr.rank(pct=True).iloc[-1])

    ranked = signal.rolling(window, min_periods=min_periods).apply(
        _rank_pct, raw=False
    )
    return (ranked - 0.5) * 2   # 0~1 → -1~+1


def clip_to_score(standardized, clip_z=2.5, scale=10.0):
    """
    표준화된 지표를 -10 ~ +10 범위로 변환.
    1) [-clip_z, +clip_z] 범위로 clipping
    2) (z / clip_z) * scale 으로 선형 변환
    """
    clipped = standardized.clip(-clip_z, clip_z)
    return (clipped / clip_z) * scale


# ──────────────────────────────────────────────────────────────
# 7. HSI 계산
#    params 딕셔너리를 받아 동작 — 그리드 서치와 바로 연결됨
# ──────────────────────────────────────────────────────────────

def compute_hsi(prices, params=None, benchmark=BENCHMARK_TICKER):
    """
    HSI_direction 및 HSI_intensity 계산.

    Parameters
    ----------
    prices    : load_price_data() 반환값 (종가 DataFrame)
    params    : 파라미터 딕셔너리. None이면 DEFAULT_PARAMS 사용.
    benchmark : 상대강도 기준 티커

    Returns
    -------
    pd.DataFrame — 컬럼 구성 (티커별):
      {ticker}_direction  : -1 ~ +1  (음수=양호/기회, 양수=위험)
      {ticker}_intensity  :  0 ~ +1  (신호 강도)
      {ticker}_signal     : 'buy' | 'watch' | 'caution'
    """
    if params is None:
        params = DEFAULT_PARAMS

    # 파라미터 꺼내기
    return_window      = params["return_window"]
    ma_windows         = params["ma_windows"]
    momentum_windows   = params["momentum_windows"]
    vol_window         = params["vol_window"]
    rs_window          = params["rs_window"]
    standardize        = params["standardize"]
    std_window         = params["std_window"]
    std_min_periods    = params["std_min_periods"]
    clip_z             = params["clip_z"]
    direction_threshold = params["direction_threshold"]

    # 개별 지표 계산 (부호: 음수=양호, 양수=위험)
    raw_signals = {
        "return":   calc_return(prices, window=return_window),
        "ma_pos":   calc_ma_position(prices, windows=ma_windows),
        "momentum": calc_momentum(prices, windows=momentum_windows),
        "vol":      calc_volatility(prices, window=vol_window),
        "rs":       calc_relative_strength(prices, benchmark=benchmark,
                                           window=rs_window),
    }

    # 표준화 → -10~+10 스코어 변환
    scored_signals = {}

    for name, sig in raw_signals.items():
        if standardize == "zscore":
            # z-score 방식:
            # 평균과 표준편차 기준으로 현재 신호가 얼마나 특이한지 계산
            std_sig = standardize_zscore(
                sig,
                window=std_window,
                min_periods=std_min_periods
            )
            scored_signals[name] = clip_to_score(
                std_sig,
                clip_z=clip_z,
                scale=10.0
            )

        elif standardize == "rank":
            # 분위수 방식:
            # 과거 window 안에서 현재 값이 어느 순위인지 계산
            std_sig = standardize_rank(
                sig,
                window=std_window,
                min_periods=std_min_periods
            )
            rank_clip = params.get("rank_clip", 1.0)
            scored_signals[name] = clip_to_score(
                std_sig,
                clip_z=rank_clip,
                scale=10.0
            )

        else:
            raise ValueError(
                "지원하지 않는 standardize 방식입니다: " + str(standardize)
            )

    # HSI direction / intensity (안내서 6절 공식)
    M = len(scored_signals) * 10.0   # 지표 수 × 10

    results = {}
    for ticker in prices.columns:
        ticker_scores = pd.DataFrame(
            {k: v[ticker] for k, v in scored_signals.items()
             if ticker in v.columns}
        )

        # V_plus = Σ max(s_i, 0),  V_minus = Σ max(-s_i, 0)
        v_plus  = ticker_scores.clip(lower=0).sum(axis=1)
        v_minus = ticker_scores.clip(upper=0).abs().sum(axis=1)

        direction = (v_plus - v_minus) / M
        intensity = (v_plus + v_minus) / M

        # 신호 구간 레이블 (안내서 7절)
        signal = pd.Series("watch", index=direction.index, dtype=str)
        signal[direction < -direction_threshold] = "buy"
        signal[direction >  direction_threshold] = "caution"

        results[ticker + "_direction"] = direction
        results[ticker + "_intensity"] = intensity
        results[ticker + "_signal"]    = signal

    return pd.DataFrame(results)


# ──────────────────────────────────────────────────────────────
# 8. 그리드 서치
#    탐색할 파라미터 후보를 딕셔너리로 넘기면
#    모든 조합을 순회하며 compute_hsi를 실행하고 결과를 모음
# ──────────────────────────────────────────────────────────────

def run_grid_search(prices, param_grid, benchmark=BENCHMARK_TICKER,
                    eval_fn=None):
    """
    HSI 파라미터 그리드 서치.

    Parameters
    ----------
    prices     : load_price_data() 반환값
    param_grid : 탐색할 파라미터 후보 딕셔너리.
                 각 키에 후보값 리스트를 넣으면 모든 조합을 순회.
                 예)
                   {
                     "return_window":       [10, 20],
                     "vol_window":          [20, 60],
                     "standardize":         ["zscore", "rank"],
                     "direction_threshold": [0.2, 0.3, 0.4],
                   }
                 param_grid에 없는 파라미터는 DEFAULT_PARAMS 값을 사용.

    eval_fn    : 평가 함수 (선택). hsi_df를 받아 숫자 하나를 반환.
                 None이면 HSI 결과만 저장하고 score=None.
                 예) lambda hsi_df: hsi_df["069500_direction"].mean()

    Returns
    -------
    results : 딕셔너리 리스트. 각 원소는
              {"params": {...}, "hsi": hsi_df, "score": score} 형태.
    summary : 파라미터 조합별 score를 정리한 DataFrame (eval_fn 있을 때만 유용).
    """
    # 탐색 키와 후보값 분리
    keys   = list(param_grid.keys())
    values = list(param_grid.values())

    results = []

    for combo in itertools.product(*values):
        # DEFAULT_PARAMS를 복사하고 그리드 값으로 덮어쓰기
        params = DEFAULT_PARAMS.copy()
        for k, v in zip(keys, combo):
            params[k] = v

        # HSI 계산
        hsi_df = compute_hsi(prices, params=params, benchmark=benchmark)

        # 평가
        score = eval_fn(hsi_df) if eval_fn is not None else None

        results.append({
            "params": params.copy(),
            "hsi":    hsi_df,
            "score":  score,
        })

    # 요약 테이블 (파라미터 + score만 모음)
    summary_rows = []
    for r in results:
        row = {k: r["params"][k] for k in keys}
        row["score"] = r["score"]
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)

    return results, summary


# ──────────────────────────────────────────────────────────────
# 9. 편의 출력 함수
# ──────────────────────────────────────────────────────────────

def print_etf_metadata():
    """선정 ETF 메타데이터 출력."""
    print("=" * 70)
    print("HSI 프로젝트 — 선정 ETF 목록")
    print("=" * 70)
    for meta in ETF_UNIVERSE.values():
        data_tag = "10년 이상 ✓" if meta["data_over_10y"] else "10년 미만 △"
        print("\n[" + meta["ticker"] + "] " + meta["name"])
        print("  asset_class : " + meta["asset_class"])
        print("  risk_group  : " + meta["risk_group"])
        print("  상장일       : " + meta["listing_date"])
        print("  데이터 분량  : " + data_tag)
        print("  note        : " + meta.get("note","특이사항 검토 후 작성"))
    print()


def latest_hsi_snapshot(hsi_df):
    """가장 최근 날짜 기준 HSI 요약 테이블 반환."""
    last = hsi_df.dropna(how="all").iloc[[-1]].T
    last.columns = ["value"]
    return last

def save_selected_etf_universe(selected, output_path=None):
    """
    최종 선정 ETF 목록을 CSV로 저장.

    저장 파일:
      output/tables/selected_etf_universe.csv
    """
    if output_path is None:
        output_path = TABLE_DIR / "selected_etf_universe.csv"

    rows = []
    for etf in selected:
        row = {
            "ticker": etf.get("ticker"),
            "name": etf.get("name"),
            "asset_class": etf.get("asset_class"),
            "risk_group": etf.get("risk_group"),
            "listing_date": etf.get("listing_date"),
            "data_years": etf.get("data_years"),
            "data_over_10y": etf.get("data_over_10y"),
            "note": etf.get("note", "메모필요"),
        }

        hsi_coverage = etf.get("hsi_coverage", {})
        for key, value in hsi_coverage.items():
            row["hsi_" + key] = value

        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("[저장 완료] selected_etf_universe:", output_path)
    return df


def save_price_outputs(prices):
    """
    가격 데이터를 CSV로 저장.

    저장 파일:
      data/processed/daily_prices.csv
    """
    output_path = PROCESSED_DIR / "daily_prices.csv"
    prices.to_csv(output_path, encoding="utf-8-sig")

    print("[저장 완료] daily_prices:", output_path)
    return output_path


def make_monthly_prices(prices):
    """
    일별 가격을 월말 가격으로 변환.

    주의:
      월말 가격은 그 달 마지막 거래일 가격을 사용한다.
      현재 환경에서는 "ME"를 우선 사용하고,
      다른 환경에서 "ME"가 지원되지 않으면 "M"으로 한 번 더 시도한다.
    """
    try:
        monthly_prices = prices.resample("ME").last()
    except ValueError:
        monthly_prices = prices.resample("M").last()

    return monthly_prices


def make_monthly_returns(monthly_prices):
    """
    월말 가격으로 월간 수익률 계산.
    """
    monthly_returns = monthly_prices.pct_change()
    return monthly_returns


def save_monthly_outputs(prices):
    """
    월말 가격과 월간 수익률 저장.

    저장 파일:
      data/processed/monthly_prices.csv
      data/processed/monthly_returns.csv
    """
    monthly_prices = make_monthly_prices(prices)
    monthly_returns = make_monthly_returns(monthly_prices)

    monthly_prices_path = PROCESSED_DIR / "monthly_prices.csv"
    monthly_returns_path = PROCESSED_DIR / "monthly_returns.csv"

    monthly_prices.to_csv(monthly_prices_path, encoding="utf-8-sig")
    monthly_returns.to_csv(monthly_returns_path, encoding="utf-8-sig")

    print("[저장 완료] monthly_prices:", monthly_prices_path)
    print("[저장 완료] monthly_returns:", monthly_returns_path)

    return monthly_prices, monthly_returns


def save_hsi_outputs(hsi_df, standardize_name="rank"):
    """
    HSI 계산 결과 저장.

    저장 파일:
      output/tables/hsi_summary_rank.csv
      output/tables/hsi_latest_snapshot_rank.csv

    standardize_name:
      rank 또는 zscore
    """
    hsi_summary_path = TABLE_DIR / f"hsi_summary_{standardize_name}.csv"
    latest_snapshot_path = TABLE_DIR / f"hsi_latest_snapshot_{standardize_name}.csv"

    hsi_df.to_csv(hsi_summary_path, encoding="utf-8-sig")

    latest = latest_hsi_snapshot(hsi_df)
    latest.to_csv(latest_snapshot_path, encoding="utf-8-sig")

    print("[저장 완료] hsi_summary:", hsi_summary_path)
    print("[저장 완료] hsi_latest_snapshot:", latest_snapshot_path)

    return latest


def save_grid_search_summary(summary, output_name="grid_search_summary.csv"):
    """
    Grid Search 요약 결과 저장.

    저장 파일:
      output/tables/grid_search_summary.csv
    """
    output_path = TABLE_DIR / output_name
    summary.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("[저장 완료] grid_search_summary:", output_path)
    return output_path
# ──────────────────────────────────────────────────────────────
# 10. 실행 예시 (직접 실행 시)
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 70)
    print("HSI 신호 계산 모듈 실행 시작")
    print("=" * 70)
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("DATA_DIR    :", DATA_DIR)
    print("OUTPUT_DIR  :", OUTPUT_DIR)
    print()

    # ── Step 1. ETF 후보군 생성 및 선정 ──────────────────────────
    candidates = build_etf_candidates()
    selected   = select_etf(candidates)
    print_selection_report(candidates, selected)

    # 선정 ETF 목록 저장
    selected_df = save_selected_etf_universe(selected)

    # 선정 결과로 ETF_UNIVERSE 갱신 (이후 코드에서 selected 기준으로 동작)
    ETF_UNIVERSE = build_etf_universe(selected)

    # ── Step 2. 데이터 로드 ───────────────────────────────────────
    print("데이터 로드 중 (yfinance)...")
    tickers = list(ETF_UNIVERSE.keys())

    try:
        prices = load_price_data(
            tickers=tickers,
            start="2012-03-07",
            source="yfinance"
        )

        print("로드 완료: " + str(prices.shape[0]) + "일 × "
              + str(prices.shape[1]) + "개 종목")
        print(prices.tail(3))
        print()

        # 일별 가격 저장
        save_price_outputs(prices)

        # 월말 가격 / 월간 수익률 저장
        monthly_prices, monthly_returns = save_monthly_outputs(prices)

        print("월말 가격 확인:")
        print(monthly_prices.tail(3))
        print()

        print("월간 수익률 확인:")
        print(monthly_returns.tail(3))
        print()

        # ── Step 3. 기본 파라미터로 HSI 계산 ─────────────────────
        # 기본 기준: 분위수(rank) 방식
        print("─" * 70)
        print("최근 날짜 HSI 스냅샷 (기본 파라미터: rank)")
        print("─" * 70)

        rank_params = DEFAULT_PARAMS.copy()
        rank_params["standardize"] = "rank"

        hsi_rank = compute_hsi(
            prices,
            params=rank_params,
            benchmark=BENCHMARK_TICKER
        )

        latest_rank = save_hsi_outputs(
            hsi_rank,
            standardize_name="rank"
        )

        print(latest_rank.to_string())
        print()

        # 비교 기준: z-score 방식
        print("─" * 70)
        print("최근 날짜 HSI 스냅샷 (비교 파라미터: zscore)")
        print("─" * 70)

        zscore_params = DEFAULT_PARAMS.copy()
        zscore_params["standardize"] = "zscore"

        hsi_zscore = compute_hsi(
            prices,
            params=zscore_params,
            benchmark=BENCHMARK_TICKER
        )

        latest_zscore = save_hsi_outputs(
            hsi_zscore,
            standardize_name="zscore"
        )

        print(latest_zscore.to_string())
        print()

        # ── Step 4. 그리드 서치 ───────────────────────────────────
        print("─" * 70)
        print("그리드 서치 실행")
        print("─" * 70)

        param_grid = {
            "return_window":       [10, 20],
            "vol_window":          [20, 60],
            "standardize":         ["rank", "zscore"],
            "direction_threshold": [0.2, 0.3, 0.4],
        }

        # 평가 함수 예시: 069500의 direction 절댓값 평균 (신호 강도 지표)
        # 주의:
        # 현재 eval_fn은 최종 전략 성과 평가가 아니라 예비 점검용이다.
        # 최종 Grid Search에서는 CAGR, MDD, Sharpe, Turnover 등을 연결해야 한다.
        def eval_fn(hsi_df):
            return hsi_df["069500_direction"].abs().mean()

        results, summary = run_grid_search(
            prices,
            param_grid,
            eval_fn=eval_fn
        )

        save_grid_search_summary(
            summary,
            output_name="grid_search_summary_preliminary.csv"
        )

        print("총 조합 수: " + str(len(results)))
        print()
        print("score 상위 5개 조합:")
        print(
            summary
            .sort_values("score", ascending=False)
            .head(5)
            .to_string(index=False)
        )

        print()
        print("=" * 70)
        print("HSI 신호 계산 모듈 실행 완료")
        print("=" * 70)
        print("저장 위치:")
        print("  - data/processed/daily_prices.csv")
        print("  - data/processed/monthly_prices.csv")
        print("  - data/processed/monthly_returns.csv")
        print("  - output/tables/selected_etf_universe.csv")
        print("  - output/tables/hsi_summary_rank.csv")
        print("  - output/tables/hsi_latest_snapshot_rank.csv")
        print("  - output/tables/hsi_summary_zscore.csv")
        print("  - output/tables/hsi_latest_snapshot_zscore.csv")
        print("  - output/tables/grid_search_summary_preliminary.csv")

    except Exception as e:
        print("[주의] 실행 중 오류 발생: " + str(e))
        print("source='csv' 모드로 ./data/{ticker}.csv 파일을 사용하거나")
        print("yfinance 설치 후 재시도하세요: pip install yfinance")
        print()
        print("추가 확인 항목:")
        print("  1. 인터넷 연결 여부")
        print("  2. Anaconda 환경에서 실행 중인지 여부")
        print("  3. yfinance 설치 여부")
        print("  4. ETF 티커 데이터 다운로드 가능 여부")