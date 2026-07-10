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

※ Grid Search / HSI 상태 기준 / 파라미터 조합 / 비중 조절 규칙:
   → HSI_gridsearch_experiment.py 참고 (HSI 설계 파트에서 연결 예정)
"""

import os
import warnings

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

    전체 기간 및 연도별 결측치 수를 집계한다.

    Returns
    -------
    summary_df  : ticker | name | total_rows | missing_count | missing_pct | ffill_applied
    yearly_df   : 연도별 결측치 수 피벗 테이블 (ticker × year)

    수정 포인트
    ----------
    기존 코드에서는 groupby("year").apply() 안에서
    g.drop(columns="year")를 실행했는데, pandas 버전에 따라
    groupby 이후 그룹 데이터에 "year" 컬럼이 남아 있지 않을 수 있다.

    따라서 year 컬럼을 만들고 삭제하는 방식 대신,
    prices.isna() 결과를 바로 연도별로 groupby하여 계산한다.
    """
    if universe is None:
        universe = ETF_UNIVERSE

    # 인덱스가 DatetimeIndex가 아닐 경우를 대비해 변환
    prices = prices.copy()
    prices.index = pd.to_datetime(prices.index)

    # 전체 결측치 집계
    summary_rows = []

    for ticker in prices.columns:
        total = len(prices[ticker])
        missing = prices[ticker].isna().sum()
        pct = round(missing / total * 100, 2) if total > 0 else 0

        meta = universe.get(ticker, {})

        summary_rows.append({
            "ticker": ticker,
            "name": meta.get("name", ticker),
            "total_rows": total,
            "missing_count": int(missing),
            "missing_pct": f"{pct}%",
            "ffill_applied": "적용됨 (load_price_data 내부)",
        })

    summary_df = pd.DataFrame(summary_rows)

    # 연도별 결측치 집계
    # prices.isna()는 ticker별 True/False 표를 만들고,
    # index.year 기준으로 묶어서 결측 개수를 합산한다.
    yearly_missing = (
        prices
        .isna()
        .groupby(prices.index.year)
        .sum()
        .T
    )

    yearly_missing.index.name = "ticker"
    yearly_missing.columns.name = "year"

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
    raw_signals = {
        "return":   calc_return(prices,         window=p["return_window"]),
        "ma_pos":   calc_ma_position(prices,    windows=p["ma_windows"]),
        "momentum": calc_momentum(prices,       windows=p["momentum_windows"]),
        "vol":      calc_volatility(prices,     window=p["vol_window"]),
        "rs":       calc_relative_strength(prices, benchmark=benchmark,
                                           window=p["rs_window"]),
    }

    scored_signals = {}
    for name, sig in raw_signals.items():
        if p["standardize"] == "zscore":
            std_sig = standardize_zscore(sig, p["std_window"], p["std_min_periods"])
        else:
            std_sig = standardize_rank(sig, p["std_window"], p["std_min_periods"])
        scored_signals[name] = clip_to_score(std_sig, clip_z=p["clip_z"])

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

    # 개별 지표 원시 점수 계산
    raw_signals = {
        "return":   calc_return(prices,         window=p["return_window"]),
        "ma_pos":   calc_ma_position(prices,    windows=p["ma_windows"]),
        "momentum": calc_momentum(prices,       windows=p["momentum_windows"]),
        "vol":      calc_volatility(prices,     window=p["vol_window"]),
        "rs":       calc_relative_strength(prices, benchmark=benchmark,
                                           window=p["rs_window"]),
    }

    raw_score_frames = {}
    for sig_name, sig_df in raw_signals.items():
        if p["standardize"] == "zscore":
            std_sig = standardize_zscore(sig_df, p["std_window"], p["std_min_periods"])
        else:
            std_sig = standardize_rank(sig_df, p["std_window"], p["std_min_periods"])
        scored = clip_to_score(std_sig, clip_z=p["clip_z"])
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
            "rs_note":   "benchmark_self_comparison" if ticker == benchmark else "",
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
            score_texts = []
            
            for c in score_cols:
                signal_name = c.replace("score_", "")
                value = row[c]
            
                # benchmark ETF의 relative strength는 자기 자신과 비교하므로
                # 계산 의미가 없는 값이다. NaN을 오류처럼 보이지 않도록 표시만 바꾼다.
                if row["ticker"] == BENCHMARK_TICKER and signal_name == "rs":
                    score_texts.append(f"{signal_name}=benchmark")
                elif pd.isna(value):
                    score_texts.append(f"{signal_name}=N/A")
                else:
                    score_texts.append(f"{signal_name}={value:+.2f}")
            
            scores_str = "  ".join(score_texts)
            print(f"    지표 점수 : {scores_str}")
            print()


# ──────────────────────────────────────────────────────────────
# 13. 실행 예시 (직접 실행 시)
#     체크리스트 순서대로 산출물 생성
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ── ① ETF 유니버스 기준 확인 ──────────────────────────────
    candidates = build_etf_candidates()
    selected   = select_etf(candidates)
    print_selection_report(candidates, selected)
    ETF_UNIVERSE = build_etf_universe(selected)

    # ── ② ETF 기본정보표 ──────────────────────────────────────
    print_etf_info_table(make_etf_info_table())

    # ── ③ 자산군 분류표 + 추종 자산 구분 + 논의 항목 ────────────
    asset_class_df = make_asset_class_table()
    print_asset_class_table(asset_class_df)          # 추종 자산 컬럼 포함
    print_discussion_notes(asset_class_df)           # [기능 3] 분류 논의 항목

    # CSV 저장 (팀원 연결용 — discussion_note 컬럼 포함)
    asset_class_df.to_csv("asset_class_table.csv", index=False, encoding="utf-8-sig")
    print("→ asset_class_table.csv 저장 완료\n")

    # ── ④⑤⑥⑦⑧ 실데이터 필요 구간 ───────────────────────────
    print("데이터 로드 중 (yfinance)...")
    tickers = list(ETF_UNIVERSE.keys())

    try:
        prices = load_price_data(tickers=tickers, start=DATA_START_DATE,
                                 source="yfinance")
        print(f"로드 완료: {prices.shape[0]}일 × {prices.shape[1]}개 종목\n")

        # ── ④ 상장일 및 데이터 기간 확인 ─────────────────────
        period_df = check_data_period(prices)
        print_data_period(period_df)

        # ── ⑤ 결측치 확인 ────────────────────────────────────
        summary_df, yearly_df = check_missing_values(prices)
        print_missing_values(summary_df, yearly_df)

        # ── ⑤-2. [기능 1] 거래량/거래대금 유동성 확인 ──────────
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

        liquidity_df.to_csv("liquidity_check.csv", index=False, encoding="utf-8-sig")
        print("→ liquidity_check.csv 저장 완료\n")

        # ── ⑥⑦ 월말 가격표 / 월간 수익률표 ──────────────────
        print_monthly_tables(prices, tail_n=12)

        make_monthly_price_table(prices).to_csv(
            "monthly_price.csv", encoding="utf-8-sig")
        make_monthly_return_table(prices).to_csv(
            "monthly_return.csv", encoding="utf-8-sig")
        print("→ monthly_price.csv / monthly_return.csv 저장 완료\n")

        # ── ⑧ HSI 기본 입력 신호표 ───────────────────────────
        signal_tables = make_hsi_signal_table(prices)
        print_hsi_signal_table(signal_tables)

        signal_tables["snapshot"].to_csv(
            "hsi_signal_snapshot.csv", index=False, encoding="utf-8-sig")
        signal_tables["raw_scores"].to_csv(
            "hsi_raw_scores.csv", encoding="utf-8-sig")
        print("→ hsi_signal_snapshot.csv / hsi_raw_scores.csv 저장 완료\n")

        print("=" * 80)
        print("모든 산출물 생성 완료.")
        print("Grid Search / 파라미터 최적화 → HSI_gridsearch_experiment.py 참고")
        print("=" * 80)

    except Exception as e:
        print(f"[주의] 데이터 로드 실패: {e}")
        print("source='csv' 모드로 ./data/{ticker}.csv 파일을 사용하거나")
        print("yfinance 설치 후 재시도하세요: pip install yfinance")
