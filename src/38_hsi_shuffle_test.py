from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg



STRATEGY_WEIGHT_FILE = cfg.TABLE_DIR / "main_final_portfolio_composition_dynamic_v1.csv"

BLOCK_SIZE = 4          # 블록 길이(개월). 상태 지속성을 어느 정도 보존하기 위함.
N_SIMULATIONS = 1000
RANDOM_SEED = 42

IS_START = "2012-04-30"
IS_END = "2020-12-31"
OOS_START = "2021-01-31"
OOS_END = "2026-06-30"

OUTPUT_NULL_DIST = cfg.TABLE_DIR / "main_final_hsi_shuffle_null_distribution.csv"
OUTPUT_PERCENTILE = cfg.TABLE_DIR / "main_final_hsi_shuffle_percentile_summary.csv"
OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_hsi_shuffle_placebo_test_note.md"


def load_monthly_returns() -> pd.DataFrame:
    bundle_path = cfg.find_data_bundle()
    ret = pd.read_excel(bundle_path, sheet_name=cfg.BACKTEST_RETURN_SHEET)
    date_col = ret.columns[0]
    ret[date_col] = pd.to_datetime(ret[date_col])
    ret = ret.set_index(date_col).sort_index()
    ret = ret[cfg.TICKERS]
    ret.index = ret.index + pd.offsets.MonthEnd(0)
    ret.index.name = "Date"
    return ret


def load_dynamic_v1_actuals() -> pd.DataFrame:
    cfg.require_file(STRATEGY_WEIGHT_FILE, label="dynamic_v1 비중 파일")
    df = pd.read_csv(STRATEGY_WEIGHT_FILE)
    df["apply_date"] = pd.to_datetime(df["apply_date"])
    df = df.set_index("apply_date").sort_index()
    df.index.name = "Date"
    return df


def state_to_target_weight(state: str) -> np.ndarray:
    """
    HSI 상태를 목표비중 벡터(순서: RISK, BOND, CASH)로 변환한다.
    insufficient_data는 여기서 처리하지 않고 상위 함수에서 '이전 비중 유지'로 별도 처리한다.
    """
    rule = cfg.FINAL_BASELINE_ALLOCATION_RULES[state]
    return np.array([
        rule[cfg.RISK_TICKER],
        rule[cfg.BOND_TICKER],
        rule[cfg.CASH_TICKER],
    ])


def reconstruct_weights(
    states: list[str],
    lambdas: np.ndarray,
    initial_weight: np.ndarray,
) -> np.ndarray:
    """
    상태 시퀀스 + λ 시퀀스로부터 실제 비중 경로를 재귀적으로 계산한다.
    """
    n = len(states)
    weights = np.zeros((n, 3))
    prev = initial_weight.copy()

    for t in range(n):
        state = states[t]
        lam = lambdas[t]

        if state == "insufficient_data":
            target = prev.copy()
        else:
            target = state_to_target_weight(state)

        w_t = prev + lam * (target - prev)
        weights[t] = w_t
        prev = w_t

    return weights


def compute_performance(weights: np.ndarray, returns: np.ndarray) -> dict:
    """
    주어진 월별 비중·수익률 경로로부터 CAGR, MDD, Sharpe, Calmar를 계산한다.
    """
    port_ret = (weights * returns).sum(axis=1)
    n_months = len(port_ret)
    years = n_months / 12.0

    cum = np.cumprod(1.0 + port_ret)
    cagr = cum[-1] ** (1.0 / years) - 1.0

    running_max = np.maximum.accumulate(cum)
    drawdown = cum / running_max - 1.0
    mdd = drawdown.min()

    ann_vol = port_ret.std(ddof=1) * np.sqrt(12)
    sharpe = (port_ret.mean() * 12) / ann_vol if ann_vol > 0 else np.nan
    calmar = cagr / abs(mdd) if mdd != 0 else np.nan

    return {
        "cagr": cagr * 100,
        "mdd": mdd * 100,
        "sharpe": sharpe,
        "calmar": calmar,
    }


def block_shuffle_states(states: list[str], block_size: int, rng: np.random.Generator) -> list[str]:
    """
    상태 시퀀스를 block_size 단위 블록으로 나눈 뒤, 블록 순서를 무작위로 섞는다.
    마지막 블록은 길이가 짧을 수 있다.
    """
    n = len(states)
    blocks = [states[i:i + block_size] for i in range(0, n, block_size)]
    order = rng.permutation(len(blocks))
    shuffled = []
    for idx in order:
        shuffled.extend(blocks[idx])
    return shuffled


def sanity_check_reconstruction(actual: pd.DataFrame) -> None:
    """
    상태->목표비중 매핑 가정이 맞는지, 원본 상태 순서로 재구성한 비중이
    실제 저장된 dynamic_v1 비중과 일치하는지 확인한다.
    """
    states = actual["hsi_state"].tolist()
    lambdas = actual["lambda_used"].to_numpy()

    initial = actual[[f"w_{t}" for t in cfg.TICKERS]].to_numpy()[0]
    # 첫 행은 재구성 대상에서 제외하고, 그 값을 시작점으로 사용한다.
    reconstructed = reconstruct_weights(states[1:], lambdas[1:], initial)

    actual_rest = actual[[f"w_{t}" for t in cfg.TICKERS]].to_numpy()[1:]
    max_diff = np.abs(reconstructed - actual_rest).max()

    print(f"    [sanity check] 원본 재구성 vs 실제 저장값 최대 오차: {max_diff:.6f}")
    if max_diff > 1e-3:
        print("    경고: 오차가 큽니다. FINAL_BASELINE_ALLOCATION_RULES가 dynamic_v1이 "
              "실제로 사용한 상태별 목표비중표와 다를 수 있습니다. 결과 해석에 주의하세요.")
    else:
        print("    OK: 목표비중 매핑 가정이 실제 데이터와 잘 맞습니다.")


def run_simulations(
    actual: pd.DataFrame,
    returns: pd.DataFrame,
) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)

    states = actual["hsi_state"].tolist()
    lambdas = actual["lambda_used"].to_numpy()
    dates = actual.index
    ret_arr = returns.loc[dates, cfg.TICKERS].to_numpy()
    initial = actual[[f"w_{t}" for t in cfg.TICKERS]].to_numpy()[0]

    rows = []

    for sim in range(N_SIMULATIONS):
        shuffled_states = block_shuffle_states(states, BLOCK_SIZE, rng)
        sim_weights = reconstruct_weights(shuffled_states, lambdas, initial)

        for label, start, end in [
            ("FULL", dates.min(), dates.max()),
            ("IS", pd.Timestamp(IS_START), pd.Timestamp(IS_END)),
            ("OOS", pd.Timestamp(OOS_START), pd.Timestamp(OOS_END)),
        ]:
            mask = (dates >= start) & (dates <= end)
            perf = compute_performance(sim_weights[mask], ret_arr[mask])
            perf["sim_id"] = sim
            perf["period"] = label
            rows.append(perf)

    return pd.DataFrame(rows)


def compute_actual_performance(actual: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    dates = actual.index
    ret_arr = returns.loc[dates, cfg.TICKERS].to_numpy()
    w_arr = actual[[f"w_{t}" for t in cfg.TICKERS]].to_numpy()

    rows = []
    for label, start, end in [
        ("FULL", dates.min(), dates.max()),
        ("IS", pd.Timestamp(IS_START), pd.Timestamp(IS_END)),
        ("OOS", pd.Timestamp(OOS_START), pd.Timestamp(OOS_END)),
    ]:
        mask = (dates >= start) & (dates <= end)
        perf = compute_performance(w_arr[mask], ret_arr[mask])
        perf["period"] = label
        rows.append(perf)

    return pd.DataFrame(rows)


def summarize_percentiles(null_dist: pd.DataFrame, actual_perf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metrics = ["cagr", "mdd", "sharpe", "calmar"]

    for period in ["FULL", "IS", "OOS"]:
        null_p = null_dist[null_dist["period"] == period]
        actual_p = actual_perf[actual_perf["period"] == period].iloc[0]

        row = {"period": period}
        for m in metrics:
            null_values = null_p[m].dropna().to_numpy()
            actual_value = actual_p[m]
            percentile = (null_values < actual_value).mean() * 100

            row[f"actual_{m}"] = actual_value
            row[f"null_mean_{m}"] = null_values.mean()
            row[f"null_std_{m}"] = null_values.std(ddof=1)
            row[f"actual_{m}_percentile"] = percentile
        rows.append(row)

    return pd.DataFrame(rows)


def build_note(percentile_summary: pd.DataFrame) -> str:
    lines = []
    lines.append("# HSI 목표비중 Shuffle Placebo Test 노트")
    lines.append("")
    lines.append("## 방법론")
    lines.append("")
    lines.append(
        f"λ 실행규칙(변동성·drawdown 기반 조절)은 dynamic_v1의 실현값을 그대로 고정하고, "
        f"HSI 목표비중(상태 시퀀스)만 {BLOCK_SIZE}개월 블록 단위로 {N_SIMULATIONS}회 무작위 셔플하여 "
        "대조군 포트폴리오를 생성하였다. 각 대조군의 CAGR, MDD, Sharpe, Calmar를 계산하여 "
        "귀무분포를 구성하고, 실제 dynamic_v1의 성과가 이 분포에서 위치하는 백분위를 확인하였다."
    )
    lines.append("")
    lines.append("## 구간별 결과")
    lines.append("")
    lines.append("| 구간 | 지표 | 실제값 | 귀무분포 평균 | 귀무분포 표준편차 | 실제값 백분위 |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for _, row in percentile_summary.iterrows():
        for m, label in [("cagr", "CAGR(%)"), ("mdd", "MDD(%)"), ("sharpe", "Sharpe"), ("calmar", "Calmar")]:
            lines.append(
                f"| {row['period']} | {label} | {row[f'actual_{m}']:.3f} | "
                f"{row[f'null_mean_{m}']:.3f} | {row[f'null_std_{m}']:.3f} | "
                f"{row[f'actual_{m}_percentile']:.1f}%ile |"
            )
    lines.append("")
    lines.append("## 해석 (초안 — 실제 수치 확인 후 다듬을 것)")
    lines.append("")
    lines.append(
        "[TODO] 백분위가 90%ile 이상(특히 Calmar, MDD 기준)이면: 무작위로 섞은 HSI 방향보다 "
        "실제 HSI 방향이 뚜렷하게 우수하다는 뜻이며, HSI가 독립적으로 유효한 정보를 제공했다는 "
        "증거로 해석할 수 있다."
    )
    lines.append("")
    lines.append(
        "[TODO] 백분위가 50%ile 근처면: 성과 대부분이 변동성·drawdown 기반 λ 조절 메커니즘만으로도 "
        "재현 가능하다는 뜻이며, HSI 방향 정보의 독립 기여는 제한적으로 해석해야 한다."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("38_hsi_shuffle_test.py 실행 시작")
    print("=" * 80)

    print("[1] 데이터 로드")
    returns = load_monthly_returns()
    actual = load_dynamic_v1_actuals()
    common_idx = returns.index.intersection(actual.index)
    returns = returns.loc[common_idx]
    actual = actual.loc[common_idx]
    print(f"    OK: 공통 {len(common_idx)}개월")

    print("[2] 목표비중 매핑 sanity check")
    sanity_check_reconstruction(actual)

    print(f"[3] Monte Carlo 시뮬레이션 실행 ({N_SIMULATIONS}회, block_size={BLOCK_SIZE})")
    null_dist = run_simulations(actual, returns)
    print(f"    OK: {len(null_dist)}개 행 생성")

    print("[4] 실제 dynamic_v1 성과 계산")
    actual_perf = compute_actual_performance(actual, returns)
    print(actual_perf.to_string(index=False))

    print("[5] 백분위 요약")
    percentile_summary = summarize_percentiles(null_dist, actual_perf)
    print(percentile_summary.to_string(index=False))

    print("[6] 저장")
    null_dist.to_csv(OUTPUT_NULL_DIST, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_NULL_DIST}")

    percentile_summary.to_csv(OUTPUT_PERCENTILE, index=False, encoding="utf-8-sig")
    print(f"    저장: {OUTPUT_PERCENTILE}")

    note = build_note(percentile_summary)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("=" * 80)
    print("38_hsi_shuffle_test.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()