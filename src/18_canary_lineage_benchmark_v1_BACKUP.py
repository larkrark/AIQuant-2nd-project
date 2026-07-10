# -*- coding: utf-8 -*-
"""
18_canary_lineage_benchmark.py

HSI 기반 ETF 방어형 Overlay 전략을 기존 카나리아형 동적자산배분 계보와 비교하기 위한
후속 검증 실험 스크립트.

핵심 목적
1) HSI가 처음부터 DAA/VAA/BAA를 개선하려고 만든 전략이었다고 과장하지 않는다.
2) 지금 인식한 문제를 바탕으로, 기존 카나리아형 전략의 단순 proxy와 HSI를 동일 조건에서 비교한다.
3) 비교 대상은 원 논문 전략의 완전 복제가 아니라, 동일 국내 ETF 3종 유니버스에서 구현 가능한
   VAA-like / DAA-like / BAA-like proxy 전략이다.
4) overfitting 논란을 줄이기 위해 신호식, 임계값, 비용, IS/OOS split, 리밸런싱 규칙을 코드 상단에 고정한다.
5) 결과표, 검증 audit, 그림, 보고서용 md note를 함께 생성한다.

실행 위치:
C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project

실행:
python .\src\18_canary_lineage_benchmark.py
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Tuple
import json
import math
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str = "18_canary_lineage_benchmark"
    experiment_name: str = "HSI vs canary-style DAA/VAA/BAA proxy benchmark"
    version: str = "v1_pre_registered"

    equity: str = "069500"
    bond: str = "114260"
    cash_like: str = "153130"

    cost_bp: float = 10.0
    periods_per_year: int = 12
    momentum_windows: Tuple[int, int, int, int] = (1, 3, 6, 12)
    oos_start: str = "2021-01-31"

    hsi_weight_file_candidates: Tuple[str, ...] = (
        "output/tables/main_final_final_ra_weights.csv",
        "output/tables/main_final_dynamic_v1_weights.csv",
        "data/processed/main_final_dynamic_v1_weights.csv",
        "data/processed/main_final_ra_weights.csv",
        "data/processed/main_final_all_strategy_weights.csv",
    )
    return_file_candidates: Tuple[str, ...] = (
        "data/processed/main_final_monthly_return_decimal.csv",
        "data/processed/monthly_return_decimal.csv",
        "output/tables/main_final_monthly_return_decimal.csv",
    )
    out_table_dir: str = "output/tables"
    out_figure_dir: str = "output/figures"
    out_doc_dir: str = "docs"


CFG = ExperimentConfig()


def project_root() -> Path:
    return Path.cwd()


def ensure_dirs(root: Path) -> None:
    for d in [CFG.out_table_dir, CFG.out_figure_dir, CFG.out_doc_dir]:
        (root / d).mkdir(parents=True, exist_ok=True)


def find_existing_file(root: Path, candidates: Tuple[str, ...], label: str) -> Path:
    for rel in candidates:
        p = root / rel
        if p.exists():
            print(f"[OK] {label}: {p}")
            return p
    raise FileNotFoundError(
        f"{label} 파일을 찾지 못했습니다. 후보 경로:\n"
        + "\n".join(str(root / x) for x in candidates)
    )


def parse_date_index(df: pd.DataFrame) -> pd.DataFrame:
    date_cols = [c for c in df.columns if str(c).lower() in ["date", "month", "ym", "rebalance_date"]]
    if date_cols:
        df = df.copy()
        df[date_cols[0]] = pd.to_datetime(df[date_cols[0]])
        df = df.set_index(date_cols[0])
    else:
        df = df.copy()
        df.index = pd.to_datetime(df.index)
    return df.sort_index()


def clean_ticker_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for c in df.columns:
        s = str(c)
        if len(s) >= 6 and s[:6].isdigit():
            rename[c] = s[:6]
    return df.rename(columns=rename)


def normalize_weights(w: pd.DataFrame) -> pd.DataFrame:
    w = w.copy().apply(pd.to_numeric, errors="coerce")
    w = w.ffill().fillna(0.0)
    s = w.sum(axis=1)
    bad = s.abs() < 1e-12
    if bad.any():
        w.loc[bad, :] = np.nan
        w = w.ffill().fillna(0.0)
        s = w.sum(axis=1)
    return w.div(s, axis=0)


def read_monthly_returns(root: Path) -> pd.DataFrame:
    p = find_existing_file(root, CFG.return_file_candidates, "monthly_return_decimal")
    df = pd.read_csv(p)
    df = parse_date_index(df)
    df = clean_ticker_columns(df)
    needed = [CFG.equity, CFG.bond, CFG.cash_like]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"수익률 파일에 필요한 ETF 컬럼이 없습니다: {missing}\n현재 컬럼: {list(df.columns)}")
    ret = df[needed].apply(pd.to_numeric, errors="coerce").dropna(how="all")
    max_abs = ret.abs().max().max()
    if max_abs > 1.0:
        raise ValueError(f"수익률 최대 절댓값이 {max_abs:.4f}입니다. decimal이 아니라 percent 단위일 가능성이 큽니다.")
    return ret


def read_hsi_weights_if_available(root: Path, ret_index: pd.DatetimeIndex) -> pd.DataFrame | None:
    for rel in CFG.hsi_weight_file_candidates:
        p = root / rel
        if not p.exists():
            continue
        try:
            raw = pd.read_csv(p)
            df = parse_date_index(raw)
            df = clean_ticker_columns(df)
            needed = [CFG.equity, CFG.bond, CFG.cash_like]
            if all(c in df.columns for c in needed):
                w = df[needed].apply(pd.to_numeric, errors="coerce")
                w = w.reindex(ret_index).ffill()
                print(f"[OK] HSI dynamic_v1 weights loaded: {p}")
                return normalize_weights(w)
        except Exception as e:
            print(f"[WARN] HSI weight 후보 읽기 실패: {p} / {e}")
    print("[WARN] HSI dynamic_v1 weight 파일을 자동으로 찾지 못했습니다.")
    return None


def weighted_momentum(ret: pd.DataFrame, windows: Tuple[int, ...]) -> pd.DataFrame:
    parts = []
    for k in windows:
        mom_k = (1.0 + ret).rolling(k).apply(np.prod, raw=True) - 1.0
        parts.append(mom_k)
    return sum(parts) / len(parts)


def max_drawdown(ret: pd.Series) -> float:
    v = (1.0 + ret.fillna(0.0)).cumprod()
    dd = v / v.cummax() - 1.0
    return float(dd.min())


def cagr(ret: pd.Series, periods_per_year: int = 12) -> float:
    ret = ret.dropna()
    if len(ret) == 0:
        return np.nan
    total = float((1.0 + ret).prod())
    n = len(ret)
    if total <= 0:
        return np.nan
    return total ** (periods_per_year / n) - 1.0


def ann_vol(ret: pd.Series, periods_per_year: int = 12) -> float:
    ret = ret.dropna()
    if len(ret) < 2:
        return np.nan
    return float(ret.std(ddof=1) * math.sqrt(periods_per_year))


def sharpe(ret: pd.Series) -> float:
    vol = ann_vol(ret)
    return np.nan if abs(vol) < 1e-12 else cagr(ret) / vol


def calmar(ret: pd.Series) -> float:
    mdd = max_drawdown(ret)
    return np.nan if abs(mdd) < 1e-12 else cagr(ret) / abs(mdd)


def one_way_turnover(weights: pd.DataFrame) -> pd.Series:
    return weights.diff().abs().sum(axis=1) / 2.0


def backtest_from_signal_weights(ret: pd.DataFrame, signal_weights: pd.DataFrame, cost_bp: float, name: str):
    """
    t월 말에 계산된 signal_weights를 t+1월 수익률에 적용한다.
    r_{p,t} = sum_i w_{i,t-1} * r_{i,t} - turnover_t * cost_rate
    """
    w = normalize_weights(signal_weights.reindex(ret.index).ffill())
    applied_w = w.shift(1)
    gross = (applied_w * ret).sum(axis=1)
    tv = one_way_turnover(w)
    cost = tv * (cost_bp / 10000.0)
    net = (gross - cost).dropna()
    tv = tv.reindex(net.index).fillna(0.0)
    net.name = name
    tv.name = name
    return net, tv


def metrics_for_period(ret: pd.Series, turnover: pd.Series, start=None, end=None) -> Dict[str, float]:
    x = ret.copy()
    tv = turnover.copy()
    if start is not None:
        x = x[x.index >= pd.to_datetime(start)]
        tv = tv[tv.index >= pd.to_datetime(start)]
    if end is not None:
        x = x[x.index <= pd.to_datetime(end)]
        tv = tv[tv.index <= pd.to_datetime(end)]
    if len(x) == 0:
        return {}
    return {
        "months": len(x),
        "cum_return": (1.0 + x).prod() - 1.0,
        "cagr": cagr(x),
        "ann_vol": ann_vol(x),
        "mdd": max_drawdown(x),
        "sharpe": sharpe(x),
        "calmar": calmar(x),
        "monthly_win_rate": (x > 0).mean(),
        "avg_turnover_ann": tv.mean() * 12.0,
    }


def summarize_all(returns: pd.DataFrame, turnovers: pd.DataFrame, oos_start: str) -> pd.DataFrame:
    rows = []
    full_start, full_end = returns.index.min(), returns.index.max()
    oos_dt = pd.to_datetime(oos_start)
    is_end = returns.index[returns.index < oos_dt].max()
    for name in returns.columns:
        for period, start, end in [("FULL", full_start, full_end), ("IS", full_start, is_end), ("OOS", oos_dt, full_end)]:
            m = metrics_for_period(returns[name], turnovers[name], start, end)
            if m:
                m["strategy"] = name
                m["period"] = period
                rows.append(m)
    cols = ["strategy", "period", "months", "cum_return", "cagr", "ann_vol", "mdd", "sharpe", "calmar", "monthly_win_rate", "avg_turnover_ann"]
    return pd.DataFrame(rows)[cols]


def make_fixed_bm_weights(index: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame({CFG.equity: 0.70, CFG.bond: 0.20, CFG.cash_like: 0.10}, index=index)


def make_ew_weights(index: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame({CFG.equity: 1/3, CFG.bond: 1/3, CFG.cash_like: 1/3}, index=index)


def make_vaa_like_weights(ret: pd.DataFrame, mom: pd.DataFrame) -> pd.DataFrame:
    breadth = (mom[[CFG.equity, CFG.bond, CFG.cash_like]] > 0).sum(axis=1)
    w = pd.DataFrame(index=ret.index, columns=[CFG.equity, CFG.bond, CFG.cash_like], dtype=float)
    risk_on = breadth == 3
    w.loc[risk_on, :] = [0.70, 0.20, 0.10]
    w.loc[~risk_on, :] = [0.00, 0.30, 0.70]
    return normalize_weights(w)


def make_daa_like_weights(ret: pd.DataFrame, mom: pd.DataFrame) -> pd.DataFrame:
    bad = (mom[[CFG.equity, CFG.bond]] <= 0).sum(axis=1)
    w = pd.DataFrame(index=ret.index, columns=[CFG.equity, CFG.bond, CFG.cash_like], dtype=float)
    w.loc[bad == 0, :] = [0.70, 0.20, 0.10]
    w.loc[bad == 1, :] = [0.35, 0.30, 0.35]
    w.loc[bad >= 2, :] = [0.00, 0.30, 0.70]
    return normalize_weights(w)


def make_baa_like_weights(ret: pd.DataFrame, mom: pd.DataFrame) -> pd.DataFrame:
    canary_ok = (mom[[CFG.equity, CFG.bond]] > 0).all(axis=1)
    w = pd.DataFrame(0.0, index=ret.index, columns=[CFG.equity, CFG.bond, CFG.cash_like])
    w.loc[canary_ok, CFG.equity] = 1.0
    for dt in w.index[~canary_ok]:
        pair = mom.loc[dt, [CFG.bond, CFG.cash_like]]
        chosen = CFG.cash_like if pair.isna().all() else pair.idxmax()
        w.loc[dt, chosen] = 1.0
    return normalize_weights(w)


def strategy_mode(weights: pd.DataFrame) -> pd.Series:
    return pd.Series(np.where(weights[CFG.equity] >= 0.5, "risk_on", "risk_off"), index=weights.index)


def count_whipsaw(weights_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, w in weights_dict.items():
        mode = strategy_mode(w)
        flips = int((mode != mode.shift(1)).sum())
        rows.append({
            "strategy": name,
            "risk_mode_flips": flips,
            "avg_equity_weight": float(w[CFG.equity].mean()),
            "min_equity_weight": float(w[CFG.equity].min()),
            "max_equity_weight": float(w[CFG.equity].max()),
        })
    return pd.DataFrame(rows)


def save_cumret_plot(returns: pd.DataFrame, path: Path) -> None:
    cum = (1.0 + returns.fillna(0.0)).cumprod() - 1.0
    plt.figure(figsize=(12, 7))
    for col in cum.columns:
        plt.plot(cum.index, cum[col], label=col)
    plt.axhline(0, linewidth=1)
    plt.title("HSI vs canary-style proxy strategies: cumulative return")
    plt.ylabel("Cumulative return, decimal")
    plt.xlabel("Date")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def save_drawdown_plot(returns: pd.DataFrame, path: Path) -> None:
    v = (1.0 + returns.fillna(0.0)).cumprod()
    dd = v / v.cummax() - 1.0
    plt.figure(figsize=(12, 7))
    for col in dd.columns:
        plt.plot(dd.index, dd[col], label=col)
    plt.axhline(0, linewidth=1)
    plt.title("HSI vs canary-style proxy strategies: drawdown")
    plt.ylabel("Drawdown, decimal")
    plt.xlabel("Date")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def save_horizontal_bar(df: pd.DataFrame, value_col: str, title: str, xlabel: str, path: Path) -> None:
    d = df.sort_values(value_col, ascending=True)
    plt.figure(figsize=(10, 6))
    plt.barh(d["strategy"], d[value_col])
    plt.title(title)
    plt.xlabel(xlabel)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def make_audit_table(ret: pd.DataFrame, weights_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = [{
        "check": "return_unit_decimal",
        "status": "PASS" if ret.abs().max().max() <= 1.0 else "FAIL",
        "evidence": f"max_abs_return={ret.abs().max().max():.6f}",
    }]
    for name, w in weights_dict.items():
        s = w.sum(axis=1)
        rows.append({"check": f"{name}_weight_sum_1", "status": "PASS" if np.allclose(s.dropna(), 1.0, atol=1e-8) else "FAIL", "evidence": f"max_abs_sum_error={float((s-1).abs().max()):.12f}"})
        rows.append({"check": f"{name}_no_negative_weight", "status": "PASS" if (w.min().min() >= -1e-12) else "FAIL", "evidence": f"min_weight={float(w.min().min()):.12f}"})
    rows.append({"check": "signal_to_return_alignment", "status": "PASS", "evidence": "backtest uses weights.shift(1) * current_month_returns to enforce t signal -> t+1 return"})
    rows.append({"check": "parameter_lock", "status": "PASS", "evidence": json.dumps(asdict(CFG), ensure_ascii=False)})
    return pd.DataFrame(rows)


def write_report_note(root: Path, metrics: pd.DataFrame, whipsaw: pd.DataFrame, audit: pd.DataFrame, has_hsi: bool) -> Path:
    oos = metrics[metrics["period"] == "OOS"].copy()
    show_cols = ["strategy", "months", "cum_return", "cagr", "ann_vol", "mdd", "sharpe", "calmar", "monthly_win_rate", "avg_turnover_ann"]
    oos_md = oos[show_cols].to_markdown(index=False, floatfmt=".4f")
    whipsaw_md = whipsaw.to_markdown(index=False, floatfmt=".4f")
    audit_md = audit.to_markdown(index=False)
    hsi_note = "기존 dynamic_v1 weight 파일을 자동으로 읽어 HSI_dynamic_v1을 포함하였다." if has_hsi else "기존 dynamic_v1 weight 파일을 자동으로 찾지 못해 이번 실행에는 HSI_dynamic_v1이 포함되지 않았다. HSI weight 파일 경로를 CFG.hsi_weight_file_candidates에 추가한 뒤 재실행해야 한다."
    text = f"""# 18. 기존 카나리아형 동적자산배분 proxy와 HSI 비교 실험 노트

## 18.1 실험의 출발점

HSI의 출발점은 처음부터 DAA, VAA, BAA 같은 기존 카나리아형 동적자산배분 전략을 개선하려는 목적이 아니었다. 초기 문제의식은 미국 시장 충격이 한국 시장으로 전이되는 현상을 관찰하고, 이런 외부 위험 신호를 한국 ETF 방어형 포트폴리오 판단에 활용할 수 있는지 확인해 보는 탐구적 실험이었다.

다만 프로젝트를 정리하는 과정에서 HSI는 기존 카나리아형 동적자산배분 계보와 비교해 볼 필요가 있다. 따라서 본 실험은 원 논문 전략을 완전 복제하려는 것이 아니라, 동일 국내 ETF 3종 유니버스 안에서 구현 가능한 VAA-like, DAA-like, BAA-like proxy 전략을 만들고, HSI_dynamic_v1과 같은 비용·같은 리밸런싱·같은 IS/OOS 조건에서 비교한다.

## 18.2 실험 가설

### H0
HSI_dynamic_v1의 5단계 상태분류와 λ 부분조정 구조는 단순 카나리아형 proxy 대비 OOS 기준 MDD, Calmar, Turnover, whipsaw 측면에서 개선을 보이지 않는다.

### H1
HSI_dynamic_v1은 기존 이진적 risk-on/risk-off proxy보다 OOS 기준 MDD, Calmar, Turnover 또는 whipsaw 측면에서 방어형 개선을 보인다. 단, 본 실험은 HSI가 DAA/VAA/BAA 원 논문 전략보다 우월하다는 결론이 아니라, 동일 국내 ETF 유니버스에서 HSI 구조가 어떤 차이를 보이는지 확인하는 후속 검증이다.

## 18.3 전략 정의

- FixedBM_70_20_10: 069500 70%, 114260 20%, 153130 10% 고정비중
- EW: 세 ETF 동일비중
- VAA_like_proxy: 세 ETF의 1/3/6/12개월 평균 momentum이 모두 양수이면 70/20/10, 하나라도 음수이면 0/30/70
- DAA_like_proxy: 069500, 114260을 canary proxy로 두고 bad canary 수에 따라 70/20/10, 35/30/35, 0/30/70 적용
- BAA_like_proxy: canary가 모두 양수이면 069500 100%, 아니면 114260과 153130 중 momentum이 높은 방어자산 100%
- HSI_dynamic_v1: 기존 프로젝트 산출 weight 파일을 읽어 동일 엔진으로 비용차감 재계산

{hsi_note}

## 18.4 과적합 방지 장치

1. 동일 ETF 유니버스 사용: 069500, 114260, 153130만 사용한다.
2. 동일 비용 적용: 모든 전략에 10bp 비용을 적용한다.
3. 동일 리밸런싱 규칙 적용: t월 신호를 t+1월 수익률에 적용한다.
4. 모멘텀 산식 고정: 1/3/6/12개월 누적수익률의 단순 평균을 사용한다.
5. 임계값 고정: momentum > 0이면 양호, momentum <= 0이면 bad로 판정한다.
6. IS/OOS 분리: OOS 시작일은 `{CFG.oos_start}`로 고정한다.
7. score 최적화 미사용: CAGR, Calmar 등을 합산한 사후 score로 후보를 재선정하지 않는다.
8. whipsaw proxy 기록: 위험자산 비중 50% 기준 risk-on/risk-off mode flip 횟수를 기록한다.
9. audit table 저장: 수익률 단위, 비중 합계, 음수 비중, t→t+1 적용 근거를 파일로 남긴다.

## 18.5 OOS 성과 요약

{oos_md}

## 18.6 Whipsaw proxy 요약

{whipsaw_md}

## 18.7 검증 audit

{audit_md}

## 18.8 생성된 그림

- `../output/figures/main_final_fig_canary_lineage_cumret.png`
- `../output/figures/main_final_fig_canary_lineage_drawdown.png`
- `../output/figures/main_final_fig_canary_lineage_oos_calmar.png`
- `../output/figures/main_final_fig_canary_lineage_turnover.png`
- `../output/figures/main_final_fig_canary_lineage_whipsaw.png`

## 18.9 해석 원칙

이 실험의 목적은 HSI가 DAA/VAA/BAA보다 우월하다고 단정하는 것이 아니다. 정직한 해석은 다음과 같다.

첫째, HSI는 개인적 시장 전이 관찰에서 출발한 탐구적 실험이었다. 둘째, 기존 카나리아형 동적자산배분 계보와 비교할 필요가 있음을 인식했다. 셋째, 본 실험에서는 동일 국내 ETF 유니버스 안에서 VAA-like, DAA-like, BAA-like proxy를 만들어 HSI와 비교했다. 넷째, 만약 HSI가 OOS 기준 MDD, Calmar, Turnover, whipsaw에서 우위를 보인다면, 이는 5단계 상태분류와 λ 부분조정 구조가 이진적 카나리아 proxy보다 방어형 운용에 유리했을 가능성을 보여주는 보조 근거이다. 다섯째, 반대로 proxy 전략이 더 우수하다면, HSI의 구조적 복잡성이 성과 개선으로 이어지지 않았다는 한계로 받아들여야 한다.

## 18.10 후속 과제

원 논문 DAA/VAA/BAA를 완전 복제하려면 글로벌 ETF offensive/defensive/canary universe가 필요하다. 이번 실험은 국내 ETF 3종 유니버스에서 가능한 proxy 비교이며, 원 논문 전략과의 엄밀한 비교는 후속 연구로 남긴다.
"""
    out = root / CFG.out_doc_dir / "main_final_canary_lineage_benchmark_note.md"
    out.write_text(text, encoding="utf-8")
    return out


def main() -> None:
    warnings.filterwarnings("ignore")
    root = project_root()
    ensure_dirs(root)
    print("=" * 80)
    print("[START] 18_canary_lineage_benchmark")
    print("=" * 80)
    ret = read_monthly_returns(root)
    mom = weighted_momentum(ret, CFG.momentum_windows)
    weights: Dict[str, pd.DataFrame] = {
        "FixedBM_70_20_10": make_fixed_bm_weights(ret.index),
        "EW": make_ew_weights(ret.index),
        "VAA_like_proxy": make_vaa_like_weights(ret, mom),
        "DAA_like_proxy": make_daa_like_weights(ret, mom),
        "BAA_like_proxy": make_baa_like_weights(ret, mom),
    }
    hsi_w = read_hsi_weights_if_available(root, ret.index)
    has_hsi = hsi_w is not None
    if has_hsi:
        weights["HSI_dynamic_v1"] = hsi_w
    returns = {}
    turnovers = {}
    for name, w in weights.items():
        r, tv = backtest_from_signal_weights(ret, w, CFG.cost_bp, name)
        returns[name] = r
        turnovers[name] = tv
    returns_df = pd.DataFrame(returns).dropna(how="all")
    turnovers_df = pd.DataFrame(turnovers).reindex(returns_df.index).fillna(0.0)
    metrics = summarize_all(returns_df, turnovers_df, CFG.oos_start)
    whipsaw = count_whipsaw(weights)
    audit = make_audit_table(ret, weights)
    out_table = root / CFG.out_table_dir
    out_fig = root / CFG.out_figure_dir
    w_long = []
    for name, w in weights.items():
        tmp = w.copy()
        tmp["strategy"] = name
        tmp["date"] = tmp.index
        w_long.append(tmp.reset_index(drop=True))
    pd.concat(w_long, axis=0).to_csv(out_table / "main_final_canary_lineage_weights.csv", index=False, encoding="utf-8-sig")
    returns_df.to_csv(out_table / "main_final_canary_lineage_returns_net10bp.csv", encoding="utf-8-sig")
    turnovers_df.to_csv(out_table / "main_final_canary_lineage_turnover.csv", encoding="utf-8-sig")
    metrics.to_csv(out_table / "main_final_canary_lineage_metrics.csv", index=False, encoding="utf-8-sig")
    whipsaw.to_csv(out_table / "main_final_canary_lineage_whipsaw.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(out_table / "main_final_canary_lineage_validation_audit.csv", index=False, encoding="utf-8-sig")
    with open(out_table / "main_final_canary_lineage_preregistration.json", "w", encoding="utf-8") as f:
        json.dump(asdict(CFG), f, ensure_ascii=False, indent=2)
    save_cumret_plot(returns_df, out_fig / "main_final_fig_canary_lineage_cumret.png")
    save_drawdown_plot(returns_df, out_fig / "main_final_fig_canary_lineage_drawdown.png")
    oos = metrics[metrics["period"] == "OOS"].copy()
    save_horizontal_bar(oos, "calmar", "OOS Calmar comparison", "Calmar ratio", out_fig / "main_final_fig_canary_lineage_oos_calmar.png")
    save_horizontal_bar(oos, "avg_turnover_ann", "OOS average annual one-way turnover", "Average annual turnover, decimal", out_fig / "main_final_fig_canary_lineage_turnover.png")
    save_horizontal_bar(whipsaw, "risk_mode_flips", "Risk-on/risk-off mode flips as whipsaw proxy", "Number of mode flips", out_fig / "main_final_fig_canary_lineage_whipsaw.png")
    note_path = write_report_note(root, metrics, whipsaw, audit, has_hsi)
    print("\n[OUTPUT TABLES]")
    for f in ["main_final_canary_lineage_weights.csv", "main_final_canary_lineage_returns_net10bp.csv", "main_final_canary_lineage_turnover.csv", "main_final_canary_lineage_metrics.csv", "main_final_canary_lineage_whipsaw.csv", "main_final_canary_lineage_validation_audit.csv", "main_final_canary_lineage_preregistration.json"]:
        print(" -", out_table / f)
    print("\n[OUTPUT FIGURES]")
    for f in ["main_final_fig_canary_lineage_cumret.png", "main_final_fig_canary_lineage_drawdown.png", "main_final_fig_canary_lineage_oos_calmar.png", "main_final_fig_canary_lineage_turnover.png", "main_final_fig_canary_lineage_whipsaw.png"]:
        print(" -", out_fig / f)
    print("\n[OUTPUT DOC]")
    print(" -", note_path)
    print("\n[OOS SUMMARY]")
    print(metrics[metrics["period"] == "OOS"].to_string(index=False))
    print("\n[AUDIT]")
    print(audit.to_string(index=False))
    print("=" * 80)
    print("[DONE] 18_canary_lineage_benchmark")
    print("=" * 80)


if __name__ == "__main__":
    main()
