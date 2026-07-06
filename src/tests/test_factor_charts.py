"""
dashboard.factor_charts 순수 헬퍼 테스트 (plotly/streamlit 불필요).
실행: cd src && python3 -m pytest tests/test_factor_charts.py -q
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dashboard.factor_charts import (  # noqa: E402
    demo_bundle,
    loading_matrix,
    rolling_factor_columns,
    waterfall_values,
)


def test_demo_bundle_schema():
    d = demo_bundle()
    for k in ["loading_summary", "rolling_ts", "vif", "attr_summary", "attr_cumulative"]:
        assert k in d and len(d[k]) > 0
    assert {"strategy", "factor", "beta", "tstat", "r2"} <= set(d["loading_summary"].columns)
    assert {"effect", "sum_contribution"} <= set(d["attr_summary"].columns)


def test_loading_matrix_excludes_alpha():
    d = demo_bundle()
    m = loading_matrix(d["loading_summary"])
    assert "alpha" not in m.columns  # 팩터만
    assert set(m.index) == {"lambda_0.3", "lambda_0.1"}
    assert {"market", "bond", "vkospi"} <= set(m.columns)


def test_waterfall_values_structure():
    d = demo_bundle()
    labels, values, measure = waterfall_values(d["attr_summary"])
    assert labels == ["saa", "timing", "lambda", "cost", "total"]
    assert measure[-1] == "total" and measure[:4] == ["relative"] * 4
    # 4효과 합 ≈ total(가법 항등식)
    assert abs(sum(values[:4]) - values[4]) < 1e-8


def test_rolling_factor_columns():
    d = demo_bundle()
    cols = rolling_factor_columns(d["rolling_ts"])
    assert set(cols) == {"market", "bond", "vkospi"}


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1; print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
