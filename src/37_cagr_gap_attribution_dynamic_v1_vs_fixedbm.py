from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
37_cagr_gap_attribution_dynamic_v1_vs_fixedbm.py

목적
----
"왜 FixedBM_70_20_10을 CAGR에서 못 이겼는가"를 감으로 서술하지 않고,
월별 초과수익을 두 항으로 정확히 분해하여 정량적으로 답한다.

핵심 아이디어
-------------
월별 산술 초과수익은 다음과 같이 정확히(항등식으로) 분해된다.

    excess_t = sum_i (w_strat_i,t - w_bm_i,t) * r_i,t
             = exposure_effect_t + timing_effect_t

    w_strat_i,t = w_bar_strat_i + delta_w_i,t   (delta_w의 기간평균은 0)

    exposure_effect_t = sum_i (w_bar_strat_i - w_bm_i) * r_i,t
    timing_effect_t   = sum_i delta_w_i,t * r_i,t

- exposure_effect: "평균적으로 위험자산을 얼마나 덜/더 들고 있었는가"만으로 설명되는 부분.
  즉 상태분류나 타이밍 능력과 무관하게, 순전히 "낮은 평균 베타" 때문에 발생하는 차이.
- timing_effect: 그 평균 노출로부터 월별로 비중을 늘리고 줄인 "타이밍"이
  실제로 좋았는지 나빴는지를 보여주는 부분.

이 분해는 월별 산술수익 기준으로는 항등식이므로 residual이 0이다.
다만 이를 기간 합산(단순 합)한 값은, 실제 복리 CAGR 격차와는 정확히 같지 않다
(복리 교차항 때문). 따라서 본 스크립트는 두 값을 모두 제시하고 차이를 명시한다.

출력
----
- output/tables/main_final_cagr_gap_attribution_monthly.csv
- output/tables/main_final_cagr_gap_attribution_summary.csv
- docs/main_final_cagr_gap_attribution_note.md
"""


STRATEGY_NAME = "dynamic_v1"
STRATEGY_WEIGHT_FILE = cfg.TABLE_DIR / "main_final_portfolio_composition_dynamic_v1.csv"

FIXED_BM_WEIGHTS = {
    cfg.RISK_TICKER: 0.70,
    cfg.BOND_TICKER: 0.20,
    cfg.CASH_TICKER: 0.10,
}

IS_START = "2012-04-30"
IS_END = "2020-12-31"
OOS_START = "2021-01-31"
OOS_END = "2026-06-30"

OUTPUT_MONTHLY = cfg.TABLE_DIR / "main_final_cagr_gap_attribution_monthly.csv"
OUTPUT_SUMMARY = cfg.TABLE_DIR / "main_final_cagr_gap_attribution_summary.csv"
OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_cagr_gap_attribution_note.md"


def load_monthly_returns() -> pd.DataFrame:
    """
    hsi_data_bundle.xlsx의 monthly_return_decimal 시트를 로드한다.
    백테스트 계산 기준 시트를 그대로 사용해 다른 실험과의 정합성을 유지한다.
    """
    bundle_path = cfg.find_data_bundle()
    ret = pd.read_excel(bundle_path, sheet_name=cfg.BACKTEST_RETURN_SHEET)

    date_col = ret.columns[0]
    ret[date_col] = pd.to_datetime(ret[date_col])
    ret = ret.set_index(date_col).sort_index()
    ret = ret[cfg.TICKERS]
    # monthly_return_decimal 시트 날짜가 월초 형식으로 저장되어 있어
    # dynamic_v1 비중 파일(apply_date, 월말 형식)과 정렬되도록 월말로 통일한다.
    ret.index = ret.index + pd.offsets.MonthEnd(0)

    ret.index.name = "Date"
    return ret


def load_strategy_weights() -> pd.DataFrame:
    """
    dynamic_v1의 월별 실제 적용 비중을 로드한다.
    apply_date를 기준으로 인덱스를 맞춘다 (t월 신호가 반영되는 실제 수익월).
    """
    cfg.require_file(STRATEGY_WEIGHT_FILE, label="dynamic_v1 비중 파일")

    w = pd.read_csv(STRATEGY_WEIGHT_FILE)
    w["apply_date"] = pd.to_datetime(w["apply_date"])
    w = w.set_index("apply_date").sort_index()

    weight_cols = {f"w_{t}": t for t in cfg.TICKERS}
    w = w.rename(columns=weight_cols)[cfg.TICKERS]
    w.index.name = "Date"
    return w


def build_fixed_bm_weights(index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    FixedBM_70_20_10의 고정비중을 전략과 동일한 기간에 대해 생성한다.
    """
    data = {t: FIXED_BM_WEIGHTS[t] for t in cfg.TICKERS}
    return pd.DataFrame(data, index=index)


def compute_attribution(
    returns: pd.DataFrame,
    w_strat: pd.DataFrame,
    w_bm: pd.DataFrame,
    period_start: str,
    period_end: str,
) -> pd.DataFrame:
    """
    지정 구간에 대해 월별 exposure_effect / timing_effect를 계산한다.

    주의: w_bar_strat(전략의 시간평균 비중)는 반드시 '해당 구간 내에서'
    계산해야 한다. FULL 구간과 OOS 구간의 w_bar가 다르면 같은 전략이라도
    구간별 exposure_effect 크기가 달라지는데, 이는 의도된 설계이다.
    (예: OOS 구간에서 전략이 평균적으로 더 공격적이었다면 OOS의 w_bar가 더 커야
    OOS 구간의 exposure_effect가 그 구간의 실제 행태를 반영한다.)
    """
    idx = returns.index[
        (returns.index >= pd.Timestamp(period_start))
        & (returns.index <= pd.Timestamp(period_end))
    ]

    r = returns.loc[idx]
    ws = w_strat.loc[idx]
    wb = w_bm.loc[idx]

    w_bar_strat = ws.mean(axis=0)
    delta_w = ws.subtract(w_bar_strat, axis=1)

    exposure_diff = w_bar_strat - wb.iloc[0]

    exposure_effect_t = (r * exposure_diff).sum(axis=1)
    timing_effect_t = (r * delta_w).sum(axis=1)
    excess_t = ((ws - wb) * r).sum(axis=1)

    r_strat_t = (ws * r).sum(axis=1)
    r_bm_t = (wb * r).sum(axis=1)

    out = pd.DataFrame({
        "r_strategy": r_strat_t,
        "r_fixed_bm": r_bm_t,
        "excess_return": excess_t,
        "exposure_effect": exposure_effect_t,
        "timing_effect": timing_effect_t,
        "identity_check_residual": excess_t - (exposure_effect_t + timing_effect_t),
    })
    return out


def summarize_period(monthly: pd.DataFrame, label: str) -> dict:
    """
    한 구간에 대한 요약 통계를 만든다.
    - 산술 분해합 (exact, arithmetic 기준)
    - 실제 복리 CAGR 격차 (참고용, compounding 포함)
    - 두 값의 차이 = 복리교차효과(compounding interaction)
    """
    n_months = len(monthly)
    years = n_months / 12.0

    cum_strat = (1.0 + monthly["r_strategy"]).prod() - 1.0
    cum_bm = (1.0 + monthly["r_fixed_bm"]).prod() - 1.0

    cagr_strat = (1.0 + cum_strat) ** (1.0 / years) - 1.0
    cagr_bm = (1.0 + cum_bm) ** (1.0 / years) - 1.0
    cagr_gap = cagr_strat - cagr_bm

    sum_excess_arith = monthly["excess_return"].sum()
    sum_exposure = monthly["exposure_effect"].sum()
    sum_timing = monthly["timing_effect"].sum()

    exposure_share = sum_exposure / sum_excess_arith if sum_excess_arith != 0 else np.nan
    timing_share = sum_timing / sum_excess_arith if sum_excess_arith != 0 else np.nan

    compounding_interaction = (cum_strat - cum_bm) - sum_excess_arith

    return {
        "period": label,
        "n_months": n_months,
        "cagr_strategy_pct": cagr_strat * 100,
        "cagr_fixed_bm_pct": cagr_bm * 100,
        "cagr_gap_pct": cagr_gap * 100,
        "cum_return_gap_pct": (cum_strat - cum_bm) * 100,
        "sum_monthly_excess_arith_pct": sum_excess_arith * 100,
        "sum_exposure_effect_pct": sum_exposure * 100,
        "sum_timing_effect_pct": sum_timing * 100,
        "exposure_effect_share_of_excess": exposure_share,
        "timing_effect_share_of_excess": timing_share,
        "compounding_interaction_pct": compounding_interaction * 100,
        "max_identity_residual": monthly["identity_check_residual"].abs().max(),
    }


def build_note(summary: pd.DataFrame) -> str:
    """
    docs/main_final_cagr_gap_attribution_note.md 초안을 생성한다.
    실제 수치는 summary 표에서 그대로 가져오며, 문장은 초안이므로
    보고서에 넣기 전에 검토가 필요하다.
    """
    lines = []
    lines.append("# CAGR 격차 원인 분해 노트 (dynamic_v1 vs FixedBM_70_20_10)")
    lines.append("")
    lines.append("## 방법론")
    lines.append("")
    lines.append(
        "월별 산술 초과수익을 exposure_effect(시간평균 비중 차이로 설명되는 부분)와 "
        "timing_effect(평균 대비 월별 비중 편차로 설명되는 부분)로 정확히 분해하였다. "
        "이 분해는 산술수익 기준 항등식이므로 residual은 0에 수렴한다 "
        f"(최대 잔차: {summary['max_identity_residual'].max():.2e}). "
        "다만 이를 기간 합산한 값은 복리 CAGR 격차와 정확히 일치하지 않으며, "
        "그 차이는 compounding_interaction으로 별도 표기하였다."
    )
    lines.append("")
    lines.append("## 구간별 결과")
    lines.append("")
    lines.append("| 구간 | CAGR 격차(%p) | Exposure Effect(%p) | Timing Effect(%p) | Exposure 비중 | Timing 비중 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['period']} | {row['cagr_gap_pct']:.2f} | "
            f"{row['sum_exposure_effect_pct']:.2f} | {row['sum_timing_effect_pct']:.2f} | "
            f"{row['exposure_effect_share_of_excess']:.1%} | {row['timing_effect_share_of_excess']:.1%} |"
        )
    lines.append("")
    lines.append("## 해석 (초안 — 실제 수치 확인 후 다듬을 것)")
    lines.append("")
    lines.append(
        "[TODO] Exposure effect 비중이 지배적이면: CAGR 격차는 주로 "
        "'평균적으로 위험자산을 덜 들고 있었기 때문'이며, 이는 방어형 설계가 "
        "의도대로 작동한 결과로 해석한다. Market timing 실패가 주원인이 아니다."
    )
    lines.append("")
    lines.append(
        "[TODO] Timing effect가 음(-)의 방향으로 상당 부분을 차지하면: "
        "상태 진입/이탈 타이밍(특히 회복 국면 재진입 지연)이 격차를 추가로 키웠다는 뜻이며, "
        "12번 방향별 λ(비대칭 λ) 실험의 필요성을 정량적으로 뒷받침하는 근거가 된다."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("37_cagr_gap_attribution_dynamic_v1_vs_fixedbm.py 실행 시작")
    print("=" * 80)

    print("[1] 월간 수익률(decimal) 로드")
    returns = load_monthly_returns()
    print(f"    OK: {returns.index.min().date()} ~ {returns.index.max().date()}, {len(returns)}개월")

    print(f"[2] {STRATEGY_NAME} 비중 로드")
    w_strat = load_strategy_weights()
    print(f"    OK: {len(w_strat)}개월")

    print("[3] 공통 구간으로 정렬")
    common_idx = returns.index.intersection(w_strat.index)
    returns = returns.loc[common_idx]
    w_strat = w_strat.loc[common_idx]
    w_bm = build_fixed_bm_weights(common_idx)
    print(f"    OK: 공통 {len(common_idx)}개월 ({common_idx.min().date()} ~ {common_idx.max().date()})")

    periods = [
        ("FULL", common_idx.min().strftime("%Y-%m-%d"), common_idx.max().strftime("%Y-%m-%d")),
        ("IS", IS_START, IS_END),
        ("OOS", OOS_START, OOS_END),
    ]

    print("[4] 구간별 분해 계산")
    summary_rows = []
    monthly_all = []

    for label, start, end in periods:
        monthly = compute_attribution(returns, w_strat, w_bm, start, end)
        monthly = monthly.copy()
        monthly["period"] = label
        monthly_all.append(monthly)

        summary_rows.append(summarize_period(monthly, label))
        print(f"    {label}: {len(monthly)}개월 처리 완료")

    monthly_out = pd.concat(monthly_all)
    monthly_out.index.name = "Date"
    summary_out = pd.DataFrame(summary_rows)

    print("[5] 저장")
    monthly_out.to_csv(OUTPUT_MONTHLY, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_MONTHLY}")

    summary_out.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_SUMMARY}")

    note = build_note(summary_out)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[요약]")
    print(summary_out.to_string(index=False))

    print("=" * 80)
    print("37_cagr_gap_attribution_dynamic_v1_vs_fixedbm.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()