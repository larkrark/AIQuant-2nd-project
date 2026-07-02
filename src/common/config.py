"""
실험 공통 상수.

여러 스크립트가 각자 하드코딩하던 ETF 유니버스, 비중 컬럼명, 벤치마크,
초기 자본을 한곳에서 관리한다.
"""

# 예비 유니버스 3종 (069500: 위험자산 기준, 114260/153130: 채권형)
ASSETS = ["069500", "114260", "153130"]

# 상대강도 기준 및 위험자산 대표 티커
BENCHMARK_TICKER = "069500"
PRIMARY_RISK_TICKER = "069500"

# 자산별 비중 컬럼명 매핑
WEIGHT_COLS = {asset: f"{asset}_weight" for asset in ASSETS}

# 백테스트 초기 자본
INITIAL_CAPITAL = 1.0
