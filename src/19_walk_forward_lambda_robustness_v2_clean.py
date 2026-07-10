# -*- coding: utf-8 -*-
r"""
19_walk_forward_lambda_robustness.py

간이 walk-forward robustness check.

목적
- '최적화했다'가 아니라, 사전에 정한 lambda 후보군이 시간에 따라 얼마나 안정적인지 확인한다.
- 각 train window 안에서만 lambda 후보를 선별하고, 다음 test window에서는 lambda를 고정 적용한다.
- test 결과를 보고 같은 window의 lambda를 다시 바꾸지 않는다.

실행 위치:
C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project

실행:
python .\src\19_walk_forward_lambda_robustness.py
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Tuple, List
import json
import math
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class CFG:
    experiment_id: str = "19_walk_forward_lambda_robustness"
    experiment_name: str = "Limited walk-forward robustness check for lambda candidates"
    version: str = "v1_pre_registered"

    equity: str = "069500"
    bond: str = "114260"
    cash_like: str = "153130"

    cost_bp: float = 10.0
    periods_per_year: int = 12

    lambda_candidates: Tuple[float, ...] = (0.1, 0.3, 0.5, 0.7, 1.0)
    train_months: int = 72
    test_months: int = 12
    step_months: int = 12
    turnover_cap_ann: float = 0.20

    # HSI 상태별 목표비중: 069500 / 114260 / 153130
    target_risk_relief: Tuple[float, float, float] = (0.70, 0.20, 0.10)
    target_neutral_watch: Tuple[float, float, float] = (0.50, 0.35, 0.15)
    target_conflict: Tuple[float, float, float] = (0.35, 0.40, 0.25)
    target_risk_warning: Tuple[float, float, float] = (0.20, 0.45, 0.35)
    target_accident_zone: Tuple[float, float, float] = (0.00, 0.30, 0.70)

    return_file_candidates: Tuple[str, ...] = (
        "data/processed/main_final_monthly_return_decimal.csv",
        "data/processed/monthly_return_decimal.csv",
        "output/tables/main_final_monthly_return_decimal.csv",
    )
    hsi_state_file_candidates: Tuple[str, ...] = (
        "output/tables/main_final_portfolio_composition_dynamic_v1.csv",
        "data/processed/main_final_portfolio_composition_dynamic_v1.csv",
        "main_final_portfolio_composition_dynamic_v1.csv",
        "data/processed/main_final_hsi_state5.csv",
        "output/tables/main_final_hsi_state5.csv",
        "data/processed/main_final_hsi_signal.csv",
    )

    out_table_dir: str = "output/tables"
    out_figure_dir: str = "output/figures"
    out_doc_dir: str = "docs"


C = CFG()


def ensure_dirs(root: Path) -> None:
    for d in [C.out_table_dir, C.out_figure_dir, C.out_doc_dir]:
        (root / d).mkdir(parents=True, exist_ok=True)


def find_existing_file(root: Path, candidates: Tuple[str, ...], label: str) -> Path:
    for rel in candidates:
        p = root / rel
        if p.exists():
            print(f"[OK] {label}: {p}")
            return p
    raise FileNotFoundError(label + " 파일을 찾지 못했습니다:\n" + "\n".join(str(root / x) for x in candidates))


def parse_date_index(df: pd.DataFrame) -> pd.DataFrame:
    date_names = ["date", "month", "ym", "rebalance_date", "apply_date", "signal_date"]
    cols = [c for c in df.columns if str(c).lower() in date_names]
    df = df.copy()
    if cols:
        df[cols[0]] = pd.to_datetime(df[cols[0]])
        df = df.set_index(cols[0])
    else:
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
    w = w.copy().apply(pd.to_numeric, errors="coerce").ffill().fillna(0.0)
    s = w.sum(axis=1)
    bad = s.abs() < 1e-12
    if bad.any():
        w.loc[bad, :] = np.nan
        w = w.ffill().fillna(0.0)
        s = w.sum(axis=1)
    return w.div(s, axis=0)


def read_monthly_returns(root: Path) -> pd.DataFrame:
    p = find_existing_file(root, C.return_file_candidates, "monthly_return_decimal")
    df = pd.read_csv(p)
    df = clean_ticker_columns(parse_date_index(df))
    needed = [C.equity, C.bond, C.cash_like]
    missing = [x for x in needed if x not in df.columns]
    if missing:
        raise ValueError(f"수익률 파일에 필요한 ETF 컬럼이 없습니다: {missing}, 현재 컬럼={list(df.columns)}")
    ret = df[needed].apply(pd.to_numeric, errors="coerce").dropna(how="all")
    max_abs = ret.abs().max().max()
    if max_abs > 1.0:
        raise ValueError(f"수익률 최대 절댓값이 {max_abs:.4f}입니다. decimal이 아니라 percent 단위일 수 있습니다.")
    return ret


def read_hsi_state_series(root: Path, ret_index: pd.DatetimeIndex) -> Tuple[pd.Series, str, str]:
    for rel in C.hsi_state_file_candidates:
        p = root / rel
        if not p.exists():
            continue
        try:
            raw = pd.read_csv(p)
            low = {str(c).lower(): c for c in raw.columns}
            if "hsi_state" not in low:
                continue
            state_col = low["hsi_state"]
            if "apply_date" in low:
                date_col = low["apply_date"]
                mode = "applied"
            elif "signal_date" in low:
                date_col = low["signal_date"]
                mode = "signal"
            else:
                candidates = [c for c in raw.columns if str(c).lower() in ["date", "month", "ym", "rebalance_date"]]
                if not candidates:
                    continue
                date_col = candidates[0]
                mode = "signal"
            df = raw[[date_col, state_col]].copy()
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.dropna(subset=[date_col, state_col]).drop_duplicates(subset=[date_col])
            s = df.set_index(date_col)[state_col].astype(str).sort_index().reindex(ret_index).ffill()
            print(f"[OK] HSI state loaded: {p}")
            print(f"     detected mode: {mode}")
            return s, mode, str(p)
        except Exception as e:
            print(f"[WARN] HSI state 후보 읽기 실패: {p} / {e}")
    raise FileNotFoundError("hsi_state 컬럼이 있는 파일을 찾지 못했습니다. main_final_portfolio_composition_dynamic_v1.csv를 output/tables에 넣어 주세요.")


def state_to_target_weights(state: pd.Series) -> pd.DataFrame:
    mapping = {
        "risk_relief": C.target_risk_relief,
        "neutral_watch": C.target_neutral_watch,
        "conflict": C.target_conflict,
        "risk_warning": C.target_risk_warning,
        "accident_zone": C.target_accident_zone,
    }
    rows = []
    prev = C.target_neutral_watch
    for dt, st in state.items():
        key = str(st).strip()
        if key == "insufficient_data":
            vals = prev
        elif key in mapping:
            vals = mapping[key]
            prev = vals
        else:
            vals = prev
        rows.append((dt, vals[0], vals[1], vals[2], key))
    out = pd.DataFrame(rows, columns=["date", C.equity, C.bond, C.cash_like, "hsi_state"]).set_index("date")
    return normalize_weights(out[[C.equity, C.bond, C.cash_like]])


def simulate_lambda_weights(target_w: pd.DataFrame, lam: float) -> pd.DataFrame:
    target_w = normalize_weights(target_w)
    out = pd.DataFrame(index=target_w.index, columns=target_w.columns, dtype=float)
    prev = target_w.iloc[0].values.astype(float)
    out.iloc[0] = prev
    for i in range(1, len(target_w)):
        tgt = target_w.iloc[i].values.astype(float)
        prev = prev + lam * (tgt - prev)
        out.iloc[i] = prev
    return normalize_weights(out)


def one_way_turnover(weights: pd.DataFrame) -> pd.Series:
    return weights.diff().abs().sum(axis=1) / 2.0


def backtest_weights(ret: pd.DataFrame, weights: pd.DataFrame, name: str, mode: str) -> Tuple[pd.Series, pd.Series]:
    w = normalize_weights(weights.reindex(ret.index).ffill())
    applied_w = w if mode == "applied" else w.shift(1)
    gross = (applied_w * ret).sum(axis=1)
    tv = one_way_turnover(w)
    net = gross - tv * (C.cost_bp / 10000.0)
    net = net.dropna()
    return net.rename(name), tv.reindex(net.index).fillna(0.0).rename(name)


def max_drawdown(r: pd.Series) -> float:
    v = (1.0 + r.fillna(0.0)).cumprod()
    return float((v / v.cummax() - 1.0).min())


def cagr(r: pd.Series) -> float:
    x = r.dropna()
    if len(x) == 0:
        return np.nan
    total = float((1.0 + x).prod())
    if total <= 0:
        return np.nan
    return total ** (C.periods_per_year / len(x)) - 1.0


def ann_vol(r: pd.Series) -> float:
    x = r.dropna()
    if len(x) < 2:
        return np.nan
    return float(x.std(ddof=1) * math.sqrt(C.periods_per_year))


def sharpe(r: pd.Series) -> float:
    vol = ann_vol(r)
    return np.nan if abs(vol) < 1e-12 else cagr(r) / vol


def calmar(r: pd.Series) -> float:
    mdd = max_drawdown(r)
    return np.nan if abs(mdd) < 1e-12 else cagr(r) / abs(mdd)


def metrics_for(r: pd.Series, tv: pd.Series) -> Dict[str, float]:
    x = r.dropna()
    t = tv.reindex(x.index).fillna(0.0)
    if len(x) == 0:
        return {"months": 0, "cum_return": np.nan, "cagr": np.nan, "ann_vol": np.nan, "mdd": np.nan, "sharpe": np.nan, "calmar": np.nan, "monthly_win_rate": np.nan, "avg_turnover_ann": np.nan}
    return {
        "months": int(len(x)),
        "cum_return": float((1.0 + x).prod() - 1.0),
        "cagr": cagr(x),
        "ann_vol": ann_vol(x),
        "mdd": max_drawdown(x),
        "sharpe": sharpe(x),
        "calmar": calmar(x),
        "monthly_win_rate": float((x > 0).mean()),
        "avg_turnover_ann": float(t.mean() * 12.0),
    }


def make_benchmark_returns(ret: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    fixed = pd.DataFrame({C.equity: 0.70, C.bond: 0.20, C.cash_like: 0.10}, index=ret.index)
    ew = pd.DataFrame({C.equity: 1/3, C.bond: 1/3, C.cash_like: 1/3}, index=ret.index)
    out_r, out_t = {}, {}
    for name, w in [("FixedBM_70_20_10", fixed), ("EW", ew)]:
        r, tv = backtest_weights(ret, w, name, mode="applied")
        out_r[name] = r
        out_t[name] = tv
    return pd.DataFrame(out_r), pd.DataFrame(out_t)


def build_windows(index: pd.DatetimeIndex) -> List[Tuple[int, pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    windows = []
    i = C.train_months
    wid = 1
    while i + C.test_months <= len(index):
        windows.append((wid, index[i - C.train_months], index[i - 1], index[i], index[i + C.test_months - 1]))
        wid += 1
        i += C.step_months
    return windows


def select_lambda(train_metrics: pd.DataFrame) -> Tuple[float, str]:
    eligible = train_metrics[train_metrics["avg_turnover_ann"] <= C.turnover_cap_ann].copy()
    reason = f"max Calmar among candidates with avg_turnover_ann <= {C.turnover_cap_ann:.2f}"
    if eligible.empty:
        eligible = train_metrics.copy()
        reason = "all candidates exceeded turnover cap; selected max Calmar without turnover filter"
    eligible = eligible.sort_values(["calmar", "mdd", "avg_turnover_ann"], ascending=[False, False, True])
    return float(eligible.iloc[0]["lambda"]), reason


def run_walk_forward(returns_by_lam: Dict[float, pd.Series], tv_by_lam: Dict[float, pd.Series], index: pd.DatetimeIndex) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows, parts = [], []
    for wid, tr_s, tr_e, te_s, te_e in build_windows(index):
        train_rows = []
        for lam in C.lambda_candidates:
            m = metrics_for(returns_by_lam[lam].loc[tr_s:tr_e], tv_by_lam[lam].loc[tr_s:tr_e])
            m["lambda"] = lam
            train_rows.append(m)
        train_m = pd.DataFrame(train_rows)
        chosen, reason = select_lambda(train_m)
        test_r = returns_by_lam[chosen].loc[te_s:te_e]
        test_tv = tv_by_lam[chosen].loc[te_s:te_e]
        test_m = metrics_for(test_r, test_tv)
        tr_sel = train_m[train_m["lambda"] == chosen].iloc[0]
        rows.append({
            "window_id": wid,
            "train_start": tr_s.date().isoformat(), "train_end": tr_e.date().isoformat(),
            "test_start": te_s.date().isoformat(), "test_end": te_e.date().isoformat(),
            "selected_lambda": chosen, "selection_reason": reason,
            "train_selected_cagr": tr_sel["cagr"], "train_selected_mdd": tr_sel["mdd"],
            "train_selected_calmar": tr_sel["calmar"], "train_selected_turnover_ann": tr_sel["avg_turnover_ann"],
            "test_cum_return": test_m["cum_return"], "test_cagr": test_m["cagr"],
            "test_ann_vol": test_m["ann_vol"], "test_mdd": test_m["mdd"],
            "test_sharpe": test_m["sharpe"], "test_calmar": test_m["calmar"],
            "test_monthly_win_rate": test_m["monthly_win_rate"], "test_turnover_ann": test_m["avg_turnover_ann"],
        })
        part = test_r.to_frame("WF_selected_lambda")
        part["selected_lambda"] = chosen
        part["window_id"] = wid
        parts.append(part)
    return pd.DataFrame(rows), pd.concat(parts).sort_index()


def save_selected_lambda_plot(ws: pd.DataFrame, path: Path) -> None:
    plt.figure(figsize=(10, 5))
    plt.plot(ws["window_id"], ws["selected_lambda"], marker="o")
    plt.title("Walk-forward selected lambda by window")
    plt.xlabel("Window")
    plt.ylabel("Selected lambda")
    plt.xticks(ws["window_id"])
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def save_cumret_plot(ret_df: pd.DataFrame, path: Path) -> None:
    cum = (1.0 + ret_df.fillna(0.0)).cumprod() - 1.0
    plt.figure(figsize=(12, 7))
    for c in cum.columns:
        plt.plot(cum.index, cum[c], label=c)
    plt.axhline(0, linewidth=1)
    plt.title("Walk-forward stitched test returns")
    plt.xlabel("Date")
    plt.ylabel("Cumulative return, decimal")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def save_test_calmar_plot(ws: pd.DataFrame, path: Path) -> None:
    plt.figure(figsize=(10, 5))
    plt.bar(ws["window_id"], ws["test_calmar"])
    plt.title("Walk-forward test Calmar by window")
    plt.xlabel("Window")
    plt.ylabel("Test Calmar")
    plt.xticks(ws["window_id"])
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def simple_markdown_table(df: pd.DataFrame, floatfmt: str = ".4f") -> str:
    """pandas.to_markdown 없이 markdown 표를 만든다. tabulate 미설치 환경 대비용."""
    if df is None or df.empty:
        return "(empty)"
    d = df.copy()

    def fmt(x):
        if pd.isna(x):
            return ""
        if isinstance(x, float):
            try:
                return format(x, floatfmt)
            except Exception:
                return str(x)
        return str(x)

    cols = [str(c) for c in d.columns]
    rows = [[fmt(v) for v in row] for row in d.to_numpy()]
    out = []
    out.append("| " + " | ".join(cols) + " |")
    out.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def write_note(root: Path, ws: pd.DataFrame, metrics: pd.DataFrame, audit: pd.DataFrame) -> Path:
    p = root / C.out_doc_dir / "main_final_walk_forward_lambda_robustness_note.md"
    text = f"""# 19. 간이 Walk-forward Robustness Check: λ 후보 안정성 점검

## 19.1 목적

본 실험은 HSI 전략의 λ 후보가 특정 전체기간 성과에만 맞춰진 것인지 점검하기 위한 간이 walk-forward robustness check이다. 이 실험은 상용 RA 수준의 완전한 walk-forward 검증이 아니라, 교육용 프로젝트의 과적합 방어를 보강하기 위한 후속 검증이다.

## 19.2 실험 설정

- train window: {C.train_months}개월
- test window: {C.test_months}개월
- step: {C.step_months}개월
- 거래비용: {C.cost_bp}bp
- 후보 λ: {C.lambda_candidates}
- 선택 기준: train Calmar 우선, 평균 연환산 Turnover {C.turnover_cap_ann:.2f} 이하 후보 우선
- 원칙: train window 안에서만 λ를 선별하고, test window에서는 고정 적용

## 19.3 Window별 선택 결과

{simple_markdown_table(ws, '.4f')}

## 19.4 Walk-forward stitched test 성과

{simple_markdown_table(metrics, '.4f')}

## 19.5 Audit

{simple_markdown_table(audit, '.4f')}

## 19.6 해석 원칙

이 실험은 λ를 최적화했다는 의미가 아니다. 각 시점에서 과거 train 구간만 보고 방어형 목적에 맞는 후보를 고른 뒤, 다음 test 구간에 고정 적용했을 때 결과가 급격히 무너지는지 확인한 것이다. 따라서 결과가 양호하더라도 상용 RA 수준의 검증이 완료되었다고 말하지 않고, 결과가 약하더라도 HSI 전체가 무효라고 단정하지 않는다.
"""
    p.write_text(text, encoding="utf-8")
    return p


def main() -> None:
    warnings.filterwarnings("ignore")
    root = Path.cwd()
    ensure_dirs(root)
    print("=" * 80)
    print("[START] 19_walk_forward_lambda_robustness")
    print("=" * 80)

    ret = read_monthly_returns(root)
    state, state_mode, state_source = read_hsi_state_series(root, ret.index)
    target_w = state_to_target_weights(state)

    returns_by_lam: Dict[float, pd.Series] = {}
    tv_by_lam: Dict[float, pd.Series] = {}
    for lam in C.lambda_candidates:
        w = simulate_lambda_weights(target_w, lam)
        r, tv = backtest_weights(ret, w, f"lambda_{lam}", mode=state_mode)
        returns_by_lam[lam] = r
        tv_by_lam[lam] = tv

    common = pd.concat(list(returns_by_lam.values()), axis=1).dropna(how="all").index
    window_summary, stitched = run_walk_forward(returns_by_lam, tv_by_lam, common)
    if window_summary.empty:
        raise ValueError("walk-forward window가 생성되지 않았습니다. train_months/test_months를 줄여야 합니다.")

    bm_r, bm_t = make_benchmark_returns(ret)
    stitched_returns = stitched[["WF_selected_lambda"]].copy()
    stitched_turnover_parts = []
    for _, row in window_summary.iterrows():
        lam = float(row["selected_lambda"])
        s = pd.to_datetime(row["test_start"])
        e = pd.to_datetime(row["test_end"])
        stitched_turnover_parts.append(tv_by_lam[lam].loc[s:e])
    wf_tv = pd.concat(stitched_turnover_parts).sort_index()
    wf_tv = wf_tv[~wf_tv.index.duplicated(keep="first")]

    for col in bm_r.columns:
        stitched_returns[col] = bm_r[col].reindex(stitched_returns.index)
    for lam in C.lambda_candidates:
        stitched_returns[f"static_lambda_{lam}"] = returns_by_lam[lam].reindex(stitched_returns.index)

    metrics_rows = []
    for col in stitched_returns.columns:
        if col == "WF_selected_lambda":
            tv = wf_tv
        elif col in bm_t.columns:
            tv = bm_t[col].reindex(stitched_returns.index)
        elif col.startswith("static_lambda_"):
            lam = float(col.replace("static_lambda_", ""))
            tv = tv_by_lam[lam].reindex(stitched_returns.index)
        else:
            tv = pd.Series(0.0, index=stitched_returns.index)
        m = metrics_for(stitched_returns[col], tv)
        m["strategy"] = col
        metrics_rows.append(m)
    metrics = pd.DataFrame(metrics_rows)[["strategy", "months", "cum_return", "cagr", "ann_vol", "mdd", "sharpe", "calmar", "monthly_win_rate", "avg_turnover_ann"]]

    audit = pd.DataFrame([
        {"check": "return_unit_decimal", "status": "PASS" if ret.abs().max().max() <= 1.0 else "FAIL", "evidence": f"max_abs_return={ret.abs().max().max():.6f}"},
        {"check": "hsi_state_loaded", "status": "PASS", "evidence": f"state_mode={state_mode}, source={state_source}, non_null_states={int(state.notna().sum())}"},
        {"check": "walk_forward_no_test_reselection", "status": "PASS", "evidence": "selected lambda is determined only from each train window and fixed in the next test window"},
        {"check": "window_count", "status": "PASS", "evidence": f"n_windows={len(window_summary)}, train_months={C.train_months}, test_months={C.test_months}, step_months={C.step_months}"},
        {"check": "parameter_lock", "status": "PASS", "evidence": json.dumps(asdict(C), ensure_ascii=False)},
    ])

    out_table = root / C.out_table_dir
    out_fig = root / C.out_figure_dir
    window_summary.to_csv(out_table / "main_final_walk_forward_lambda_window_summary.csv", index=False, encoding="utf-8-sig")
    stitched_returns.to_csv(out_table / "main_final_walk_forward_lambda_stitched_returns.csv", encoding="utf-8-sig")
    metrics.to_csv(out_table / "main_final_walk_forward_lambda_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({f"lambda_{lam}": returns_by_lam[lam] for lam in C.lambda_candidates}).to_csv(out_table / "main_final_walk_forward_lambda_candidate_full_returns.csv", encoding="utf-8-sig")
    audit.to_csv(out_table / "main_final_walk_forward_lambda_validation_audit.csv", index=False, encoding="utf-8-sig")
    with open(out_table / "main_final_walk_forward_lambda_preregistration.json", "w", encoding="utf-8") as f:
        json.dump(asdict(C), f, ensure_ascii=False, indent=2)

    save_selected_lambda_plot(window_summary, out_fig / "main_final_fig_walk_forward_selected_lambda.png")
    save_cumret_plot(stitched_returns[["WF_selected_lambda", "FixedBM_70_20_10", "EW"]], out_fig / "main_final_fig_walk_forward_cumret.png")
    save_test_calmar_plot(window_summary, out_fig / "main_final_fig_walk_forward_test_calmar.png")
    note_path = write_note(root, window_summary, metrics, audit)

    print("\n[OUTPUT TABLES]")
    for f in [
        "main_final_walk_forward_lambda_window_summary.csv",
        "main_final_walk_forward_lambda_stitched_returns.csv",
        "main_final_walk_forward_lambda_metrics.csv",
        "main_final_walk_forward_lambda_candidate_full_returns.csv",
        "main_final_walk_forward_lambda_validation_audit.csv",
        "main_final_walk_forward_lambda_preregistration.json",
    ]:
        print(" -", out_table / f)
    print("\n[OUTPUT FIGURES]")
    for f in [
        "main_final_fig_walk_forward_selected_lambda.png",
        "main_final_fig_walk_forward_cumret.png",
        "main_final_fig_walk_forward_test_calmar.png",
    ]:
        print(" -", out_fig / f)
    print("\n[OUTPUT DOC]")
    print(" -", note_path)
    print("\n[WINDOW SUMMARY]")
    print(window_summary.to_string(index=False))
    print("\n[WALK-FORWARD METRICS]")
    print(metrics.to_string(index=False))
    print("\n[AUDIT]")
    print(audit.to_string(index=False))
    print("=" * 80)
    print("[DONE] 19_walk_forward_lambda_robustness")
    print("=" * 80)


if __name__ == "__main__":
    main()
