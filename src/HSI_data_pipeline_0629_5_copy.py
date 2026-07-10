"""
HSI (Hourglass Signal Index) — 데이터 수집 및 산출물 생성 모듈
==============================================================
담당: 데이터 수집·전처리 및 HSI 기본 입력 신호 산출

산출물 체크리스트 (주원 파트):
  ① ETF 유니버스 기준 확인       → build_etf_candidates() / select_etf()
  ② ETF 기본정보표               → make_etf_info_table()
  ③ 자산군 분류표                → make_asset_class_table()
     ├─ 추종 자산 구분 포함       → underlying_asset 필드 (주식형/채권형/금/달러/원자재)
     └─ 분류 논의 항목 출력       → print_discussion_notes()
  ④ 상장일 및 데이터 기간 확인   → check_data_period()
  ⑤ 결측치 확인                  → check_missing_values()
  ⑤-2. 거래량/거래대금 유동성 확인 → check_liquidity()
  ⑥ 월말 가격표                  → make_monthly_price_table()
  ⑦ 월간 수익률표                → make_monthly_return_table()
  ⑧ HSI 기본 입력 신호표         → make_hsi_signal_table()

필드 역할 구분:
  note            : 선정 근거, HSI 지표 적용 시 주의사항
  discussion_note : 자산군·추종 자산 분류가 애매한 경우에만 기재
                    (명확한 경우 빈 문자열 "")

산출물 통합:
  모든 표 산출물은 개별 CSV가 아니라 하나의 엑셀 워크북으로 합본 저장한다.
  → build_data_workbook() / save_data_workbook()  →  hsi_data_bundle.xlsx
     각 산출물을 원래 형태(wide/tidy) 그대로 표별 시트로 분리.
  처리 과정·제외 사유 기록은 preprocessing_log.md (사람용 보고서)로 별도 저장.

범위 구분 (데이터 파트):
  본 모듈은 ETF 정보·자산군, 월말 가격·월간 수익률, HSI 입력 신호,
  점수화 중간 산출물, 최신 snapshot, 품질 점검표까지만 담당한다.
  Grid Search / Robustness / Turnover·거래비용 / 백테스트는 후속 파트 담당이며
  본 모듈 범위에서 제외한다.
"""

import os
import unicodedata
import warnings
from collections import OrderedDict

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ──────────────────────────────────────────────────────────────
# 1. ETF 후보군 정의 및 선정 기준
#
#    선정 기준 (HSI 안내서 기반):
#      (A) 코스피(KRX 유가증권시장) 상장 종목
#      (B) 종가 데이터만으로 HSI 5개 지표 계산 가능
#      (C) 자산군 다양성: equity / bond / money_market 각 1개 이상
#      (D) 상장일 기준 현재(2026) 10년 이상 데이터 확보
#      (E) 최종 선정 수: 3개 이하
# ──────────────────────────────────────────────────────────────

SELECTION_CRITERIA = {
    "min_data_years":         10,
    "reference_year":         2026,
    "max_etf_count":          3,
    "required_asset_classes": ["equity", "bond", "money_market"],
}


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
                      True=완전적용, False=신뢰도 낮거나 해당없음
      note          : 선정 근거 및 HSI 활용 시 주의사항
    """
    candidates = [
        {
            "ticker":           "069500",
            "name":             "KODEX 200",
            "asset_class":      "equity",
            "underlying_asset": "주식형",   # 주식형 | 채권형 | 금 | 달러 | 원자재
            "risk_group":       "high",
            "listing_date":     "2002-10-14",
            "hsi_coverage": {
                "return":   True,
                "ma_pos":   True,
                "momentum": True,
                "vol":      True,
                "rs":       True,   # 기준(benchmark) 역할
            },
            "note":             "국내 주식시장 대표 지수. 상대강도 계산 시 기준(benchmark)으로 사용.",
            "discussion_note":  "",  # 분류 명확 — 논의 불필요
        },
        {
            "ticker":           "114260",
            "name":             "KODEX 국고채3년",
            "asset_class":      "bond",
            "underlying_asset": "채권형",
            "risk_group":       "low",
            "listing_date":     "2009-07-29",
            "hsi_coverage": {
                "return":   True,
                "ma_pos":   True,
                "momentum": True,
                "vol":      True,   # 절댓값 작음 — 자산군 내 상대 비교 권장
                "rs":       True,   # 069500 대비 계산
            },
            "note":             "국고채 3년물 추종. 변동성이 작아 vol 지표는 자산군 내 상대 비교 권장.",
            "discussion_note":  "",  # 채권형 분류 명확 — 논의 불필요
        },
        {
            "ticker":           "153130",
            "name":             "KODEX 단기채권PLUS",
            "asset_class":      "money_market",
            "underlying_asset": "채권형",   # 기초자산은 국채·통안채 등 단기채권
            "risk_group":       "very_low",
            "listing_date":     "2012-03-07",
            "hsi_coverage": {
                "return":   True,   # 단조 증가 — 절댓값보다 상대 비교 활용
                "ma_pos":   False,  # 가격 단조증가로 신뢰도 낮음
                "momentum": False,  # 변화폭 미미
                "vol":      True,   # 위험도 척도로 활용
                "rs":       True,   # 069500 대비 계산
            },
            "note":            "단기 채권 ETF. 가격이 단조증가하여 ma_pos·momentum 적용 제한.",
            "discussion_note": (
                "기초자산은 국채·통안채 등 단기채권(채권형)이나, 가격 단조증가·낮은 변동성으로 "
                "HSI 분류상 현금성자산(money_market)으로 배치. "
                "5개 추종 자산 분류(주식형/채권형/금/달러/원자재) 중 채권형에 해당하나 "
                "실질 특성은 현금성에 가까워 asset_class와 underlying_asset이 불일치. "
                "HSI 설계 파트에서 슬롯 배치 시 이 점을 감안 요망."
            ),
        },
        # ── 아래부터 탈락 후보 (기준 미충족 시 자동 제외됨) ─────────────────
        {
            "ticker":           "148020",
            "name":             "KOSEF 국고채10년",
            "asset_class":      "bond",
            "underlying_asset": "채권형",
            "risk_group":       "low",
            "listing_date":     "2012-05-10",
            "hsi_coverage": {
                "return":   True,
                "ma_pos":   True,
                "momentum": True,
                "vol":      True,
                "rs":       True,
            },
            "note":            "국고채 10년물 추종. bond 자산군에서 114260과 경쟁 후 커버리지 점수로 탈락.",
            "discussion_note": "",  # 채권형 분류 명확 — 논의 불필요
        },
        {
            "ticker":           "395160",
            "name":             "TIGER KOFR금리액티브(합성)",
            "asset_class":      "money_market",
            "underlying_asset": "채권형",   # KOFR 금리 추종 → 채권형에 가장 가깝지만 경계 모호
            "risk_group":       "very_low",
            "listing_date":     "2022-04-12",
            "hsi_coverage": {
                "return":   True,
                "ma_pos":   False,
                "momentum": False,
                "vol":      True,
                "rs":       True,
            },
            "note":            "상장 4년으로 10년 기준 미충족. 데이터 연수 필터(기준 D)에서 자동 탈락.",
            "discussion_note": (
                "KOFR(한국 무위험 지표금리)를 스왑 계약으로 합성 복제하는 ETF. "
                "5개 추종 자산 분류 중 채권형으로 배치하나, 실질적으로는 초단기 현금성에 가깝고 "
                "합성 구조(스왑)로 인한 거래상대방 신용위험이 존재. "
                "또한 데이터 연수 부족(4년)으로 현재 유니버스에서 제외 — 향후 편입 시 재논의 필요."
            ),
        },
    ]
    return candidates


def select_etf(candidates, criteria=None):
    """
    후보군에 선정 기준을 적용해 최종 ETF 리스트를 반환.

    적용 순서:
      Step 1. 데이터 연수 필터 (기준 D)
      Step 2. 자산군별 최우선 후보 1개 선택 (hsi_coverage True 개수 기준)
      Step 3. 최대 선정 수 초과 시 상위 N개 유지
    """
    if criteria is None:
        criteria = SELECTION_CRITERIA

    min_years   = criteria["min_data_years"]
    ref_year    = criteria["reference_year"]
    max_count   = criteria["max_etf_count"]
    req_classes = criteria["required_asset_classes"]

    def coverage_score(etf):
        return sum(1 for v in etf["hsi_coverage"].values() if v)

    # Step 1. 데이터 연수 계산 및 필터
    passed = []
    for etf in candidates:
        listing_year = int(etf["listing_date"].split("-")[0])
        data_years   = ref_year - listing_year
        etf = etf.copy()
        etf["data_years"]    = data_years
        etf["data_over_10y"] = data_years >= min_years
        if etf["data_over_10y"]:
            passed.append(etf)

    # Step 2. 자산군별 최우선 후보 선택
    selected_by_class = {}
    for etf in passed:
        ac = etf["asset_class"]
        if ac not in selected_by_class:
            selected_by_class[ac] = etf
        else:
            if coverage_score(etf) > coverage_score(selected_by_class[ac]):
                selected_by_class[ac] = etf

    selected = []
    for ac in req_classes:
        if ac in selected_by_class:
            selected.append(selected_by_class[ac])

    for ac, etf in selected_by_class.items():
        if ac not in req_classes and len(selected) < max_count:
            selected.append(etf)

    # Step 3. 최대 선정 수 초과 시 trimming
    if len(selected) > max_count:
        selected = sorted(selected, key=coverage_score, reverse=True)[:max_count]

    return selected


def print_selection_report(candidates, selected):
    """후보군 전체와 최종 선정 결과를 비교해 출력."""
    selected_tickers = [e["ticker"] for e in selected]

    # ── 선정 기준 출력 ─────────────────────────────────────
    print("=" * 72)
    print("ETF 선정 보고서")
    print("=" * 72)
    print()
    print("[선정 기준]")
    print("  (A) 코스피(KRX 유가증권시장) 상장")
    print("  (B) 종가 데이터만으로 HSI 5개 지표 계산 가능")
    print("  (C) 자산군 다양성: equity / bond / money_market 각 1개 이상")
    print(f"  (D) 상장일 기준 {SELECTION_CRITERIA['reference_year']}년 현재 "
          f"{SELECTION_CRITERIA['min_data_years']}년 이상 데이터 확보")
    print(f"  (E) 최종 선정 수: {SELECTION_CRITERIA['max_etf_count']}개 이하")
    print()

    # ── 후보군 요약표 ─────────────────────────────────────
    print("[후보군 현황]")
    print(f"{'ticker':<8} {'name':<22} {'asset_class':<14} "
          f"{'risk':<10} {'연수':<6} {'10년↑':<6} {'결과':<6}")
    print("-" * 72)
    for etf in candidates:
        listing_year = int(etf["listing_date"].split("-")[0])
        data_years   = SELECTION_CRITERIA["reference_year"] - listing_year
        over10       = "✓" if data_years >= SELECTION_CRITERIA["min_data_years"] else "✗"
        chosen       = "★ 선정" if etf["ticker"] in selected_tickers else "  탈락"
        print(f"{etf['ticker']:<8} {etf['name']:<22} {etf['asset_class']:<14} "
              f"{etf['risk_group']:<10} {str(data_years)+'년':<6} {over10:<6} {chosen:<6}")
    print()

    # ── 선정 ETF 상세 ─────────────────────────────────────
    print(f"[최종 선정 ETF — {len(selected)}종목]")
    for i, etf in enumerate(selected, 1):
        cov_true  = [k for k, v in etf["hsi_coverage"].items() if v]
        cov_false = [k for k, v in etf["hsi_coverage"].items() if not v]
        print()
        print(f"  {i}. [{etf['ticker']}] {etf['name']}")
        print(f"     asset_class  : {etf['asset_class']}")
        print(f"     risk_group   : {etf['risk_group']}")
        print(f"     상장일        : {etf['listing_date']}  ({etf['data_years']}년)")
        print(f"     HSI 지표 적용 ({len(cov_true)}/5): {', '.join(cov_true)}")
        if cov_false:
            print(f"     HSI 지표 제한 ({len(cov_false)}/5): {', '.join(cov_false)}")
        print(f"     note         : {etf['note']}")
    print()


def build_etf_universe(selected):
    """select_etf() 결과를 {ticker: etf_dict} 딕셔너리로 변환."""
    return {etf["ticker"]: etf for etf in selected}


# ──────────────────────────────────────────────────────────────
# 2. ETF 메타데이터 (선정 결과 확정본)
#    — 선정 과정 없이 바로 임포트해 쓸 수 있도록 하드코딩 유지
# ──────────────────────────────────────────────────────────────

ETF_UNIVERSE = {
    "069500": {
        "ticker":           "069500",
        "name":             "KODEX 200",
        "asset_class":      "equity",
        "underlying_asset": "주식형",
        "risk_group":       "high",
        "listing_date":     "2002-10-14",
        "data_over_10y":    True,
        "note":             "국내 주식시장 대표 지수. 상대강도 계산 시 기준(benchmark)으로 사용.",
        "discussion_note":  "",
    },
    "114260": {
        "ticker":           "114260",
        "name":             "KODEX 국고채3년",
        "asset_class":      "bond",
        "underlying_asset": "채권형",
        "risk_group":       "low",
        "listing_date":     "2009-07-29",
        "data_over_10y":    True,
        "note":             "국고채 3년물 추종. 변동성이 작아 vol 지표는 자산군 내 상대 비교 권장.",
        "discussion_note":  "",
    },
    "153130": {
        "ticker":           "153130",
        "name":             "KODEX 단기채권PLUS",
        "asset_class":      "money_market",
        "underlying_asset": "채권형",
        "risk_group":       "very_low",
        "listing_date":     "2012-03-07",
        "data_over_10y":    True,
        "note":             "단기 채권 ETF. 가격이 단조증가하여 ma_pos·momentum 적용 제한.",
        "discussion_note":  (
            "기초자산은 국채·통안채 등 단기채권(채권형)이나, 가격 단조증가·낮은 변동성으로 "
            "HSI 분류상 현금성자산(money_market)으로 배치. "
            "5개 추종 자산 분류(주식형/채권형/금/달러/원자재) 중 채권형에 해당하나 "
            "실질 특성은 현금성에 가까워 asset_class와 underlying_asset이 불일치. "
            "HSI 설계 파트에서 슬롯 배치 시 이 점을 감안 요망."
        ),
    },
}

# 전체 유니버스 공통 데이터 시작일
#   → 가장 늦게 상장된 153130 기준 (2012-03-07) 으로 통일
DATA_START_DATE  = "2012-03-07"
BENCHMARK_TICKER = "069500"


# ──────────────────────────────────────────────────────────────
# 3. 자산군 분류표
#    팀원(HSI 설계 파트)이 상태별 비중 조절 규칙을 연결할 기준 테이블
# ──────────────────────────────────────────────────────────────

# 자산군 메타 정의 (위험등급 숫자가 높을수록 위험)
ASSET_CLASS_META = {
    "equity":       {"kr": "국내주식",       "risk_level": 3, "role": "위험자산"},
    "bond":         {"kr": "국내채권",       "risk_level": 2, "role": "안전자산"},
    "money_market": {"kr": "단기채권/현금성", "risk_level": 1, "role": "현금성자산"},
}

RISK_GROUP_META = {
    "high":     {"kr": "고위험", "order": 4},
    "mid":      {"kr": "중위험", "order": 3},
    "low":      {"kr": "저위험", "order": 2},
    "very_low": {"kr": "초저위험", "order": 1},
}

# ── [기능 2] 추종 자산 분류 메타데이터 ───────────────────────
#    5개 카테고리: 주식형 / 채권형 / 금 / 달러 / 원자재
#    asset_class(HSI 설계 슬롯)와 별개로 기초자산 추종 대상을 명시
UNDERLYING_ASSET_META = {
    "주식형":  {"en": "equity",    "description": "국내외 주식 지수 추종"},
    "채권형":  {"en": "bond",      "description": "국내외 채권(국채·회사채 등) 추종"},
    "금":      {"en": "gold",      "description": "금 현물 또는 선물 추종"},
    "달러":    {"en": "usd",       "description": "미 달러화(USD) 가치 추종"},
    "원자재":  {"en": "commodity", "description": "원자재(에너지·농산물·금속 등) 지수 추종"},
}

# ── [기능 1] 유동성 판단 기준 ─────────────────────────────────
#    거래량/거래대금 기준을 변경하려면 이 딕셔너리만 수정
LIQUIDITY_CRITERIA = {
    "min_daily_volume":   10_000,        # 일평균 거래량 기준 (주)
    "min_daily_turnover": 100_000_000,   # 일평균 거래대금 기준 (원, 1억)
    "lookback_days":      60,            # 기준 산출 기간 (최근 N 거래일)
}

# HSI 5개 지표 적용 현황 (ETF별)
HSI_COVERAGE_DETAIL = {
    "069500": {
        "return": True, "ma_pos": True, "momentum": True,
        "vol":    True, "rs":     True,
    },
    "114260": {
        "return": True, "ma_pos": True, "momentum": True,
        "vol":    True, "rs":     True,
    },
    "153130": {
        "return":   True,
        "ma_pos":   False,   # 가격 단조증가 → 신뢰도 낮음
        "momentum": False,   # 변화폭 미미
        "vol":      True,
        "rs":       True,
    },
}


def make_asset_class_table(universe=None, coverage=None):
    """
    자산군 분류표 DataFrame 생성.

    반환 컬럼:
      ticker | name | asset_class | asset_class_kr | underlying_asset
      risk_group | risk_group_kr | risk_level | role
      listing_date | data_start | coverage_count | hsi_na_signals
      note | discussion_note

    Parameters
    ----------
    universe : ETF_UNIVERSE 딕셔너리. None이면 전역 ETF_UNIVERSE 사용.
    coverage : HSI_COVERAGE_DETAIL 딕셔너리. None이면 전역 값 사용.

    Returns
    -------
    pd.DataFrame — 자산군 분류표 (자산군 위험등급 내림차순 정렬)
    """
    if universe is None:
        universe = ETF_UNIVERSE
    if coverage is None:
        coverage = HSI_COVERAGE_DETAIL

    rows = []
    for ticker, meta in universe.items():
        ac      = meta["asset_class"]
        rg      = meta["risk_group"]
        ua      = meta.get("underlying_asset", "")
        ac_meta = ASSET_CLASS_META.get(ac, {"kr": ac, "risk_level": 0, "role": "-"})
        rg_meta = RISK_GROUP_META.get(rg, {"kr": rg, "order": 0})

        cov = coverage.get(ticker, {})
        cov_count  = sum(1 for v in cov.values() if v)
        na_signals = [k for k, v in cov.items() if not v]

        rows.append({
            "ticker":           ticker,
            "name":             meta["name"],
            "asset_class":      ac,
            "asset_class_kr":   ac_meta["kr"],
            "underlying_asset": ua,               # [기능 2] 추종 자산 구분
            "risk_group":       rg,
            "risk_group_kr":    rg_meta["kr"],
            "risk_level":       ac_meta["risk_level"],
            "role":             ac_meta["role"],
            "listing_date":     meta["listing_date"],
            "data_start":       DATA_START_DATE,
            "coverage_count":   f"{cov_count}/5",
            "hsi_na_signals":   ", ".join(na_signals) if na_signals else "없음",
            "note":             meta.get("note", ""),
            "discussion_note":  meta.get("discussion_note", ""),  # [기능 3]
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("risk_level", ascending=False).reset_index(drop=True)
    return df


def print_asset_class_table(df=None):
    """자산군 분류표를 콘솔에 정렬해 출력 (추종 자산 컬럼 포함)."""
    if df is None:
        df = make_asset_class_table()

    print("=" * 80)
    print("③ 자산군 분류표")
    print("=" * 80)
    print(f"{'ticker':<8} {'name':<20} {'자산군':<14} {'추종자산':<8} "
          f"{'위험등급':<10} {'역할':<14} {'HSI 적용':<8} {'제한 지표'}")
    print("-" * 80)
    for _, row in df.iterrows():
        disc_marker = " ★" if row["discussion_note"] else ""   # 논의 항목 표시
        print(f"{row['ticker']:<8} {row['name']:<20} "
              f"{row['asset_class_kr']:<14} {row['underlying_asset']:<8} "
              f"{row['risk_group_kr']:<10} {row['role']:<14} "
              f"{row['coverage_count']:<8} {row['hsi_na_signals']}{disc_marker}")
    print()
    print("[비고] risk_level: 3=고위험(위험자산), 2=중위험(안전자산), 1=저위험(현금성자산)")
    print("       추종자산: 주식형 | 채권형 | 금 | 달러 | 원자재")
    print("       ★ 표시: 분류 논의 항목 존재 — print_discussion_notes() 참고")
    print()


def print_discussion_notes(df=None, universe=None):
    """
    [기능 3] 자산군·추종 자산 분류가 애매한 ETF의 discussion_note만 별도 출력.

    discussion_note가 비어 있는 ETF는 출력하지 않음.

    Parameters
    ----------
    df      : make_asset_class_table() 반환값. None이면 내부에서 생성.
    universe: ETF_UNIVERSE 딕셔너리. None이면 전역 값 사용.
    """
    if universe is None:
        universe = ETF_UNIVERSE

    # df가 없으면 universe 전체(탈락 후보 포함) 또는 선정 유니버스 기준으로 생성
    if df is None:
        df = make_asset_class_table(universe=universe)

    flagged = df[df["discussion_note"].str.strip() != ""]

    print("=" * 80)
    print("③-별첨  분류 논의 항목 (discussion_note)")
    print("=" * 80)

    if flagged.empty:
        print("  논의가 필요한 분류 항목이 없습니다.\n")
        return

    for _, row in flagged.iterrows():
        print(f"  [{row['ticker']}] {row['name']}")
        print(f"    asset_class      : {row['asset_class']}  →  {row['asset_class_kr']}")
        print(f"    underlying_asset : {row['underlying_asset']}")
        # discussion_note 줄바꿈 처리
        note_lines = row["discussion_note"].replace("  ", "\n    ").split("\n")
        print(f"    discussion_note  :")
        for line in note_lines:
            if line.strip():
                print(f"      {line.strip()}")
        print()


# ──────────────────────────────────────────────────────────────
# 4. ETF 기본정보표
# ──────────────────────────────────────────────────────────────

def make_etf_info_table(universe=None, ref_year=2026):
    """
    ETF 기본정보표 DataFrame 생성.

    반환 컬럼:
      ticker | name | asset_class | risk_group | listing_date | data_years | data_start | note
    """
    if universe is None:
        universe = ETF_UNIVERSE

    rows = []
    for ticker, meta in universe.items():
        listing_year = int(meta["listing_date"].split("-")[0])
        data_years   = ref_year - listing_year
        rows.append({
            "ticker":       ticker,
            "name":         meta["name"],
            "asset_class":  meta["asset_class"],
            "risk_group":   meta["risk_group"],
            "listing_date": meta["listing_date"],
            "data_years":   data_years,
            "data_start":   DATA_START_DATE,
            "note":         meta.get("note", ""),
        })

    return pd.DataFrame(rows)


def print_etf_info_table(df=None):
    """ETF 기본정보표를 콘솔에 출력."""
    if df is None:
        df = make_etf_info_table()

    print("=" * 72)
    print("ETF 기본정보표")
    print("=" * 72)
    for _, row in df.iterrows():
        print(f"  [{row['ticker']}] {row['name']}")
        print(f"    자산군     : {row['asset_class']}  ({row['risk_group']})")
        print(f"    상장일     : {row['listing_date']}  (약 {row['data_years']}년)")
        print(f"    데이터 시작: {row['data_start']}  (유니버스 공통 기준)")
        print(f"    비고       : {row['note']}")
        print()


# ──────────────────────────────────────────────────────────────
# 5. HSI 기본 파라미터
# ──────────────────────────────────────────────────────────────

DEFAULT_PARAMS = {
    "return_window":       20,
    "ma_windows":          [20, 60, 120],
    "momentum_windows":    [21, 63, 126],
    "vol_window":          20,
    "rs_window":           21,
    "standardize":         "zscore",   # "zscore" 또는 "rank"
    "std_window":          252,
    "std_min_periods":     60,
    "clip_z":              2.5,
    "direction_threshold": 0.3,
}


# ──────────────────────────────────────────────────────────────
# 6. 데이터 로더
# ──────────────────────────────────────────────────────────────

def load_price_data(tickers=None, start=DATA_START_DATE, end=None,
                    source="yfinance", csv_dir="./data"):
    """
    종가(adjusted close) DataFrame 반환.
    컬럼 = ticker, 인덱스 = 날짜(DatetimeIndex).

    Parameters
    ----------
    tickers  : 로드할 티커 목록. None이면 ETF_UNIVERSE 전체.
    start    : 시작일 문자열 'YYYY-MM-DD'
    end      : 종료일 문자열. None이면 오늘.
    source   : 'yfinance' 또는 'csv'
    csv_dir  : source='csv'일 때 파일 경로 ({csv_dir}/{ticker}.csv, 컬럼 'Date','Close').
    """
    if tickers is None:
        tickers = list(ETF_UNIVERSE.keys())

    if source == "yfinance":
        try:
            import yfinance as yf
        except ImportError as e:
            raise ImportError("pip install yfinance 후 재시도하세요.") from e

        yf_tickers = [t + ".KS" for t in tickers]
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
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")
            df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
            frames[t] = df["Close"]
        close = pd.DataFrame(frames)

    else:
        raise ValueError(f"지원하지 않는 source: {source}")

    close.index = pd.to_datetime(close.index)
    close = close.sort_index()
    close = close.ffill()
    close = close.dropna(how="all")
    return close


# ── [기능 1] 거래량 데이터 로더 ───────────────────────────────

def load_volume_data(tickers=None, start=DATA_START_DATE, end=None,
                     source="yfinance", csv_dir="./data"):
    """
    거래량(Volume) DataFrame 반환.
    컬럼 = ticker, 인덱스 = 날짜(DatetimeIndex).

    합성 ETF(예: KOFR금리액티브(합성)) 또는 일부 채권형 ETF는
    실거래량이 0이거나 데이터가 없을 수 있음 → check_liquidity()에서 확인.

    Parameters
    ----------
    tickers  : 로드할 티커 목록. None이면 ETF_UNIVERSE 전체.
    start    : 시작일 문자열 'YYYY-MM-DD'
    end      : 종료일 문자열. None이면 오늘.
    source   : 'yfinance' 또는 'csv'
    csv_dir  : source='csv'일 때 파일 경로 ({csv_dir}/{ticker}.csv, 컬럼 'Date','Volume').
    """
    if tickers is None:
        tickers = list(ETF_UNIVERSE.keys())

    if source == "yfinance":
        try:
            import yfinance as yf
        except ImportError as e:
            raise ImportError("pip install yfinance 후 재시도하세요.") from e

        yf_tickers = [t + ".KS" for t in tickers]
        raw = yf.download(yf_tickers, start=start, end=end,
                          auto_adjust=True, progress=False)

        if isinstance(raw.columns, pd.MultiIndex):
            volume = raw["Volume"].copy()
            volume.columns = [c.replace(".KS", "") for c in volume.columns]
        else:
            volume = raw[["Volume"]].copy()
            volume.columns = [tickers[0]]

    elif source == "csv":
        frames = {}
        for t in tickers:
            path = os.path.join(csv_dir, t + ".csv")
            if not os.path.exists(path):
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")
            df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
            if "Volume" not in df.columns:
                raise KeyError(f"{path} 에 'Volume' 컬럼이 없습니다.")
            frames[t] = df["Volume"]
        volume = pd.DataFrame(frames)

    else:
        raise ValueError(f"지원하지 않는 source: {source}")

    volume.index = pd.to_datetime(volume.index)
    volume = volume.sort_index()
    volume = volume.fillna(0)   # 거래량 결측 → 0으로 처리 (거래 없음)
    return volume


# ── [기능 1] 거래량/거래대금 유동성 확인 ──────────────────────

def check_liquidity(prices, volumes=None, universe=None,
                    criteria=None):
    """
    ⑤-2. 거래량/거래대금 기준 유동성 확인.

    거래량 데이터를 수집할 수 있는지 여부와 기준 충족 여부를 함께 반환.
    volumes가 None이면 거래량 로드 없이 메타데이터만으로 '확인불가' 처리.

    반환 컬럼:
      ticker | name | underlying_asset | volume_available
      avg_daily_volume | avg_daily_turnover_krw
      meets_volume_criterion | meets_turnover_criterion
      criterion_applicable | overall_pass | status

    Parameters
    ----------
    prices   : load_price_data() 반환값 (종가 DataFrame)
    volumes  : load_volume_data() 반환값. None이면 '데이터 없음' 처리.
    universe : ETF_UNIVERSE 딕셔너리. None이면 전역 값 사용.
    criteria : LIQUIDITY_CRITERIA 딕셔너리. None이면 전역 값 사용.

    Returns
    -------
    pd.DataFrame — 유동성 확인 결과
    """
    if universe is None:
        universe = ETF_UNIVERSE
    if criteria is None:
        criteria = LIQUIDITY_CRITERIA

    min_vol      = criteria["min_daily_volume"]
    min_turnover = criteria["min_daily_turnover"]
    lookback     = criteria["lookback_days"]

    rows = []
    for ticker in prices.columns:
        meta = universe.get(ticker, {})
        name = meta.get("name", ticker)
        ua   = meta.get("underlying_asset", "")

        if volumes is None or ticker not in volumes.columns:
            # 거래량 데이터 미수집 상태
            rows.append({
                "ticker":                  ticker,
                "name":                    name,
                "underlying_asset":        ua,
                "volume_available":        False,
                "avg_daily_volume":        None,
                "avg_daily_turnover_krw":  None,
                "meets_volume_criterion":  None,
                "meets_turnover_criterion": None,
                "criterion_applicable":    False,
                "overall_pass":            None,
                "status":                  "거래량 데이터 미수집 — load_volume_data() 필요",
            })
            continue

        # 최근 lookback 거래일 기준으로 집계
        vol_series   = volumes[ticker].dropna()
        price_series = prices[ticker].dropna()
        common_idx   = vol_series.index.intersection(price_series.index)

        if len(common_idx) == 0:
            rows.append({
                "ticker":                  ticker,
                "name":                    name,
                "underlying_asset":        ua,
                "volume_available":        False,
                "avg_daily_volume":        None,
                "avg_daily_turnover_krw":  None,
                "meets_volume_criterion":  None,
                "meets_turnover_criterion": None,
                "criterion_applicable":    False,
                "overall_pass":            None,
                "status":                  "가격·거래량 공통 날짜 없음",
            })
            continue

        recent_idx    = common_idx[-lookback:]
        recent_vol    = vol_series.loc[recent_idx]
        recent_price  = price_series.loc[recent_idx]
        daily_turnover = recent_vol * recent_price   # 거래대금 = 거래량 × 종가

        avg_vol      = recent_vol.mean()
        avg_turnover = daily_turnover.mean()

        # 거래량이 전부 0이면 데이터 수집 자체가 불가한 것으로 판단
        vol_available = avg_vol > 0

        meets_vol      = vol_available and (avg_vol >= min_vol)
        meets_turnover = vol_available and (avg_turnover >= min_turnover)
        overall        = meets_vol and meets_turnover

        if not vol_available:
            status = "거래량 데이터 없음 (합성 ETF 또는 장외거래 가능성)"
        elif overall:
            status = "기준 충족"
        else:
            parts = []
            if not meets_vol:
                parts.append(f"거래량 미달({avg_vol:,.0f}주 < {min_vol:,}주)")
            if not meets_turnover:
                parts.append(f"거래대금 미달({avg_turnover/1e8:.1f}억 < {min_turnover/1e8:.0f}억)")
            status = " / ".join(parts)

        rows.append({
            "ticker":                   ticker,
            "name":                     name,
            "underlying_asset":         ua,
            "volume_available":         vol_available,
            "avg_daily_volume":         round(avg_vol),
            "avg_daily_turnover_krw":   round(avg_turnover),
            "meets_volume_criterion":   meets_vol,
            "meets_turnover_criterion": meets_turnover,
            "criterion_applicable":     vol_available,
            "overall_pass":             overall,
            "status":                   status,
        })

    return pd.DataFrame(rows)


def print_liquidity_check(df=None, prices=None, volumes=None, criteria=None):
    """
    ⑤-2. 거래량/거래대금 유동성 확인 결과 출력.

    Parameters
    ----------
    df       : check_liquidity() 반환값. None이면 내부에서 계산.
    prices   : df=None일 때 필요한 종가 DataFrame.
    volumes  : df=None일 때 필요한 거래량 DataFrame.
    criteria : LIQUIDITY_CRITERIA 딕셔너리. None이면 전역 값 사용.
    """
    if criteria is None:
        criteria = LIQUIDITY_CRITERIA
    if df is None:
        if prices is None:
            raise ValueError("df 또는 prices 중 하나를 반드시 넘겨야 합니다.")
        df = check_liquidity(prices, volumes=volumes, criteria=criteria)

    min_vol      = criteria["min_daily_volume"]
    min_turnover = criteria["min_daily_turnover"]
    lookback     = criteria["lookback_days"]

    print("=" * 80)
    print("⑤-2. 거래량/거래대금 유동성 확인")
    print("=" * 80)
    print(f"  기준: 일평균 거래량 ≥ {min_vol:,}주  |  "
          f"일평균 거래대금 ≥ {min_turnover/1e8:.0f}억원  |  "
          f"최근 {lookback} 거래일 기준")
    print()
    print(f"{'ticker':<8} {'name':<20} {'추종자산':<8} "
          f"{'거래량가능':<10} {'일평균거래량':<14} {'일평균거래대금':<16} {'결과'}")
    print("-" * 80)
    for _, row in df.iterrows():
        avol = f"{row['avg_daily_volume']:,}주" if row["avg_daily_volume"] is not None else "N/A"
        atrn = (f"{row['avg_daily_turnover_krw']/1e8:.1f}억"
                if row["avg_daily_turnover_krw"] is not None else "N/A")
        avail = "가능 ✓" if row["volume_available"] else "불가 ✗"
        result = ("통과 ✓" if row["overall_pass"] is True
                  else ("미달 ✗" if row["overall_pass"] is False else "확인필요"))
        print(f"{row['ticker']:<8} {row['name']:<20} {row['underlying_asset']:<8} "
              f"{avail:<10} {avol:<14} {atrn:<16} {result}")
    print()
    print("[상세 사유]")
    for _, row in df.iterrows():
        print(f"  [{row['ticker']}] {row['status']}")
    print()


# ──────────────────────────────────────────────────────────────
# 7. 데이터 검증 산출물
# ──────────────────────────────────────────────────────────────

def check_data_period(prices, universe=None):
    """
    ④ 상장일 및 데이터 기간 확인.

    각 티커별로 실제 데이터 시작일·종료일·거래일 수를 집계하고,
    ETF 메타데이터의 상장일과 비교해 반환.

    Returns
    -------
    pd.DataFrame — ticker | name | listing_date | data_start_actual |
                   data_end | trading_days | data_years_actual | status
    """
    if universe is None:
        universe = ETF_UNIVERSE

    rows = []
    for ticker in prices.columns:
        series       = prices[ticker].dropna()
        meta         = universe.get(ticker, {})
        listing_date = meta.get("listing_date", "N/A")

        actual_start = series.index[0].strftime("%Y-%m-%d")  if len(series) > 0 else "N/A"
        actual_end   = series.index[-1].strftime("%Y-%m-%d") if len(series) > 0 else "N/A"
        trading_days = len(series)
        data_years   = round(trading_days / 252, 1)

        # 데이터 시작일 vs 상장일 비교
        if listing_date != "N/A" and actual_start != "N/A":
            lst  = pd.to_datetime(listing_date)
            actl = pd.to_datetime(actual_start)
            gap  = (actl - lst).days
            if gap <= 30:
                status = "정상"
            elif gap <= 365:
                status = f"시작 {gap}일 지연"
            else:
                status = f"시작 {gap//365}년 이상 지연"
        else:
            status = "확인불가"

        rows.append({
            "ticker":              ticker,
            "name":                meta.get("name", ticker),
            "listing_date":        listing_date,
            "data_start_actual":   actual_start,
            "data_end":            actual_end,
            "trading_days":        trading_days,
            "data_years_actual":   data_years,
            "status":              status,
        })

    return pd.DataFrame(rows)


def print_data_period(df=None, prices=None):
    """데이터 기간 확인 결과 출력."""
    if df is None:
        if prices is None:
            raise ValueError("df 또는 prices 중 하나를 반드시 넘겨야 합니다.")
        df = check_data_period(prices)

    print("=" * 72)
    print("④ 상장일 및 데이터 기간 확인")
    print("=" * 72)
    print(f"{'ticker':<8} {'name':<20} {'상장일':<12} {'실제시작':<12} "
          f"{'종료일':<12} {'거래일수':<8} {'연수':<6} {'상태'}")
    print("-" * 72)
    for _, row in df.iterrows():
        print(f"{row['ticker']:<8} {row['name']:<20} {row['listing_date']:<12} "
              f"{row['data_start_actual']:<12} {row['data_end']:<12} "
              f"{row['trading_days']:<8} {str(row['data_years_actual'])+'년':<6} {row['status']}")
    print()


def check_missing_values(prices, universe=None):
    """
    ⑤ 결측치 확인.

    전체 기간 및 연도별 결측치 수를 집계.

    Returns
    -------
    summary_df  : ticker | name | total_rows | missing_count | missing_pct | ffill_applied
    yearly_df   : 연도별 결측치 수 피벗 테이블 (ticker × 연도)
    """
    if universe is None:
        universe = ETF_UNIVERSE

    # 전체 결측치 집계
    summary_rows = []
    for ticker in prices.columns:
        # ffill 적용 전 원본 기준으로 집계하기 위해 로직상 ffill 이후 데이터를 사용
        # (load_price_data에서 이미 ffill 적용됨)
        total    = len(prices[ticker])
        missing  = prices[ticker].isna().sum()
        pct      = round(missing / total * 100, 2) if total > 0 else 0
        meta     = universe.get(ticker, {})
        summary_rows.append({
            "ticker":        ticker,
            "name":          meta.get("name", ticker),
            "total_rows":    total,
            "missing_count": int(missing),
            "missing_pct":   f"{pct}%",
            "ffill_applied": "적용됨 (load_price_data 내부)",
        })
    summary_df = pd.DataFrame(summary_rows)

    # 연도별 결측치 피벗 테이블
    yearly = prices.copy()
    yearly["year"] = yearly.index.year
    yearly_missing = (
        yearly
        .groupby("year")
        .apply(lambda g: g.drop(columns="year").isna().sum())
        .T
    )
    yearly_missing.index.name = "ticker"

    return summary_df, yearly_missing


def print_missing_values(summary_df=None, yearly_df=None, prices=None):
    """결측치 확인 결과 출력."""
    if summary_df is None:
        if prices is None:
            raise ValueError("summary_df 또는 prices 중 하나를 반드시 넘겨야 합니다.")
        summary_df, yearly_df = check_missing_values(prices)

    print("=" * 72)
    print("⑤ 결측치 확인")
    print("=" * 72)

    print("[전체 기간 결측치 현황]")
    print(f"{'ticker':<8} {'name':<20} {'전체행':<8} {'결측수':<8} "
          f"{'결측률':<8} {'처리방법'}")
    print("-" * 72)
    for _, row in summary_df.iterrows():
        print(f"{row['ticker']:<8} {row['name']:<20} {row['total_rows']:<8} "
              f"{row['missing_count']:<8} {row['missing_pct']:<8} {row['ffill_applied']}")
    print()

    if yearly_df is not None and not yearly_df.empty:
        print("[연도별 결측치 수]")
        print(yearly_df.to_string())
        print()


# ──────────────────────────────────────────────────────────────
# 8. 월별 산출물
# ──────────────────────────────────────────────────────────────

def make_monthly_price_table(prices):
    """
    ⑥ 월말 가격표 생성.

    월말 영업일 기준 종가를 피벗 테이블로 반환.
    인덱스: 연월(YYYY-MM), 컬럼: ticker

    Returns
    -------
    pd.DataFrame — 월말 종가 테이블
    """
    monthly = prices.resample("ME").last()
    monthly.index = monthly.index.to_period("M").astype(str)
    monthly.index.name = "year_month"
    return monthly


def make_monthly_return_table(prices):
    """
    ⑦ 월간 수익률표 생성.

    월말 종가 기준 월간 수익률(%)을 피벗 테이블로 반환.
    인덱스: 연월(YYYY-MM), 컬럼: ticker

    Returns
    -------
    pd.DataFrame — 월간 수익률 테이블 (단위: %)
    """
    monthly_ret = make_monthly_price_table(prices).pct_change() * 100
    return monthly_ret.round(4).dropna(how="all")


def print_monthly_tables(prices, tail_n=12):
    """월말 가격표 및 월간 수익률표 최근 N개월 출력."""
    price_table  = make_monthly_price_table(prices)
    return_table = make_monthly_return_table(prices)

    print("=" * 72)
    print("⑥ 월말 가격표 (최근 " + str(tail_n) + "개월)")
    print("=" * 72)
    print(price_table.tail(tail_n).to_string())
    print()

    print("=" * 72)
    print("⑦ 월간 수익률표 (단위: %, 최근 " + str(tail_n) + "개월)")
    print("=" * 72)
    print(return_table.tail(tail_n).to_string())
    print()


# ──────────────────────────────────────────────────────────────
# 9. HSI 개별 지표 계산 함수
#    부호 규칙: 음수=양호/기회, 양수=위험
# ──────────────────────────────────────────────────────────────

def _sign_flip(df):
    """양호 신호(양수)를 음수로 반전해 '위험 방향=양수' 기준으로 통일."""
    return -df


def calc_return(prices, window=20):
    """최근 수익률 = (P_t / P_{t-window}) - 1. 높을수록 양호 → 부호 반전."""
    return _sign_flip(prices.pct_change(window))


def calc_ma_position(prices, windows=None):
    """
    이동평균 대비 위치 = (P_t / MA_t) - 1.
    여러 이동평균의 평균. 가격 > MA → 양호 → 부호 반전.
    """
    if windows is None:
        windows = [20, 60, 120]
    signals = [(prices / prices.rolling(w, min_periods=w).mean()) - 1 for w in windows]
    return _sign_flip(pd.concat(signals).groupby(level=0).mean())


def calc_momentum(prices, windows=None):
    """
    모멘텀 = n일 수익률 (1M≈21, 3M≈63, 6M≈126 거래일).
    여러 기간 평균. 양수=양호 → 부호 반전.
    """
    if windows is None:
        windows = [21, 63, 126]
    signals = [prices.pct_change(w) for w in windows]
    return _sign_flip(pd.concat(signals).groupby(level=0).mean())


def calc_volatility(prices, window=20, annualize=True):
    """
    변동성 = 일간 수익률의 rolling 표준편차.
    높을수록 위험 → 양수=위험이므로 부호 반전 없이 반환.
    """
    vol = prices.pct_change().rolling(window, min_periods=window).std()
    return vol * np.sqrt(252) if annualize else vol


def calc_relative_strength(prices, benchmark=BENCHMARK_TICKER, window=21):
    """
    상대강도 = 종목 수익률(window) - 기준 수익률(window).
    기준보다 강하면 양호 → 부호 반전.
    """
    if benchmark not in prices.columns:
        raise ValueError(
            f"benchmark 티커 '{benchmark}'가 prices 컬럼에 없습니다. "
            f"사용 가능 컬럼: {list(prices.columns)}"
        )
    ret    = prices.pct_change(window)
    bm_ret = ret[[benchmark]]
    return _sign_flip(ret.subtract(bm_ret.values, axis=0))


# ──────────────────────────────────────────────────────────────
# 10. 표준화
# ──────────────────────────────────────────────────────────────

def standardize_zscore(signal, window=252, min_periods=60):
    """Rolling z-score 표준화 (미래 데이터 누출 방지)."""
    roll_mean = signal.rolling(window, min_periods=min_periods).mean()
    roll_std  = signal.rolling(window, min_periods=min_periods).std()
    return (signal - roll_mean) / roll_std.replace(0, np.nan)


def standardize_rank(signal, window=252, min_periods=60):
    """
    Rolling 분위수 표준화 (0~1 → -1~+1 선형 변환).
    0.5=중립=0.
    """
    def _rank_pct(x):
        arr = pd.Series(x)
        if arr.isna().all():
            return np.nan
        return float(arr.rank(pct=True).iloc[-1])

    ranked = signal.rolling(window, min_periods=min_periods).apply(_rank_pct, raw=False)
    return (ranked - 0.5) * 2


def clip_to_score(standardized, clip_z=2.5, scale=10.0):
    """표준화 지표를 -10~+10 범위로 변환."""
    clipped = standardized.clip(-clip_z, clip_z)
    return (clipped / clip_z) * scale


# ──────────────────────────────────────────────────────────────
# 11. HSI 계산 (기본 파라미터 기준)
# ──────────────────────────────────────────────────────────────

def _compute_signed_signals(prices, params, benchmark):
    """
    HSI 5개 지표를 '위험 방향=양수' 부호로 통일해 계산 (부호 반전 포함).
    compute_hsi / make_hsi_signal_table 공통 사용 — 중복 제거용 헬퍼.
    """
    p = params
    return {
        "return":   calc_return(prices,         window=p["return_window"]),
        "ma_pos":   calc_ma_position(prices,    windows=p["ma_windows"]),
        "momentum": calc_momentum(prices,       windows=p["momentum_windows"]),
        "vol":      calc_volatility(prices,     window=p["vol_window"]),
        "rs":       calc_relative_strength(prices, benchmark=benchmark,
                                           window=p["rs_window"]),
    }


def _score_signals(signed_signals, params):
    """표준화 + 점수 변환(-10~+10)을 일괄 적용 — 중복 제거용 헬퍼."""
    p = params
    scored = {}
    for name, sig in signed_signals.items():
        if p["standardize"] == "zscore":
            std_sig = standardize_zscore(sig, p["std_window"], p["std_min_periods"])
        else:
            std_sig = standardize_rank(sig, p["std_window"], p["std_min_periods"])
        scored[name] = clip_to_score(std_sig, clip_z=p["clip_z"])
    return scored


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
      {ticker}_direction  : -1~+1  (음수=양호/기회, 양수=위험)
      {ticker}_intensity  :  0~+1  (신호 강도)
      {ticker}_signal     : 'buy' | 'watch' | 'caution'
    """
    if params is None:
        params = DEFAULT_PARAMS

    p = params
    signed_signals = _compute_signed_signals(prices, p, benchmark)
    scored_signals = _score_signals(signed_signals, p)

    M = len(scored_signals) * 10.0
    results = {}

    for ticker in prices.columns:
        ticker_scores = pd.DataFrame(
            {k: v[ticker] for k, v in scored_signals.items() if ticker in v.columns}
        )

        v_plus  = ticker_scores.clip(lower=0).sum(axis=1)
        v_minus = ticker_scores.clip(upper=0).abs().sum(axis=1)

        direction = (v_plus - v_minus) / M
        intensity = (v_plus + v_minus) / M

        thr = p["direction_threshold"]
        signal = pd.Series("watch", index=direction.index, dtype=str)
        signal[direction < -thr] = "buy"
        signal[direction >  thr] = "caution"

        results[ticker + "_direction"] = direction
        results[ticker + "_intensity"] = intensity
        results[ticker + "_signal"]    = signal

    return pd.DataFrame(results)


# ──────────────────────────────────────────────────────────────
# 12. HSI 기본 입력 신호표
# ──────────────────────────────────────────────────────────────

def make_hsi_signal_table(prices, params=None, benchmark=BENCHMARK_TICKER):
    """
    ⑧ HSI 기본 입력 신호표 생성.

    각 지표의 원시 점수(-10~+10)를 티커별로 집계한 테이블.
    (compute_hsi의 중간 산출물을 그대로 노출)

    Returns
    -------
    dict of pd.DataFrame:
      "raw_scores"    : 각 지표 점수 (컬럼: {ticker}_{지표명})
      "hsi_direction" : HSI direction 컬럼만 추출
      "hsi_signal"    : HSI signal 컬럼만 추출 (buy/watch/caution)
      "snapshot"      : 가장 최근 날짜 기준 요약 테이블
    """
    if params is None:
        params = DEFAULT_PARAMS

    p = params

    # 개별 지표 원시 점수 계산 (compute_hsi와 동일 헬퍼 사용 — 중복 제거)
    signed_signals = _compute_signed_signals(prices, p, benchmark)
    scored_signals = _score_signals(signed_signals, p)

    raw_score_frames = {}
    for sig_name, scored in scored_signals.items():
        for ticker in prices.columns:
            if ticker in scored.columns:
                raw_score_frames[f"{ticker}_{sig_name}"] = scored[ticker]

    raw_scores_df = pd.DataFrame(raw_score_frames)

    # HSI 최종 결과
    hsi_df = compute_hsi(prices, params=params, benchmark=benchmark)

    direction_cols = [c for c in hsi_df.columns if c.endswith("_direction")]
    signal_cols    = [c for c in hsi_df.columns if c.endswith("_signal")]

    # 최근 날짜 스냅샷
    last_date  = hsi_df.dropna(how="all").index[-1]
    snap_rows  = []
    for ticker in prices.columns:
        d_col = ticker + "_direction"
        i_col = ticker + "_intensity"
        s_col = ticker + "_signal"
        if d_col not in hsi_df.columns:
            continue
        score_cols = [c for c in raw_scores_df.columns if c.startswith(ticker + "_")]
        scores = {}
        for c in score_cols:
            sig_name = c.replace(ticker + "_", "")
            scores[sig_name] = round(raw_scores_df[c].loc[last_date], 3)

        snap_rows.append({
            "ticker":    ticker,
            "name":      ETF_UNIVERSE.get(ticker, {}).get("name", ticker),
            "date":      last_date.strftime("%Y-%m-%d"),
            "direction": round(hsi_df[d_col].loc[last_date], 4),
            "intensity": round(hsi_df[i_col].loc[last_date], 4),
            "signal":    hsi_df[s_col].loc[last_date],
            **{f"score_{k}": v for k, v in scores.items()},
        })

    snapshot_df = pd.DataFrame(snap_rows)

    return {
        "raw_scores":    raw_scores_df,
        "hsi_direction": hsi_df[direction_cols],
        "hsi_signal":    hsi_df[signal_cols],
        "snapshot":      snapshot_df,
    }


def print_hsi_signal_table(signal_tables):
    """⑧ HSI 기본 입력 신호표 출력."""
    snap = signal_tables["snapshot"]
    print("=" * 72)
    print("⑧ HSI 기본 입력 신호표 (기본 파라미터 기준, 최근 날짜 스냅샷)")
    print("=" * 72)

    if not snap.empty:
        date_str = snap["date"].iloc[0]
        print(f"기준일: {date_str}")
        print()
        score_cols = [c for c in snap.columns if c.startswith("score_")]
        for _, row in snap.iterrows():
            print(f"  [{row['ticker']}] {row['name']}")
            print(f"    direction : {row['direction']:+.4f}  |  "
                  f"intensity : {row['intensity']:.4f}  |  signal : {row['signal'].upper()}")
            scores_str = "  ".join(
                [f"{c.replace('score_', '')}={row[c]:+.2f}" for c in score_cols]
            )
            print(f"    지표 점수 : {scores_str}")
            print()


# ──────────────────────────────────────────────────────────────
# 12-B. [추가 기능 1·2] HSI 기본 입력 신호표 (원신호 / hsi_signal_inputs.csv)
#    부호 반전 전 '실제값'을 ETF·날짜별 tidy 표로 산출.
#    기본 6개 컬럼 우선 계산, include_extended=True 시 확장 5개 컬럼 추가.
# ──────────────────────────────────────────────────────────────

# 기본/확장 컬럼 정의 (docx 출력 #6 'HSI 입력 신호표')
SIGNAL_INPUT_BASE_COLS = [
    "ret_1m", "ret_3m", "ma_gap", "momentum", "volatility", "relative_strength",
]
SIGNAL_INPUT_EXT_COLS = [
    "ret_6m", "ret_12m", "drawdown", "shock_count", "defensive_rs",
]


def _find_cash_ticker(universe):
    """방어자산 상대강도(defensive_rs) 기준이 될 현금성(money_market) 티커 탐색."""
    for ticker, meta in universe.items():
        if meta.get("asset_class") == "money_market":
            return ticker
    return None


def make_hsi_signal_inputs(prices, benchmark=BENCHMARK_TICKER, params=None,
                           ext=None, include_extended=False, universe=None,
                           log=None):
    """
    ⑥ HSI 기본 입력 신호표 생성 (hsi_signal_inputs.csv).

    각 ETF·날짜별 원신호(부호 반전 전 실제값)를 long(tidy) DataFrame으로 반환.

    기본 컬럼 (우선 계산):
      ret_1m, ret_3m, ma_gap, momentum, volatility, relative_strength
    확장 컬럼 (include_extended=True):
      ret_6m, ret_12m, drawdown, shock_count, defensive_rs

    Parameters
    ----------
    prices           : 종가 DataFrame (컬럼=ticker)
    benchmark        : relative_strength 기준 티커 (기본 069500 KODEX 200)
    params           : 윈도우 설정. None이면 SIGNAL_INPUT_PARAMS 사용.
    ext              : 확장 윈도우 설정. None이면 EXTENDED_PARAMS 사용.
    include_extended : True면 확장 5개 컬럼 추가.
    universe         : ETF_UNIVERSE. defensive_rs 기준 현금성 티커 탐색에 사용.
    log              : PreprocessingLog 인스턴스. 주어지면 처리 단계 기록.

    Returns
    -------
    pd.DataFrame — 컬럼: Date, ticker, [기본 6개] (+ 확장 5개)
    """
    if params is None:
        params = SIGNAL_INPUT_PARAMS
    if ext is None:
        ext = EXTENDED_PARAMS
    if universe is None:
        universe = ETF_UNIVERSE

    if benchmark not in prices.columns:
        raise ValueError(
            f"benchmark 티커 '{benchmark}'가 prices 컬럼에 없습니다. "
            f"사용 가능 컬럼: {list(prices.columns)}"
        )

    daily_ret = prices.pct_change()

    # ── 기본 6개 원신호 (wide: 컬럼=ticker) ───────────────────
    ret_1m = prices.pct_change(params["ret_1m_window"])
    ret_3m = prices.pct_change(params["ret_3m_window"])

    ma_w   = params["ma_gap_window"]
    ma_gap = prices / prices.rolling(ma_w, min_periods=ma_w).mean() - 1

    mom_windows = params["momentum_windows"]
    momentum = (pd.concat([prices.pct_change(w) for w in mom_windows])
                .groupby(level=0).mean())

    volatility = calc_volatility(prices, window=params["vol_window"])

    rs_w  = params["rs_window"]
    r_w   = prices.pct_change(rs_w)
    relative_strength = r_w.subtract(r_w[benchmark], axis=0)

    signal_map = {
        "ret_1m":            ret_1m,
        "ret_3m":            ret_3m,
        "ma_gap":            ma_gap,
        "momentum":          momentum,
        "volatility":        volatility,
        "relative_strength": relative_strength,
    }
    cols = list(SIGNAL_INPUT_BASE_COLS)

    if log is not None:
        log.step(f"기본 입력 신호 6종 계산 완료 "
                 f"(ret_1m={params['ret_1m_window']}d, ret_3m={params['ret_3m_window']}d, "
                 f"ma_gap=MA{ma_w}, vol={params['vol_window']}d, rs={rs_w}d, "
                 f"benchmark={benchmark})")

    # ── 확장 5개 컬럼 ─────────────────────────────────────────
    if include_extended:
        signal_map["ret_6m"]  = prices.pct_change(ext["ret_6m"])
        signal_map["ret_12m"] = prices.pct_change(ext["ret_12m"])

        dd_w     = ext["drawdown_window"]
        roll_max = prices.rolling(dd_w, min_periods=1).max()
        signal_map["drawdown"] = prices / roll_max - 1          # ≤ 0 (낙폭)

        thr = ext["shock_threshold"]
        shock_flag = (daily_ret < -thr).astype(float)
        signal_map["shock_count"] = shock_flag.rolling(dd_w, min_periods=1).sum()

        cash_ticker = _find_cash_ticker(universe)
        if cash_ticker is not None and cash_ticker in prices.columns:
            rs_s   = ext["rs_short_window"]
            r_s    = prices.pct_change(rs_s)
            signal_map["defensive_rs"] = r_s.subtract(r_s[cash_ticker], axis=0)
        else:
            signal_map["defensive_rs"] = pd.DataFrame(
                np.nan, index=prices.index, columns=prices.columns)

        cols += list(SIGNAL_INPUT_EXT_COLS)

        if log is not None:
            cash_label = cash_ticker if cash_ticker else "없음(NaN 처리)"
            log.step(f"확장 입력 신호 5종 계산 완료 "
                     f"(ret_6m={ext['ret_6m']}d, ret_12m={ext['ret_12m']}d, "
                     f"drawdown=MAX{dd_w}d, shock=|<-{thr:.0%}|×{dd_w}d, "
                     f"defensive_rs vs {cash_label})")

    # ── wide → long(tidy) 변환 ────────────────────────────────
    frames = []
    for ticker in prices.columns:
        tdf = pd.DataFrame({c: signal_map[c][ticker] for c in cols})
        tdf.insert(0, "ticker", ticker)
        tdf.index.name = "Date"
        frames.append(tdf.reset_index())

    out = pd.concat(frames, ignore_index=True)
    out = out.dropna(subset=cols, how="all").reset_index(drop=True)
    out[cols] = out[cols].round(6)
    return out


def latest_signal_inputs(signal_inputs):
    """HSI 입력 신호표에서 ETF별 가장 최근 날짜 1행씩 추출."""
    return (signal_inputs.sort_values("Date")
            .groupby("ticker", as_index=False).tail(1)
            .reset_index(drop=True))


def print_hsi_signal_inputs(signal_inputs, universe=None):
    """⑥ HSI 기본 입력 신호표를 ETF별 최근 스냅샷 표로 출력."""
    if universe is None:
        universe = ETF_UNIVERSE

    snap = latest_signal_inputs(signal_inputs)
    value_cols = [c for c in signal_inputs.columns if c not in ("Date", "ticker")]
    extended = any(c in value_cols for c in SIGNAL_INPUT_EXT_COLS)

    print("=" * 100)
    title = "⑥ HSI 기본 입력 신호표 (원신호 — 부호 반전 전 실제값"
    title += ", 확장 컬럼 포함)" if extended else ")"
    print(title)
    print("=" * 100)
    print(f"  전체 {len(signal_inputs):,}행  |  ETF {snap['ticker'].nunique()}종목  |  "
          f"컬럼 {len(value_cols)}개 ({'기본6+확장5' if extended else '기본6'})")
    print()

    headers = ["ticker", "name", "Date"] + value_cols
    aligns  = ["left", "left", "left"] + ["right"] * len(value_cols)
    rows = []
    for _, r in snap.iterrows():
        name = universe.get(r["ticker"], {}).get("name", r["ticker"])
        date_str = pd.to_datetime(r["Date"]).strftime("%Y-%m-%d")
        cells = [r["ticker"], name, date_str]
        for c in value_cols:
            val = r[c]
            if pd.isna(val):
                cells.append("N/A")
            elif c == "shock_count":
                cells.append(f"{val:.0f}")
            else:
                cells.append(f"{val:+.4f}")
        rows.append(cells)
    _print_grid(headers, rows, aligns)
    print()
    print("  ※ ret_*/momentum/relative_strength/defensive_rs: 비율(원수익률 단위), "
          "volatility: 연율화 표준편차")
    print("     ma_gap: 이동평균 이격도, drawdown: 낙폭(≤0), shock_count: 급락일 수")
    print()


# ──────────────────────────────────────────────────────────────
# 12-C. [추가 기능 3] 전처리 로그 (preprocessing_log.md)
#    데이터 처리 과정과 제외 사유를 누적 기록 → 마크다운으로 저장.
# ──────────────────────────────────────────────────────────────

class PreprocessingLog:
    """
    데이터 처리 단계와 제외 사유를 누적 기록하는 경량 로거.

    사용 예
    -------
    log = PreprocessingLog()
    log.step("가격 데이터 로드 완료")
    log.exclude("148020", "KOSEF 국고채10년", "커버리지 점수 열위로 미선정")
    log.save("preprocessing_log.md")
    """

    def __init__(self, title="HSI 데이터 전처리 로그"):
        self.title      = title
        self.created_at = pd.Timestamp.now()
        self.steps      = []   # (순번, 시각, 메시지)
        self.exclusions = []   # dict(ticker, name, reason)
        self.notes      = []   # 자유 메모

    def step(self, message, echo=True):
        """처리 단계 1건 기록 (echo=True면 콘솔에도 출력)."""
        ts = pd.Timestamp.now()
        self.steps.append((len(self.steps) + 1, ts, message))
        if echo:
            print(f"  · [LOG] {message}")
        return self

    def exclude(self, ticker, name, reason, echo=True):
        """ETF 제외(또는 미선정) 사유 1건 기록."""
        self.exclusions.append({"ticker": ticker, "name": name, "reason": reason})
        if echo:
            print(f"  · [LOG-제외] [{ticker}] {name} — {reason}")
        return self

    def note(self, text):
        """보조 메모 기록."""
        self.notes.append(text)
        return self

    def to_markdown(self):
        """누적 기록을 마크다운 문자열로 변환."""
        lines = [f"# {self.title}", ""]
        lines.append(f"- 생성 시각: {self.created_at:%Y-%m-%d %H:%M:%S}")
        lines.append(f"- 처리 단계: {len(self.steps)}건 / 제외 항목: {len(self.exclusions)}건")
        lines.append("")

        lines.append("## 1. 데이터 처리 과정")
        lines.append("")
        if self.steps:
            lines.append("| 순번 | 시각 | 처리 내용 |")
            lines.append("|---:|:---|:---|")
            for no, ts, msg in self.steps:
                lines.append(f"| {no} | {ts:%H:%M:%S} | {msg} |")
        else:
            lines.append("_기록된 처리 단계가 없습니다._")
        lines.append("")

        lines.append("## 2. 제외 / 미선정 사유")
        lines.append("")
        if self.exclusions:
            lines.append("| ticker | name | 제외·미선정 사유 |")
            lines.append("|:---|:---|:---|")
            for ex in self.exclusions:
                lines.append(f"| {ex['ticker']} | {ex['name']} | {ex['reason']} |")
        else:
            lines.append("_제외된 항목이 없습니다._")
        lines.append("")

        if self.notes:
            lines.append("## 3. 비고")
            lines.append("")
            for n in self.notes:
                lines.append(f"- {n}")
            lines.append("")

        return "\n".join(lines)

    def save(self, path="preprocessing_log.md"):
        """마크다운 로그를 파일로 저장."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        return path


def log_etf_exclusions(log, candidates, selected, criteria=None):
    """
    후보군 대비 미선정 ETF의 사유를 PreprocessingLog에 일괄 기록.

    데이터 연수 미충족이면 그 사유를, 그 외는 자산군 내 커버리지 열위로 기록.
    """
    if criteria is None:
        criteria = SELECTION_CRITERIA

    selected_tickers = {e["ticker"] for e in selected}
    min_years = criteria["min_data_years"]
    ref_year  = criteria["reference_year"]

    for etf in candidates:
        if etf["ticker"] in selected_tickers:
            continue
        listing_year = int(etf["listing_date"].split("-")[0])
        data_years   = ref_year - listing_year
        if data_years < min_years:
            reason = f"데이터 연수 부족({data_years}년 < 기준 {min_years}년)"
        else:
            reason = "자산군 내 HSI 커버리지 점수 열위로 미선정"
        log.exclude(etf["ticker"], etf["name"], reason, echo=False)
    return log


def write_preprocessing_log(log, path="preprocessing_log.md"):
    """PreprocessingLog를 마크다운 파일로 저장하는 단축 함수."""
    return log.save(path)


# ──────────────────────────────────────────────────────────────
# 13. 표 출력 공통 유틸 (한글 폭 보정 정렬)
# ──────────────────────────────────────────────────────────────

def _wlen(text):
    """동아시아 전각 문자를 2칸으로 계산한 표시 폭."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1
               for ch in str(text))


def _pad(text, width, align="left"):
    """표시 폭 기준으로 문자열을 width 칸에 맞춰 패딩."""
    text = str(text)
    gap  = max(0, width - _wlen(text))
    if align == "right":
        return " " * gap + text
    if align == "center":
        left = gap // 2
        return " " * left + text + " " * (gap - left)
    return text + " " * gap


def _print_grid(headers, rows, aligns=None, gap=2):
    """
    헤더 + 2차원 리스트를 한글 폭 보정해 격자 표로 출력.

    headers : 컬럼 제목 리스트
    rows    : 행 리스트 (각 행은 셀 문자열 리스트)
    aligns  : 컬럼별 정렬 ("left"|"right"|"center"). None이면 전부 left.
    """
    ncol   = len(headers)
    aligns = aligns or ["left"] * ncol
    widths = [_wlen(h) for h in headers]
    for row in rows:
        for i in range(ncol):
            widths[i] = max(widths[i], _wlen(row[i]))

    sep = " " * gap
    line = sep.join(_pad(h, widths[i], "center") for i, h in enumerate(headers))
    print(line)
    print("-" * _wlen(line))
    for row in rows:
        print(sep.join(_pad(row[i], widths[i], aligns[i]) for i in range(ncol)))


# ──────────────────────────────────────────────────────────────
# 14. [추가 기능 1] HSI 입력 구조표 (14개 항목)
#     docx 'HSI 입력 구조표'를 코드 구조로 옮기고,
#     14개 항목을 실제 객체로 '받아와서 입력하는' 수집기까지 제공.
# ──────────────────────────────────────────────────────────────

# ── 입력 #11) 신호 방향 정의 — _sign_flip 부호 규칙과 1:1 대응 ──
#    HSI 통일 규칙: 양수=위험 악화, 음수=위험 완화
SIGNAL_DIRECTION_MAP = {
    "return":   {"raw_direction": "높을수록 양호", "hsi_sign": "반전(-)",
                 "interpretation": "수익률↑ → 위험 완화"},
    "ma_pos":   {"raw_direction": "MA 위=양호",   "hsi_sign": "반전(-)",
                 "interpretation": "이동평균 상회 → 위험 완화"},
    "momentum": {"raw_direction": "높을수록 양호", "hsi_sign": "반전(-)",
                 "interpretation": "모멘텀↑ → 위험 완화"},
    "vol":      {"raw_direction": "높을수록 위험", "hsi_sign": "유지(+)",
                 "interpretation": "변동성↑ → 위험 악화"},
    "rs":       {"raw_direction": "기준 대비 강함=양호", "hsi_sign": "반전(-)",
                 "interpretation": "상대강도↑ → 위험 완화"},
}

# ── 입력 #9) 데이터 품질 점검 기준 — 결측/기간/유동성 통합 ──
QUALITY_RULES = {
    "max_missing_ratio":   0.05,   # 결측치 허용 비율 (5%)
    "min_observation_days": 252,   # 최소 관측기간 (약 1년 거래일)
    "min_daily_volume":    LIQUIDITY_CRITERIA["min_daily_volume"],
    "min_daily_turnover":  LIQUIDITY_CRITERIA["min_daily_turnover"],
}

# ── 입력 #12) 점수화 방식 설정 — DEFAULT_PARAMS에서 파생 ──
SCALING_CONFIG = {
    "method":      DEFAULT_PARAMS["standardize"],   # "zscore" | "rank"
    "window":      DEFAULT_PARAMS["std_window"],
    "min_periods": DEFAULT_PARAMS["std_min_periods"],
    "clip_z":      DEFAULT_PARAMS["clip_z"],
    "score_range": (-10, 10),
    "note":        "rank/z-score는 같은 원신호를 다른 눈금으로 읽는 비교 실험",
}

# ── 입력 #7-보강) HSI 기본 입력 신호표 윈도우 설정 ──
#    make_hsi_signal_inputs()의 기본 6개 컬럼 계산 기간 (거래일 기준)
SIGNAL_INPUT_PARAMS = {
    "ret_1m_window":   21,    # 1개월 수익률
    "ret_3m_window":   63,    # 3개월 수익률
    "ma_gap_window":   60,    # 이동평균 이격도 기준 MA 기간
    "momentum_windows": [21, 63, 126],  # 모멘텀(다기간 평균)
    "vol_window":      20,    # 변동성(연율화)
    "rs_window":       21,    # 상대강도 기준 기간
}

# ── 입력 #8) 확장 파라미터 — 확장 컬럼(ret_6m 등) 계산에 사용 ──
#    main_v3 후보(ma20_gap, ma60_gap, vol20, drawdown_60, risk_vs_cash_ret20)와 연결.
EXTENDED_PARAMS = {
    "ret_6m":           126,   # 6개월 수익률
    "ret_12m":          252,   # 12개월 수익률
    "ma_short_window":  20,    # 단기 이동평균(이격도)
    "ma_mid_window":    60,    # 중기 이동평균(이격도)
    "vol_short_window": 20,    # 단기 변동성
    "drawdown_window":  60,    # 낙폭/충격 집계 기간
    "rs_short_window":  20,    # 방어자산 상대강도(risk_vs_cash) 기간
    "shock_threshold":  0.03,  # 일간 -3% 이상 급락을 '충격'으로 집계
}

# (비중 규칙 후보·거래비용 가정 입력은 Grid Search/Robustness 파트 항목으로
#  데이터 파트 범위에서 제외 — WEIGHT_RULE_CONFIG / COST_ASSUMPTION_CONFIG 삭제)


# 입력 항목 명세 (docx 'HSI 입력 구조표' 기반, 데이터 파트 범위)
#   key      : collect_hsi_inputs() 반환 dict의 키
#   status   : "제공" = 이 모듈이 직접 공급 | "부분" | "예정"(타 파트)
#   source   : 이 모듈에서 해당 입력을 만드는 객체/함수
HSI_INPUT_STRUCTURE = [
    {"no": 1,  "key": "etf_info",
     "category": "ETF 후보 정보", "object": "etf_info.csv",
     "columns": "ticker, name, asset_class, risk_group, listing_date, note",
     "description": "실험 대상 ETF의 기본 정보 표. 후보 선정의 출발점.",
     "next_step": "ETF 유니버스 선정",
     "source": "make_etf_info_table() / ETF_UNIVERSE", "status": "제공"},
    {"no": 2,  "key": "selection_criteria",
     "category": "ETF 선정 기준", "object": "selection_criteria",
     "columns": "min_data_years, reference_year, exclude_leverage, "
                "exclude_inverse, required_asset_classes",
     "description": "ETF 포함/제외 기준. 최소 사용기간·레버리지/인버스 제외 등.",
     "next_step": "최종 ETF 유니버스 확정",
     "source": "SELECTION_CRITERIA", "status": "제공"},
    {"no": 3,  "key": "raw_prices",
     "category": "원천 가격 데이터", "object": "korea_etf.csv / 개별 가격 파일",
     "columns": "Date, Open, High, Low, Close, Volume",
     "description": "ETF별 일별 가격. 월말 가격·월간 수익률·HSI 원신호의 기초.",
     "next_step": "전처리 및 리샘플링",
     "source": "load_price_data() / load_volume_data()", "status": "제공"},
    {"no": 4,  "key": "monthly_prices",
     "category": "전처리 가격 데이터", "object": "monthly_prices.csv",
     "columns": "Date, ETF별 월말 가격 컬럼",
     "description": "일별 데이터를 월말 기준으로 정리한 가격표.",
     "next_step": "월간 수익률 계산",
     "source": "make_monthly_price_table()", "status": "제공"},
    {"no": 5,  "key": "monthly_returns",
     "category": "월간 수익률 데이터", "object": "monthly_returns.csv",
     "columns": "Date, ETF별 월간 수익률 컬럼",
     "description": "백테스트 성과 계산에 쓰는 월간 수익률 데이터.",
     "next_step": "신호 계산 / 성과 계산",
     "source": "make_monthly_return_table()", "status": "제공"},
    {"no": 6,  "key": "benchmark_info",
     "category": "기준 자산 정보", "object": "benchmark_info / 변수",
     "columns": "benchmark_ticker",
     "description": "상대강도 계산 기준이 되는 ETF/시장지수 정보.",
     "next_step": "상대강도 계산",
     "source": "BENCHMARK_TICKER", "status": "제공"},
    {"no": 7,  "key": "default_params",
     "category": "HSI 기본 파라미터", "object": "DEFAULT_PARAMS",
     "columns": "ret_window, ma_window, momentum_window, vol_window, rs_window",
     "description": "HSI 5지표 계산에 필요한 기간 설정(기본형 기준값).",
     "next_step": "입력 신호 계산",
     "source": "DEFAULT_PARAMS", "status": "제공"},
    {"no": 8,  "key": "extended_params",
     "category": "확장 파라미터", "object": "EXTENDED_PARAMS",
     "columns": "ret_6m, ret_12m, ma_short_window, ma_mid_window, "
                "vol_short_window, drawdown_window, rs_short_window, shock_threshold",
     "description": "확장 컬럼(ret_6m·ret_12m·drawdown·shock_count·defensive_rs) 계산 조건.",
     "next_step": "확장 실험",
     "source": "EXTENDED_PARAMS / make_hsi_signal_inputs(include_extended=True)",
     "status": "제공"},
    {"no": 9,  "key": "quality_rules",
     "category": "데이터 품질 점검 기준", "object": "quality_rules",
     "columns": "결측치 허용 기준, 최소 관측기간, 거래량/거래대금 기준",
     "description": "데이터 사용 가능 여부 판단 기준(결측·기간·유동성).",
     "next_step": "유니버스 정제",
     "source": "QUALITY_RULES", "status": "제공"},
    {"no": 10, "key": "asset_class_rules",
     "category": "자산군 분류 기준", "object": "asset_class_rules",
     "columns": "주식형 / 채권형 / 금 / 달러 / 원자재 / 대체자산 등",
     "description": "ETF를 자산군으로 묶는 기준(위험·방어 자산 구분).",
     "next_step": "비중 조절 규칙 설계",
     "source": "ASSET_CLASS_META / UNDERLYING_ASSET_META", "status": "제공"},
    {"no": 11, "key": "signal_direction_map",
     "category": "신호 방향 정의", "object": "signal_direction_map.csv",
     "columns": "signal_name, raw_direction, hsi_sign, interpretation",
     "description": "각 입력 신호의 위험 악화/완화 방향 정의(부호 통일 근거).",
     "next_step": "HSI 점수화 / direction 계산",
     "source": "SIGNAL_DIRECTION_MAP", "status": "제공"},
    {"no": 12, "key": "scaling_config",
     "category": "점수화 방식 설정", "object": "scaling_config",
     "columns": "method, window, score_range, note",
     "description": "원신호를 HSI 점수로 변환하는 방식(rank/z-score 비교).",
     "next_step": "HSI 점수화 비교",
     "source": "SCALING_CONFIG", "status": "제공"},
    # (비중 규칙 후보·거래비용 가정 입력은 Grid Search/Robustness 파트 항목으로 제외)
]


def make_hsi_input_table():
    """HSI 입력 구조표(14개 항목)를 DataFrame으로 반환."""
    rows = []
    for item in HSI_INPUT_STRUCTURE:
        rows.append({
            "번호":        item["no"],
            "입력 구분":   item["category"],
            "파일명/객체": item["object"],
            "필수 컬럼":   item["columns"],
            "설명":        item["description"],
            "다음 단계":   item["next_step"],
            "공급원":      item["source"],
            "상태":        item["status"],
        })
    return pd.DataFrame(rows)


def print_hsi_input_table(df=None):
    """HSI 입력 구조표를 콘솔 격자 표로 출력 (한글 폭 보정)."""
    if df is None:
        df = make_hsi_input_table()

    n_total = len(df)
    n_ready = (df["상태"] == "제공").sum()

    print("=" * 96)
    print("[추가 기능 1] HSI 입력 구조표 — 14개 입력 항목")
    print("=" * 96)
    print(f"  총 {n_total}개 항목 중 이 모듈 직접 공급: {n_ready}개 / 타 파트 예정: {n_total - n_ready}개")
    print()

    headers = ["번호", "입력 구분", "파일명/객체", "공급원", "상태"]
    aligns  = ["right", "left", "left", "left", "center"]
    rows = []
    for _, r in df.iterrows():
        mark = "✓ 제공" if r["상태"] == "제공" else f"  {r['상태']}"
        rows.append([str(r["번호"]), r["입력 구분"], r["파일명/객체"],
                     r["공급원"], mark])
    _print_grid(headers, rows, aligns)
    print()
    print("  ※ 필수 컬럼·설명·다음 단계는 합본 hsi_data_bundle.xlsx(시트=input_structure) 참고")
    print()


def collect_hsi_inputs(prices=None, volumes=None, universe=None, params=None):
    """
    14개 입력 항목을 실제 객체로 '받아와서' 하나의 dict로 묶어 반환.

    docx 'HSI 입력 구조표'의 각 항목을 이 모듈이 제공 가능한 형태로 수집한다.
    제공 불가(타 파트 예정) 항목은 placeholder(None) 그대로 담아 키를 보존한다.

    Parameters
    ----------
    prices   : load_price_data() 반환값. None이면 가격 의존 항목(#3·4·5)은 None.
    volumes  : load_volume_data() 반환값. None이면 거래량은 미수집.
    universe : ETF_UNIVERSE 딕셔너리. None이면 전역 값 사용.
    params   : HSI 기본 파라미터. None이면 DEFAULT_PARAMS 사용.

    Returns
    -------
    OrderedDict — {key: 입력 객체}  (키 순서는 입력 구조표 번호 순)
    """
    if universe is None:
        universe = ETF_UNIVERSE
    if params is None:
        params = DEFAULT_PARAMS

    raw_prices = None
    if prices is not None:
        raw_prices = {"close": prices, "volume": volumes}

    monthly_prices  = make_monthly_price_table(prices)  if prices is not None else None
    monthly_returns = make_monthly_return_table(prices) if prices is not None else None

    inputs = OrderedDict()
    inputs["etf_info"]               = make_etf_info_table(universe)
    inputs["selection_criteria"]     = SELECTION_CRITERIA
    inputs["raw_prices"]             = raw_prices
    inputs["monthly_prices"]         = monthly_prices
    inputs["monthly_returns"]        = monthly_returns
    inputs["benchmark_info"]         = {"benchmark_ticker": BENCHMARK_TICKER}
    inputs["default_params"]         = params
    inputs["extended_params"]        = EXTENDED_PARAMS
    inputs["quality_rules"]          = QUALITY_RULES
    inputs["asset_class_rules"]      = ASSET_CLASS_META
    inputs["signal_direction_map"]   = SIGNAL_DIRECTION_MAP
    inputs["scaling_config"]         = SCALING_CONFIG
    return inputs


def print_collected_inputs(inputs):
    """collect_hsi_inputs() 결과를 항목별 수집 상태로 요약 출력."""
    key2cat = {it["key"]: it["category"] for it in HSI_INPUT_STRUCTURE}

    print("=" * 96)
    print("[추가 기능 1] 입력 항목 수집 결과 (collect_hsi_inputs)")
    print("=" * 96)

    headers = ["번호", "입력 구분", "수집 키", "수집 상태"]
    aligns  = ["right", "left", "left", "left"]
    rows = []
    for no, (key, val) in enumerate(inputs.items(), 1):
        if val is None:
            state = "미수집 (None — 타 파트/데이터 필요)"
        elif isinstance(val, pd.DataFrame):
            state = f"수집됨 (DataFrame {val.shape[0]}×{val.shape[1]})"
        elif isinstance(val, dict):
            state = f"수집됨 (dict, {len(val)}개 키)"
        else:
            state = f"수집됨 ({type(val).__name__})"
        rows.append([str(no), key2cat.get(key, ""), key, state])
    _print_grid(headers, rows, aligns)
    print()


def make_signal_direction_table():
    """입력 #11 / 출력 #18) 신호 방향 정의표를 DataFrame으로 반환."""
    rows = []
    for sig, meta in SIGNAL_DIRECTION_MAP.items():
        rows.append({
            "signal_name":     sig,
            "raw_direction":   meta["raw_direction"],
            "hsi_sign":        meta["hsi_sign"],
            "interpretation":  meta["interpretation"],
        })
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────
# 15. [추가 기능 2] HSI 출력 구조표 (24개 항목)
#     docx 'HSI 출력 구조표'를 산출물 카탈로그 표로 제공.
#     각 산출물의 담당 파트·구현 상태·생성 함수를 한눈에.
# ──────────────────────────────────────────────────────────────

# 데이터 파트 산출물 카탈로그 — docx 'CSV 역할 구분'의 6개 역할 그룹 기준.
#   role         : 6개 역할 그룹 (docx 1번 표)
#   bundle_table : 합본 워크북(hsi_data_bundle.xlsx)에서 이 산출물이 들어가는 시트명
#   status       : "산출"(현재 생성 가능) | "부분"
#   ※ Grid Search / Robustness / Turnover·거래비용 / 백테스트 산출물은
#     후속 파트 담당이라 본 카탈로그(데이터 파트 범위)에서 제외함.
HSI_OUTPUT_STRUCTURE = [
    # ── ① ETF 기본 정보 / 자산군 분류 ──────────────────────────
    {"no": 1, "role": "①ETF·자산군", "category": "ETF 기본정보표",
     "columns": "ticker, name, asset_class, risk_group, listing_date, data_years, note",
     "meaning": "실험 대상 ETF 후보·자산군·위험그룹 기본 정보.",
     "producer": "make_etf_info_table()", "bundle_table": "etf_info", "status": "산출"},
    {"no": 2, "role": "①ETF·자산군", "category": "자산군 분류표",
     "columns": "ticker, asset_class_kr, underlying_asset, role, risk_level, "
                "coverage_count, discussion_note",
     "meaning": "자산군·추종자산·위험등급 분류와 분류 논의 항목.",
     "producer": "make_asset_class_table()", "bundle_table": "asset_class", "status": "산출"},
    # ── ② 월말 가격 / 월간 수익률 ──────────────────────────────
    {"no": 3, "role": "②가격·수익률", "category": "월말 가격표",
     "columns": "year_month, ticker, month_end_price",
     "meaning": "리밸런싱 기준 월말 종가.",
     "producer": "make_monthly_price_table()", "bundle_table": "monthly_price", "status": "산출"},
    {"no": 4, "role": "②가격·수익률", "category": "월간 수익률표",
     "columns": "year_month, ticker, monthly_return",
     "meaning": "전략 성과 계산의 기본 입력(월간 수익률 %).",
     "producer": "make_monthly_return_table()", "bundle_table": "monthly_return", "status": "산출"},
    # ── ③ HSI 입력 신호 ────────────────────────────────────────
    {"no": 5, "role": "③HSI 입력신호", "category": "HSI 입력 신호표(원신호)",
     "columns": "ret_1m, ret_3m, ma_gap, momentum, volatility, relative_strength "
                "(+확장: ret_6m, ret_12m, drawdown, shock_count, defensive_rs)",
     "meaning": "HSI 계산 직전 단계의 원신호(부호 반전 전 실제값).",
     "producer": "make_hsi_signal_inputs()", "bundle_table": "signal_inputs", "status": "산출"},
    # ── ④ 점수화 전후 중간 산출물 ──────────────────────────────
    {"no": 6, "role": "④점수화 중간", "category": "지표 점수표(raw scores)",
     "columns": "date, ticker, score_return/ma_pos/momentum/vol/rs (-10~+10)",
     "meaning": "표준화·부호 통일 후 지표별 점수.",
     "producer": "make_hsi_signal_table()['raw_scores']", "bundle_table": "raw_scores", "status": "산출"},
    {"no": 7, "role": "④점수화 중간", "category": "HSI 방향 점수표",
     "columns": "date, ticker, direction (-1~+1)",
     "meaning": "위험 악화/완화 방향성 점수.",
     "producer": "make_hsi_signal_table()['hsi_direction']", "bundle_table": "hsi_direction", "status": "산출"},
    {"no": 8, "role": "④점수화 중간", "category": "HSI 상태 분류표",
     "columns": "date, ticker, signal (buy/watch/caution)",
     "meaning": "방향 임계 기준 상태 라벨(3단계).",
     "producer": "make_hsi_signal_table()['hsi_signal']", "bundle_table": "hsi_signal", "status": "부분"},
    {"no": 9, "role": "④점수화 중간", "category": "신호 방향 정의표",
     "columns": "signal_name, raw_direction, hsi_sign, interpretation",
     "meaning": "각 신호의 위험 악화/완화 방향 정의(부호 반전 근거).",
     "producer": "make_signal_direction_table()", "bundle_table": "signal_direction_map", "status": "산출"},
    # ── ⑤ 최신 상태 확인용 snapshot ───────────────────────────
    {"no": 10, "role": "⑤snapshot", "category": "HSI 최신 snapshot",
     "columns": "ticker, date, direction, intensity, signal, score_*",
     "meaning": "기준일 HSI 점수·상태 요약(빠른 확인용).",
     "producer": "make_hsi_signal_table()['snapshot']", "bundle_table": "snapshot", "status": "산출"},
    # ── ⑥ 품질 점검표 ─────────────────────────────────────────
    {"no": 11, "role": "⑥품질 점검", "category": "데이터 기간 점검표",
     "columns": "ticker, listing_date, data_start_actual, data_end, trading_days, status",
     "meaning": "상장일 대비 실제 사용 가능 기간 확인.",
     "producer": "check_data_period()", "bundle_table": "data_period", "status": "산출"},
    {"no": 12, "role": "⑥품질 점검", "category": "결측치 점검표",
     "columns": "ticker, total_rows, missing_count, missing_pct, ffill_applied",
     "meaning": "ETF별 결측치 현황·처리 방법.",
     "producer": "check_missing_values()", "bundle_table": "missing_summary", "status": "산출"},
    {"no": 13, "role": "⑥품질 점검", "category": "유동성 점검표",
     "columns": "ticker, avg_daily_volume, avg_daily_turnover_krw, overall_pass, status",
     "meaning": "거래량·거래대금 기준 유동성 점검.",
     "producer": "check_liquidity()", "bundle_table": "liquidity_check", "status": "산출"},
    {"no": 14, "role": "⑥품질 점검", "category": "제외 사유표",
     "columns": "ticker, name, reason",
     "meaning": "후보 미선정·제외 사유 기록.",
     "producer": "PreprocessingLog.exclusions", "bundle_table": "exclusions", "status": "산출"},
]


def make_hsi_output_table():
    """데이터 파트 산출물 카탈로그를 DataFrame으로 반환."""
    rows = []
    for item in HSI_OUTPUT_STRUCTURE:
        rows.append({
            "번호":        item["no"],
            "역할 그룹":   item["role"],
            "출력 구분":   item["category"],
            "주요 컬럼":   item["columns"],
            "의미":        item["meaning"],
            "생성 함수":   item["producer"],
            "합본 시트":   item["bundle_table"],
            "상태":        item["status"],
        })
    return pd.DataFrame(rows)


def print_hsi_output_table(df=None):
    """데이터 파트 산출물 카탈로그를 콘솔 격자 표로 출력 (한글 폭 보정)."""
    if df is None:
        df = make_hsi_output_table()

    status_mark = {"산출": "✓ 산출", "부분": "△ 부분"}

    n_total = len(df)
    n_now   = (df["상태"] == "산출").sum()
    n_part  = (df["상태"] == "부분").sum()
    n_role  = df["역할 그룹"].nunique()

    print("=" * 100)
    print("HSI 데이터 파트 산출물 카탈로그 (6개 역할 그룹)")
    print("=" * 100)
    print(f"  총 {n_total}개 산출물 / {n_role}개 역할 그룹  |  "
          f"산출 {n_now}개 · 부분 {n_part}개  |  모두 하나의 hsi_data_bundle.xlsx(표별 시트)로 합본")
    print()

    headers = ["번호", "역할 그룹", "출력 구분", "합본 시트", "상태", "생성 함수"]
    aligns  = ["right", "left", "left", "left", "center", "left"]
    rows = []
    for _, r in df.iterrows():
        rows.append([
            str(r["번호"]), r["역할 그룹"], r["출력 구분"],
            r["합본 시트"], status_mark.get(r["상태"], r["상태"]), r["생성 함수"],
        ])
    _print_grid(headers, rows, aligns)
    print()
    print("  범례  ✓ 산출=현재 바로 생성  |  △ 부분=일부만(3단계 상태 등)")
    print("  ※ Grid Search / Robustness / Turnover·거래비용 / 백테스트는 후속 파트 담당(제외)")
    print()


# ──────────────────────────────────────────────────────────────
# 16. [추가 기능] 산출물 합본 (엑셀 워크북 — 표별 시트 분리)
#     여러 개로 흩어지던 CSV를 하나의 hsi_data_bundle.xlsx로 통합.
#     각 산출물을 원래 형태(wide/tidy) 그대로 별도 시트에 저장한다.
#       시트 예: etf_info, monthly_price, signal_inputs, raw_scores ...
# ──────────────────────────────────────────────────────────────

def build_data_workbook(*, etf_info=None, asset_class=None,
                        monthly_price=None, monthly_return=None,
                        signal_inputs=None, raw_scores=None,
                        hsi_direction=None, hsi_signal=None, snapshot=None,
                        signal_direction_map=None,
                        data_period=None, missing_summary=None,
                        liquidity_check=None, exclusions=None,
                        input_structure=None, output_structure=None):
    """
    데이터 파트 산출물들을 (시트명 → (DataFrame, 인덱스 저장 여부)) 묶음으로 정리.

    넘겨준(None이 아닌) 표만 포함된다. 시계열·점수표는 날짜 인덱스를 보존하기
    위해 index=True로, 행 단위 표(tidy)는 index=False로 저장한다.

    Returns
    -------
    OrderedDict[str, (pd.DataFrame, bool)]
    """
    # (시트명, DataFrame, 인덱스 저장 여부) — index=True면 날짜/연월 인덱스 보존
    spec = [
        ("input_structure",      input_structure,      False),
        ("output_structure",     output_structure,     False),
        ("etf_info",             etf_info,             False),
        ("asset_class",          asset_class,          False),
        ("monthly_price",        monthly_price,        True),   # index=연월
        ("monthly_return",       monthly_return,       True),   # index=연월
        ("signal_inputs",        signal_inputs,        False),  # Date 컬럼 보유
        ("raw_scores",           raw_scores,           True),   # index=날짜
        ("hsi_direction",        hsi_direction,        True),   # index=날짜
        ("hsi_signal",           hsi_signal,           True),   # index=날짜
        ("signal_direction_map", signal_direction_map, False),
        ("snapshot",             snapshot,             False),
        ("data_period",          data_period,          False),
        ("missing_summary",      missing_summary,      False),
        ("liquidity_check",      liquidity_check,      False),
    ]

    sheets = OrderedDict()
    for name, df, keep_index in spec:
        if df is not None:
            sheets[name] = (df, keep_index)
    if exclusions is not None and len(exclusions) > 0:
        sheets["exclusions"] = (pd.DataFrame(exclusions), False)
    return sheets


def save_data_workbook(sheets, path="hsi_data_bundle.xlsx"):
    """
    시트 묶음을 하나의 엑셀 워크북으로 저장.

    Parameters
    ----------
    sheets : build_data_workbook() 반환값 — {시트명: (DataFrame, index여부)}
    path   : 저장 경로 (.xlsx)
    """
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, (df, keep_index) in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=keep_index)
    return path


def print_data_workbook_summary(sheets, path="hsi_data_bundle.xlsx"):
    """워크북에 포함된 시트별 행·열 수를 요약 출력."""
    print("=" * 80)
    print(f"산출물 합본 저장 완료 → {path}")
    print("=" * 80)
    print(f"  {len(sheets)}개 산출물을 표별 시트로 분리해 워크북 1개로 저장")
    print()
    headers = ["시트(table)", "행", "열", "인덱스"]
    aligns  = ["left", "right", "right", "center"]
    rows = []
    for name, (df, keep_index) in sheets.items():
        ncol = df.shape[1] + (1 if keep_index else 0)
        rows.append([name, f"{df.shape[0]:,}", str(ncol),
                     "포함" if keep_index else "-"])
    _print_grid(headers, rows, aligns)
    print()


# ──────────────────────────────────────────────────────────────
# 17. 실행 예시 (직접 실행 시)
#     산출물은 모두 hsi_data_bundle.xlsx 하나(표별 시트)로 합본 저장
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ── [추가 기능 3] 전처리 로그 시작 ────────────────────────
    log = PreprocessingLog()

    # ── ① ETF 유니버스 기준 확인 ──────────────────────────────
    candidates = build_etf_candidates()
    selected   = select_etf(candidates)
    print_selection_report(candidates, selected)
    ETF_UNIVERSE = build_etf_universe(selected)

    log.step(f"ETF 선정 완료: 후보 {len(candidates)}종목 중 {len(selected)}종목 선정")
    log_etf_exclusions(log, candidates, selected)   # 미선정 사유 기록

    # ── ② ETF 기본정보표 ──────────────────────────────────────
    etf_info_df = make_etf_info_table()
    print_etf_info_table(etf_info_df)

    # ── ③ 자산군 분류표 + 추종 자산 구분 + 논의 항목 ────────────
    asset_class_df = make_asset_class_table()
    print_asset_class_table(asset_class_df)          # 추종 자산 컬럼 포함
    print_discussion_notes(asset_class_df)           # 분류 논의 항목

    # ── 입력 구조표 / 출력 카탈로그 / 신호 방향 정의표 (데이터 불필요) ──
    input_df   = make_hsi_input_table()
    print_hsi_input_table(input_df)
    output_df  = make_hsi_output_table()
    print_hsi_output_table(output_df)
    sig_dir_df = make_signal_direction_table()       # 신호 방향 정의표

    # ── ④⑤⑥⑦⑧ 실데이터 필요 구간 ───────────────────────────
    print("데이터 로드 중 (yfinance)...")
    tickers = list(ETF_UNIVERSE.keys())

    # 데이터 의존 산출물 (로드 실패 시 None 유지 → 합본은 부분 저장)
    period_df = summary_df = liquidity_df = None
    signal_inputs = signal_tables = None

    try:
        prices = load_price_data(tickers=tickers, start=DATA_START_DATE,
                                 source="yfinance")
        print(f"로드 완료: {prices.shape[0]}일 × {prices.shape[1]}개 종목\n")
        log.step(f"가격 데이터 로드: {prices.shape[0]}일 × {prices.shape[1]}종목 "
                 f"(시작 {DATA_START_DATE}, ffill 적용)")

        # ── ④ 상장일 및 데이터 기간 확인 ─────────────────────
        period_df = check_data_period(prices)
        print_data_period(period_df)
        for _, r in period_df.iterrows():
            if r["status"] != "정상":
                log.exclude(r["ticker"], r["name"],
                            f"데이터 기간 점검: {r['status']}", echo=False)
        log.step("상장일·데이터 기간 점검 완료")

        # ── ⑤ 결측치 확인 ────────────────────────────────────
        summary_df, yearly_df = check_missing_values(prices)
        print_missing_values(summary_df, yearly_df)
        total_missing = int(summary_df["missing_count"].sum())
        log.step(f"결측치 점검 완료: 총 결측 {total_missing}건 (load_price_data 내 ffill 처리)")

        # ── ⑤-2. 거래량/거래대금 유동성 확인 ──────────────────
        print("거래량 데이터 로드 중...")
        try:
            volumes = load_volume_data(tickers=tickers, start=DATA_START_DATE,
                                       source="yfinance")
            print(f"거래량 로드 완료: {volumes.shape[0]}일 × {volumes.shape[1]}개 종목\n")
        except Exception as ve:
            print(f"[주의] 거래량 로드 실패: {ve}")
            volumes = None

        liquidity_df = check_liquidity(prices, volumes=volumes)
        print_liquidity_check(liquidity_df)
        for _, r in liquidity_df.iterrows():
            if r["overall_pass"] is False:
                log.exclude(r["ticker"], r["name"],
                            f"유동성 점검 미달: {r['status']}", echo=False)
        log.step("거래량·거래대금 유동성 점검 완료")

        # ── ⑥⑦ 월말 가격표 / 월간 수익률표 ──────────────────
        print_monthly_tables(prices, tail_n=12)
        monthly_price_df  = make_monthly_price_table(prices)
        monthly_return_df = make_monthly_return_table(prices)
        log.step("월말 가격표·월간 수익률표 리샘플링 완료")

        # ── ⑥ HSI 기본 입력 신호표 (원신호) ──────────────────
        signal_inputs = make_hsi_signal_inputs(
            prices, include_extended=True, log=log)
        print_hsi_signal_inputs(signal_inputs)

        # ── ⑧ HSI 표준화 점수표 (direction/intensity/state) ──
        signal_tables = make_hsi_signal_table(prices)
        print_hsi_signal_table(signal_tables)
        log.step("HSI 표준화 점수·direction/intensity 산출 완료")

        # ── 입력 항목을 실제 객체로 수집 ─────────────────────
        hsi_inputs = collect_hsi_inputs(prices=prices, volumes=volumes)
        print_collected_inputs(hsi_inputs)

    except Exception as e:
        print(f"[주의] 데이터 로드 실패: {e}")
        print("source='csv' 모드로 ./data/{ticker}.csv 파일을 사용하거나")
        print("yfinance 설치 후 재시도하세요: pip install yfinance")
        log.step(f"중단: 데이터 로드/처리 실패 — {e}", echo=False)
        monthly_price_df = monthly_return_df = None

    # ── 산출물 합본 저장 (엑셀 워크북 — 표별 시트) ────────────
    #    데이터 로드 성공 여부와 무관하게, 확보된 표만 모아 하나로 저장.
    sheets = build_data_workbook(
        input_structure=input_df,
        output_structure=output_df,
        etf_info=etf_info_df,
        asset_class=asset_class_df,
        monthly_price=monthly_price_df,
        monthly_return=monthly_return_df,
        signal_inputs=signal_inputs,
        raw_scores=(signal_tables or {}).get("raw_scores"),
        hsi_direction=(signal_tables or {}).get("hsi_direction"),
        hsi_signal=(signal_tables or {}).get("hsi_signal"),
        snapshot=(signal_tables or {}).get("snapshot"),
        signal_direction_map=sig_dir_df,
        data_period=period_df,
        missing_summary=summary_df,
        liquidity_check=liquidity_df,
        exclusions=log.exclusions,
    )
    save_data_workbook(sheets, "hsi_data_bundle.xlsx")
    print_data_workbook_summary(sheets, "hsi_data_bundle.xlsx")
    log.step(f"산출물 합본 저장: hsi_data_bundle.xlsx ({len(sheets)}개 시트)", echo=False)

    # ── 전처리 로그 저장 (사람용 보고서) ──────────────────────
    log.note("산출물은 hsi_data_bundle.xlsx 하나로 합본 (표별 시트 분리)")
    log.note("Grid Search / Robustness / Turnover·거래비용 / 백테스트는 후속 파트 담당(본 모듈 제외)")
    log.save("preprocessing_log.md")
    print("→ preprocessing_log.md 저장 완료\n")

    print("=" * 80)
    print("데이터 파트 산출물 생성 완료 → hsi_data_bundle.xlsx + preprocessing_log.md")
    print("Grid Search / Robustness는 후속 파트에서 별도 진행 (본 모듈 범위 외)")
    print("=" * 80)
