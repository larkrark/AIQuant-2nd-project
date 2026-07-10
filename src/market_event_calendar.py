"""
market_event_calendar.py
========================
HSI 해석용 시장 사건 달력 (2012-03-07 이후 적용본)

Purpose
-------
- Calendar / reference data only.
- Do NOT use this file directly for HSI signal calculation or portfolio weight decisions.
- Use it after HSI states and backtest results are produced, for:
  1) event-annotated HSI timeline,
  2) crisis / positive / mixed regime interpretation,
  3) theta sensitivity interpretation,
  4) robustness period definition.

Important distinction
---------------------
- HSI signal input: price-based indicators only.
- market_event_calendar: ex-post interpretation and validation helper.

ETF universe assumed
--------------------
- 069500: KODEX 200                  (equity / risk asset)
- 114260: KODEX 국고채3년             (bond / defensive asset)
- 153130: KODEX 단기채권PLUS          (short-term bond / cash-like asset)

Notes
-----
- Events before the common ETF data start date are intentionally omitted here.
- Some long regimes overlap. This is expected. Downstream code should allow
  multiple active events per month.
- expected_etf_impact is a hypothesis for interpretation, not a realized return.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Any

DATA_START_DATE = "2012-03-07"
ETF_TICKERS = ("069500", "114260", "153130")

IMPACT_VALUES = ("positive", "negative", "neutral", "mixed")
EVENT_DIRECTIONS = ("risk_off", "risk_on", "mixed", "neutral")
SPAN_TYPES = ("point", "window", "regime")


def _normalize_event(
    *,
    event_id: str,
    start_date: str,
    event_name: str,
    region: str,
    shock_type: str,
    analyst_theme: str,
    news_keywords: List[str],
    expected_etf_impact: Dict[str, str],
    end_date: Optional[str] = None,
    event_span_type: str = "point",
    event_direction: str = "risk_off",
    severity: int = 3,
    visual_priority: int = 2,
    reference_flag: bool = True,
    backtest_flag: bool = True,
    data_available_flag: bool = True,
    use_in_report: str = "appendix",
    source_note: str = "manual research / team review needed",
    caution: str = "",
) -> Dict[str, Any]:
    """Return one standardized event record."""
    if end_date is None:
        end_date = start_date

    if event_span_type not in SPAN_TYPES:
        raise ValueError(f"Invalid event_span_type: {event_span_type}")
    if event_direction not in EVENT_DIRECTIONS:
        raise ValueError(f"Invalid event_direction: {event_direction}")

    # Keep the calendar conservative: point/window/regime are analysis labels,
    # not strategy signals.
    return {
        "event_id": event_id,
        "start_date": start_date,
        "end_date": end_date,
        "event_span_type": event_span_type,
        "region": region,
        "event_name": event_name,
        "news_keywords": news_keywords,
        "analyst_theme": analyst_theme,
        "shock_type": shock_type,
        "event_direction": event_direction,
        "severity": int(severity),
        "visual_priority": int(visual_priority),
        "reference_flag": bool(reference_flag),
        "backtest_flag": bool(backtest_flag),
        "data_available_flag": bool(data_available_flag),
        "use_in_report": use_in_report,
        "expected_etf_impact": expected_etf_impact,
        "source_note": source_note,
        "caution": caution,
    }


market_event_calendar: Dict[str, Dict[str, Any]] = {
    # ------------------------------------------------------------------
    # 2012-2016: Korea / global risk, health, policy and trade shocks
    # ------------------------------------------------------------------
    "2013_taper_tantrum": _normalize_event(
        event_id="2013_taper_tantrum",
        start_date="2013-05-22",
        end_date="2013-09-18",
        event_span_type="window",
        region="US / Global / Korea",
        event_name="Taper Tantrum / US QE Taper Signal",
        news_keywords=["taper tantrum", "QE taper", "버냉키", "양적완화 축소", "금리상승"],
        analyst_theme="US taper signal, global yield shock, pressure on risk assets and duration-sensitive bonds",
        shock_type="monetary_tightening",
        event_direction="risk_off",
        severity=3,
        visual_priority=3,
        expected_etf_impact={"069500": "negative", "114260": "mixed", "153130": "neutral"},
        source_note="reference event; verify detailed Korean ETF impact with realized returns",
        caution="Bond ETF response may be mixed because risk-off demand and rate-rise pressure can conflict.",
    ),
    "2014_sewol_ferry_tragedy": _normalize_event(
        event_id="2014_sewol_ferry_tragedy",
        start_date="2014-04-16",
        region="Korea",
        event_name="Sewol Ferry Tragedy",
        news_keywords=["Sewol", "ferry tragedy", "세월호", "참사", "사회적 충격"],
        analyst_theme="Social trust shock, national mourning, domestic sentiment deterioration",
        shock_type="social_tragedy",
        event_direction="risk_off",
        severity=3,
        visual_priority=2,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="carried from original shock_calendar; team source check recommended",
    ),
    "2015_mers_outbreak_korea": _normalize_event(
        event_id="2015_mers_outbreak_korea",
        start_date="2015-05-20",
        end_date="2015-07-28",
        event_span_type="window",
        region="Korea",
        event_name="MERS Outbreak in Korea",
        news_keywords=["MERS", "outbreak", "메르스", "감염병", "보건위기", "소비위축"],
        analyst_theme="Public health shock, mobility and consumption slowdown, defensive preference",
        shock_type="pandemic",
        event_direction="risk_off",
        severity=3,
        visual_priority=2,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="carried from original shock_calendar; team source check recommended",
    ),
    "2015_china_devaluation_global_selloff": _normalize_event(
        event_id="2015_china_devaluation_global_selloff",
        start_date="2015-08-11",
        end_date="2015-08-24",
        event_span_type="window",
        region="China / Global",
        event_name="China Yuan Devaluation / Global Equity Selloff",
        news_keywords=["China devaluation", "yuan", "중국 위안화 절하", "Black Monday", "글로벌 증시 급락"],
        analyst_theme="China slowdown concern, global equity volatility, risk-off shock",
        shock_type="market_volatility_shock",
        event_direction="risk_off",
        severity=3,
        visual_priority=2,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="reference event; verify detailed Korean ETF impact with realized returns",
    ),
    "2016_brexit_referendum": _normalize_event(
        event_id="2016_brexit_referendum",
        start_date="2016-06-24",
        region="UK / Europe / Global",
        event_name="Brexit Referendum Shock",
        news_keywords=["Brexit", "referendum", "브렉시트", "유럽 정치 리스크"],
        analyst_theme="Global political uncertainty, temporary risk-off and safe-haven demand",
        shock_type="political_shock",
        event_direction="risk_off",
        severity=3,
        visual_priority=2,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="reference event; verify detailed Korean ETF impact with realized returns",
    ),
    "2016_thaad_conflict": _normalize_event(
        event_id="2016_thaad_conflict",
        start_date="2016-07-08",
        end_date="2017-10-31",
        event_span_type="window",
        region="Korea / China",
        event_name="THAAD Conflict / China Retaliation Risk",
        news_keywords=["THAAD", "사드", "China retaliation", "중국 보복", "한중 갈등"],
        analyst_theme="Diplomatic and trade tension, sector pressure, uncertainty in China-exposed Korean equities",
        shock_type="geopolitical_trade_conflict",
        event_direction="risk_off",
        severity=3,
        visual_priority=2,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="carried from original shock_calendar; team source check recommended",
    ),
    "2016_2017_korea_impeachment_period": _normalize_event(
        event_id="2016_2017_korea_impeachment_period",
        start_date="2016-12-09",
        end_date="2017-03-10",
        event_span_type="window",
        region="Korea",
        event_name="Park Geun-hye Impeachment Period",
        news_keywords=["impeachment", "박근혜 탄핵", "국정농단", "정치불확실성", "헌법재판소"],
        analyst_theme="Political uncertainty and governance transition; market impact may be neutral or mixed after institutional resolution",
        shock_type="political_event",
        event_direction="mixed",
        severity=2,
        visual_priority=2,
        expected_etf_impact={"069500": "neutral", "114260": "neutral", "153130": "neutral"},
        source_note="carried from original shock_calendar; team source check recommended",
        caution="Do not force a risk-off interpretation if realized market response was muted.",
    ),

    # ------------------------------------------------------------------
    # 2017-2020: Geopolitics, global trade conflict and pandemic
    # ------------------------------------------------------------------
    "2017_north_korea_missile_tension": _normalize_event(
        event_id="2017_north_korea_missile_tension",
        start_date="2017-09-03",
        end_date="2017-11-29",
        event_span_type="window",
        region="Korea / US / Global",
        event_name="North Korea Nuclear / Missile Tension",
        news_keywords=["North Korea", "missile", "nuclear test", "북한 미사일", "핵실험", "지정학 리스크"],
        analyst_theme="Geopolitical risk premium around Korean assets and temporary risk aversion",
        shock_type="geopolitical_tension",
        event_direction="risk_off",
        severity=3,
        visual_priority=3,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="reference event; team source check recommended",
    ),
    "2018_pyeongchang_olympics": _normalize_event(
        event_id="2018_pyeongchang_olympics",
        start_date="2018-02-09",
        end_date="2018-02-25",
        event_span_type="window",
        region="Korea",
        event_name="Pyeongchang Winter Olympics",
        news_keywords=["Pyeongchang", "Olympics", "평창올림픽", "평화", "국가 이미지"],
        analyst_theme="Peace sentiment, national branding, temporary confidence uplift",
        shock_type="sentiment_positive",
        event_direction="risk_on",
        severity=2,
        visual_priority=3,
        expected_etf_impact={"069500": "positive", "114260": "neutral", "153130": "neutral"},
        source_note="carried from original shock_calendar; team source check recommended",
    ),
    "2018_2019_us_china_trade_war": _normalize_event(
        event_id="2018_2019_us_china_trade_war",
        start_date="2018-07-06",
        end_date="2019-12-13",
        event_span_type="regime",
        region="US / China / Global / Korea",
        event_name="US-China Trade War Regime",
        news_keywords=["US-China trade war", "tariffs", "미중 무역전쟁", "관세", "수출주"],
        analyst_theme="Trade uncertainty, global supply-chain pressure, risk sentiment deterioration for export-sensitive markets",
        shock_type="trade_conflict",
        event_direction="risk_off",
        severity=4,
        visual_priority=2,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="reference event; verify detailed Korean ETF impact with realized returns",
        caution="Long regime; avoid overcrowding main timeline. Use in appendix or regime shading.",
    ),
    "2019_japan_export_restrictions": _normalize_event(
        event_id="2019_japan_export_restrictions",
        start_date="2019-07-01",
        end_date="2019-12-31",
        event_span_type="window",
        region="Korea / Japan",
        event_name="Japan Export Restrictions",
        news_keywords=["Japan export restrictions", "수출규제", "화이트리스트", "소부장", "한일 갈등"],
        analyst_theme="Supply-chain disruption, trade tension, domestic industrial resilience focus",
        shock_type="trade_conflict",
        event_direction="risk_off",
        severity=3,
        visual_priority=2,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="carried from original shock_calendar; team source check recommended",
    ),
    "2020_covid19_pandemic_korea_global": _normalize_event(
        event_id="2020_covid19_pandemic_korea_global",
        start_date="2020-01-20",
        end_date="2020-06-30",
        event_span_type="window",
        region="Korea / Global",
        event_name="COVID-19 Pandemic Shock / K-Quarantine Period",
        news_keywords=["COVID-19", "coronavirus", "코로나", "K-방역", "pandemic", "mobility collapse"],
        analyst_theme="Pandemic shock, mobility collapse, policy response, defensive allocation demand",
        shock_type="pandemic",
        event_direction="risk_off",
        severity=5,
        visual_priority=1,
        use_in_report="main",
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="carried from original shock_calendar; key crisis window for event-annotated HSI timeline",
    ),

    # ------------------------------------------------------------------
    # 2021-2024: China slowdown, war, rates, banking stress, AI cycle
    # ------------------------------------------------------------------
    "2021_2024_china_real_estate_crisis": _normalize_event(
        event_id="2021_2024_china_real_estate_crisis",
        start_date="2021-09-01",
        end_date="2024-12-31",
        event_span_type="regime",
        region="China / Global / Korea",
        event_name="China Real Estate Crisis / Evergrande Spillover",
        news_keywords=["Evergrande", "China real estate", "중국 부동산", "헝다", "부채위기"],
        analyst_theme="China slowdown, spillover uncertainty, pressure on export-sensitive Korean market sentiment",
        shock_type="macro_crisis",
        event_direction="risk_off",
        severity=3,
        visual_priority=3,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="carried from original shock_calendar; use mainly as background regime",
        caution="Long overlapping regime; do not interpret every month as a discrete shock.",
    ),
    "2022_russia_ukraine_war": _normalize_event(
        event_id="2022_russia_ukraine_war",
        start_date="2022-02-24",
        end_date="2022-03-31",
        event_span_type="window",
        region="Europe / Global",
        event_name="Russia-Ukraine War Shock",
        news_keywords=["Russia-Ukraine", "war", "러시아 우크라이나 전쟁", "지정학 리스크", "commodity inflation"],
        analyst_theme="Geopolitical shock, commodity inflation, risk-off and defensive demand",
        shock_type="geopolitical_war",
        event_direction="risk_off",
        severity=4,
        visual_priority=1,
        use_in_report="main",
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="carried from original shock_calendar; key crisis window",
    ),
    "2022_2024_us_rate_hike_cycle": _normalize_event(
        event_id="2022_2024_us_rate_hike_cycle",
        start_date="2022-03-16",
        end_date="2024-12-31",
        event_span_type="regime",
        region="US / Global / Korea",
        event_name="US Rate Hike Cycle / Higher-for-Longer Regime",
        news_keywords=["Fed hike", "rate hike", "긴축", "금리인상", "연준", "higher for longer"],
        analyst_theme="Monetary tightening, valuation compression, bond-duration pressure, cash preference",
        shock_type="monetary_tightening",
        event_direction="risk_off",
        severity=4,
        visual_priority=2,
        expected_etf_impact={"069500": "negative", "114260": "mixed", "153130": "positive"},
        source_note="Reuters reported the Fed's March 2022 liftoff and aggressive tightening path; use as long regime",
        caution="Bond impact is mixed because rate hikes can hurt bond prices even when investors prefer defensive assets.",
    ),
    "2022_itaewon_tragedy": _normalize_event(
        event_id="2022_itaewon_tragedy",
        start_date="2022-10-29",
        region="Korea",
        event_name="Itaewon Tragedy",
        news_keywords=["Itaewon", "tragedy", "이태원", "참사", "사회 충격"],
        analyst_theme="Social trauma, domestic sentiment shock, temporary risk aversion",
        shock_type="social_tragedy",
        event_direction="risk_off",
        severity=2,
        visual_priority=3,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="carried from original shock_calendar; team source check recommended",
    ),
    "2023_svb_banking_turmoil": _normalize_event(
        event_id="2023_svb_banking_turmoil",
        start_date="2023-03-10",
        end_date="2023-03-31",
        event_span_type="window",
        region="US / Global",
        event_name="Silicon Valley Bank Collapse / Banking Turmoil",
        news_keywords=["SVB", "Silicon Valley Bank", "bank failure", "은행위기", "regional banks"],
        analyst_theme="Financial-system confidence shock, liquidity preference, risk-off spillover to global markets",
        shock_type="financial_stress",
        event_direction="risk_off",
        severity=3,
        visual_priority=2,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="Reuters reported SVB as the largest bank failure since the 2008 financial crisis on 2023-03-10",
    ),
    "2023_2024_ai_semiconductor_cycle": _normalize_event(
        event_id="2023_2024_ai_semiconductor_cycle",
        start_date="2023-01-01",
        end_date="2024-12-31",
        event_span_type="regime",
        region="Global / Korea",
        event_name="AI / Semiconductor Upcycle",
        news_keywords=["AI", "semiconductor", "반도체", "엔비디아", "generative AI", "HBM"],
        analyst_theme="AI-led growth, semiconductor strength, risk-on support for Korean equity sentiment",
        shock_type="tech_boom",
        event_direction="risk_on",
        severity=3,
        visual_priority=2,
        expected_etf_impact={"069500": "positive", "114260": "neutral", "153130": "neutral"},
        source_note="carried from original shock_calendar; positive overlapping regime",
        caution="Overlaps with rate-hike and China-real-estate regimes, so conflict states may be meaningful.",
    ),
    "2023_israel_hamas_war": _normalize_event(
        event_id="2023_israel_hamas_war",
        start_date="2023-10-07",
        end_date="2023-12-31",
        event_span_type="window",
        region="Middle East / Global",
        event_name="Israel-Hamas War / Middle East Risk",
        news_keywords=["Israel-Hamas", "Gaza", "Middle East", "oil", "gold", "중동 리스크", "안전자산"],
        analyst_theme="Geopolitical risk, oil-price and safe-haven response, possible risk-off spillover",
        shock_type="geopolitical_war",
        event_direction="risk_off",
        severity=3,
        visual_priority=2,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="Reuters reported oil and gold safe-haven responses after the October 2023 conflict escalation",
    ),

    # ------------------------------------------------------------------
    # 2024-2025: Political shocks, technology outage, carry unwind, tariffs
    # ------------------------------------------------------------------
    "2024_korea_general_election": _normalize_event(
        event_id="2024_korea_general_election",
        start_date="2024-04-10",
        region="Korea",
        event_name="2024 Korea General Election",
        news_keywords=["election", "총선", "국회의원 선거", "정치 일정", "policy uncertainty"],
        analyst_theme="Political event, policy expectation reset, possible short-term sector rotation",
        shock_type="political_event",
        event_direction="neutral",
        severity=1,
        visual_priority=3,
        expected_etf_impact={"069500": "neutral", "114260": "neutral", "153130": "neutral"},
        source_note="carried from original shock_calendar; use as neutral political event",
    ),
    "2024_trump_assassination_attempt": _normalize_event(
        event_id="2024_trump_assassination_attempt",
        start_date="2024-07-13",
        region="US / Global",
        event_name="Trump Assassination Attempt / US Political Shock",
        news_keywords=["Trump", "assassination attempt", "미국 대선", "정치 리스크", "volatility"],
        analyst_theme="US political shock, volatility disturbance, risk sentiment uncertainty",
        shock_type="political_shock",
        event_direction="risk_off",
        severity=2,
        visual_priority=3,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="carried from original shock_calendar; team source check recommended",
    ),
    "2024_crowdstrike_global_it_outage": _normalize_event(
        event_id="2024_crowdstrike_global_it_outage",
        start_date="2024-07-19",
        end_date="2024-07-21",
        event_span_type="window",
        region="Global",
        event_name="Global IT Outage / CrowdStrike Incident",
        news_keywords=["CrowdStrike", "IT outage", "global outage", "전산장애", "보안사고", "Microsoft"],
        analyst_theme="Technology infrastructure shock, operational disruption, temporary risk aversion",
        shock_type="tech_operational_shock",
        event_direction="risk_off",
        severity=2,
        visual_priority=3,
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="Reuters reported a global outage affecting airlines, banking, healthcare and media on 2024-07-19",
    ),
    "2024_yen_carry_unwind_vol_spike": _normalize_event(
        event_id="2024_yen_carry_unwind_vol_spike",
        start_date="2024-08-05",
        region="Global",
        event_name="Global Equity Volatility Spike / Yen Carry Unwind",
        news_keywords=["volatility spike", "yen carry trade", "risk-off", "글로벌 변동성", "엔캐리 청산"],
        analyst_theme="Cross-asset de-risking, carry-trade unwind, global volatility shock",
        shock_type="market_volatility_shock",
        event_direction="risk_off",
        severity=4,
        visual_priority=1,
        use_in_report="main",
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="Reuters described the August 2024 selloff as linked to carry-trade unwind and a global risk-off move",
    ),
    "2024_korea_martial_law_shock": _normalize_event(
        event_id="2024_korea_martial_law_shock",
        start_date="2024-12-03",
        end_date="2024-12-04",
        event_span_type="window",
        region="Korea",
        event_name="Korea Martial-Law Emergency Shock",
        news_keywords=["martial law", "비상계엄", "정치 충격", "헌정 위기", "won", "KOSPI"],
        analyst_theme="Domestic political shock, abrupt uncertainty, liquidity support and market stabilization response",
        shock_type="political_shock",
        event_direction="risk_off",
        severity=5,
        visual_priority=1,
        use_in_report="main",
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="Reuters reported South Korea market stabilization measures and stock/won stress after the martial-law bid",
    ),
    "2025_us_reciprocal_tariff_shock": _normalize_event(
        event_id="2025_us_reciprocal_tariff_shock",
        start_date="2025-04-02",
        end_date="2025-04-09",
        event_span_type="window",
        region="US / Global / Korea",
        event_name="US Reciprocal Tariff Shock / Liberation Day Tariffs",
        news_keywords=["Trump tariffs", "Liberation Day", "reciprocal tariffs", "관세", "무역전쟁", "보호무역"],
        analyst_theme="Tariff shock, trade-war fear, global selloff, export-market uncertainty",
        shock_type="trade_conflict",
        event_direction="risk_off",
        severity=4,
        visual_priority=1,
        use_in_report="main",
        expected_etf_impact={"069500": "negative", "114260": "positive", "153130": "positive"},
        source_note="Reuters reported global market stress after sweeping US tariff announcements in April 2025",
    ),
    "2025_korea_presidential_election": _normalize_event(
        event_id="2025_korea_presidential_election",
        start_date="2025-06-03",
        end_date="2025-06-04",
        event_span_type="window",
        region="Korea",
        event_name="2025 Korea Presidential Election / Political Normalization Test",
        news_keywords=["Lee Jae-myung", "presidential election", "대통령 선거", "정권교체", "정치 정상화"],
        analyst_theme="Post-martial-law political transition, policy expectation reset, potential normalization of domestic risk premium",
        shock_type="political_event",
        event_direction="mixed",
        severity=2,
        visual_priority=2,
        expected_etf_impact={"069500": "neutral", "114260": "neutral", "153130": "neutral"},
        source_note="Reuters reported Lee Jae-myung's June 2025 election after the martial-law political crisis",
        caution="Treat as political transition event, not mechanically risk-on or risk-off.",
    ),
    "2025_ai_rates_geopolitical_regime": _normalize_event(
        event_id="2025_ai_rates_geopolitical_regime",
        start_date="2025-01-01",
        end_date="2025-12-31",
        event_span_type="regime",
        region="Global / Korea",
        event_name="Ongoing AI, Rates, Tariff and Geopolitical Regime",
        news_keywords=["AI", "rates", "tariffs", "geopolitics", "inflation", "semiconductor"],
        analyst_theme="AI leadership, higher-rate uncertainty, tariff shocks and geopolitical fragmentation",
        shock_type="regime_shift",
        event_direction="mixed",
        severity=2,
        visual_priority=3,
        backtest_flag=False,
        use_in_report="appendix",
        expected_etf_impact={"069500": "neutral", "114260": "neutral", "153130": "neutral"},
        source_note="broad 2025 regime; use as background only, not a discrete crisis test",
        caution="Too broad for direct crisis-window scoring. Prefer specific 2025 tariff / election events for tables.",
    ),
}


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_market_event_calendar(
    *,
    backtest_only: bool = False,
    main_only: bool = False,
    min_visual_priority: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return filtered market event calendar."""
    start = _parse_date(start_date) if start_date else None
    end = _parse_date(end_date) if end_date else None

    out: Dict[str, Dict[str, Any]] = {}
    for event_id, event in market_event_calendar.items():
        event_start = _parse_date(event["start_date"])
        event_end = _parse_date(event["end_date"])

        if backtest_only and not event.get("backtest_flag", False):
            continue
        if main_only and event.get("use_in_report") != "main":
            continue
        if min_visual_priority is not None and event.get("visual_priority", 99) > min_visual_priority:
            continue
        if start and event_end < start:
            continue
        if end and event_start > end:
            continue
        out[event_id] = event
    return out


def iter_market_events(**filters: Any) -> Iterable[Dict[str, Any]]:
    """Yield filtered events sorted by start_date."""
    events = get_market_event_calendar(**filters)
    return iter(sorted(events.values(), key=lambda x: (x["start_date"], x["end_date"], x["event_id"])))


def to_event_table(**filters: Any):
    """
    Convert events to a pandas DataFrame.

    This function imports pandas lazily so that the calendar itself can be
    imported even in lightweight environments.
    """
    import pandas as pd

    rows: List[Dict[str, Any]] = []
    for event in iter_market_events(**filters):
        row = dict(event)
        impacts = row.pop("expected_etf_impact", {})
        for ticker in ETF_TICKERS:
            row[f"expected_impact_{ticker}"] = impacts.get(ticker, "neutral")
        row["event_window_months"] = (
            row["start_date"][:7]
            if row["start_date"][:7] == row["end_date"][:7]
            else f"{row['start_date'][:7]}~{row['end_date'][:7]}"
        )
        rows.append(row)
    return pd.DataFrame(rows)


def get_backtest_event_windows():
    """Return event table limited to data-available backtest windows."""
    return to_event_table(backtest_only=True, start_date=DATA_START_DATE)


# Backward-compatible alias for older notes/scripts.
# Prefer get_market_event_calendar() in new code.
def get_shock_calendar():
    return market_event_calendar


if __name__ == "__main__":
    # Small manual check.
    df = to_event_table(start_date=DATA_START_DATE)
    print(df[["event_id", "start_date", "end_date", "event_span_type", "event_direction", "visual_priority"]].to_string(index=False))
