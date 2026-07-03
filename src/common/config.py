"""
실험 공통 상수 (ETF 유니버스/비중 컬럼/벤치마크/초기자본).
"""

# 예비 유니버스 3종 (069500: 위험자산, 114260/153130: 채권형/단기채권)
ASSETS = ["069500", "114260", "153130"]

BENCHMARK_TICKER = "069500"
PRIMARY_RISK_TICKER = "069500"

WEIGHT_COLS = {asset: f"{asset}_weight" for asset in ASSETS}

INITIAL_CAPITAL = 1.0
