"""
36_shuffle_control_block_mc.py
HSI 목표비중 블록 셔플 몬테카를로 대조군 — "HSI 방향이 우연인가?" 검정.

설계 (2026-07-08 팀 논의, docs/experiment_notes/셔플_대조군_실험_논의정리_2026-07-08.md):
- λ를 정하는 변동성·drawdown 규칙(시장 데이터 기반 vz/dd/mz)은 그대로 유지.
- HSI가 주는 (상태, 목표비중) 행을 3·6개월 블록 단위로 잘라 블록 순서만 무작위 재배치.
  → 상태 지속성(블록 내부)은 보존, "언제 그 비중을 썼는가"(timing)만 파괴.
  → exposure_effect(시간평균 비중)는 재배열에 거의 불변 → 사실상 timing_effect 유의성 검정.
- 셔플 후 dyn_lambda는 셔플된 상태 시퀀스 + 실제 시장 플래그로 재계산 (풀버전과 동일 규칙).
- 판정: 실제 dynamic_v1 지표가 셔플 분포의 어느 백분위인지. p = (1+#{셔플>=실제})/(N+1).

백테스트 관례는 35번(월별 정본)과 동일: w_t → r_{t+1}, 연율화 12.
실행: python src/36_shuffle_control_block_mc.py [--n 500] [--blocks 3 6] [--seed 42]
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "output" / "tables"
FIG = ROOT / "output" / "figures"
PROC = ROOT / "data" / "processed"
FIG.mkdir(parents=True, exist_ok=True)

ASSETS = ["069500", "114260", "153130"]
WCOLS = [f"{a}_weight" for a in ASSETS]
MPY = 12

for c in [
    "C:/Windows/Fonts/malgun.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]:
    if Path(c).exists():
        font_manager.fontManager.addfont(c)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=c).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False


# ---------------- 35번과 동일한 코어 (정본 월별 관례) ----------------

def apply_lambda_arr(tg: np.ndarray, lam: np.ndarray) -> np.ndarray:
    out = np.empty_like(tg)
    prev = tg[0].copy()
    for i in range(len(tg)):
        out[i] = prev if i == 0 else prev + lam[i] * (tg[i] - prev)
        prev = out[i]
    return out


def rz(s, w):
    return (s - s.rolling(w, min_periods=max(3, w // 3)).mean()) / s.rolling(w, min_periods=max(3, w // 3)).std(ddof=1)


def monthly_returns():
    px = pd.read_csv(PROC / "korea_etf_price_clean.csv", index_col=0, parse_dates=True)[ASSETS].dropna().sort_index()
    m = (1 + px.pct_change()).resample("ME").prod() - 1
    m = m.dropna()
    m.index.name = "Date"
    return m


def load_state5():
    d = pd.read_csv(TAB / "main_v2_hsi_state5_table_rank.csv")
    d["Date"] = pd.to_datetime(d["Date"])
    return d.sort_values("Date").reset_index(drop=True)


def flags(state5, mret):
    s = state5.copy()
    s["p"] = s["Date"].dt.to_period("M")
    mm = mret.copy()
    mm["p"] = mm.index.to_period("M")
    j = s.merge(mm[["p", "069500"]], on="p", how="left")
    r = pd.to_numeric(j["069500"], errors="coerce").fillna(0.0)
    ann = r.rolling(12, min_periods=6).std(ddof=1) * np.sqrt(12)
    vz = rz(ann, 36).to_numpy()
    idx = (1 + r).cumprod()
    dd = (idx / idx.rolling(12, min_periods=1).max() - 1).to_numpy()
    mom = (1 + r).rolling(12, min_periods=6).apply(np.prod, raw=True) - 1
    mz = rz(mom, 36).to_numpy()
    return vz, dd, mz


def dyn_lambda(states: np.ndarray, vz, dd, mz) -> np.ndarray:
    n = len(states)
    per = np.zeros(n, int)
    cc = 0
    for i, v in enumerate(states):
        cc = cc + 1 if v == "risk_relief" else 0
        per[i] = cc
    hr = (vz > 1.0) | (dd < -0.10)
    es = (per >= 3) & (vz < 0) & (mz > 0)
    lam = np.full(n, 0.3)
    lam[es] = 0.5
    lam[hr] = 0.1
    return lam


def align_returns(dates: pd.Series, mret: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """w_t → r_{t+1} 정렬을 1회만 계산 (날짜축은 셔플과 무관하게 고정).

    반환: (valid — s5 행 중 다음 달 수익률이 있는 행의 불리언 마스크,
           R — 해당 행들에 적용될 다음 달 수익률 행렬)
    """
    ret_p = pd.PeriodIndex(dates.dt.to_period("M")) + 1
    r_by_p = mret.copy()
    r_by_p.index = mret.index.to_period("M")
    valid = np.array([p in r_by_p.index for p in ret_p])
    R = r_by_p.loc[ret_p[valid]][ASSETS].to_numpy(float)
    return valid, R


def bt_metrics(weights: np.ndarray, valid: np.ndarray, R: np.ndarray) -> dict:
    """월말 비중 w_t → 다음 달 r_{t+1} (35번 bt_monthly와 동일 관례, 정렬은 사전계산)."""
    W = weights[valid]
    sret = (W * R).sum(axis=1)
    cum = np.cumprod(1 + sret)
    dd = cum / np.maximum.accumulate(cum) - 1
    n = len(sret)
    cagr = cum[-1] ** (MPY / n) - 1
    vol = sret.std(ddof=1) * np.sqrt(MPY)
    mdd = float(dd.min())
    return {
        "CAGR_pct": cagr * 100,
        "MDD_pct": mdd * 100,
        "Sharpe": (sret.mean() * MPY) / vol if vol > 0 else np.nan,
        "Calmar": cagr / abs(mdd) if mdd < 0 else np.nan,
        "avg_w_risky_pct": W[:, 0].mean() * 100,
    }


# ---------------- 블록 셔플 ----------------

def block_shuffle_index(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    starts = list(range(0, n, block))
    blocks = [np.arange(s, min(s + block, n)) for s in starts]
    order = rng.permutation(len(blocks))
    return np.concatenate([blocks[k] for k in order])


def run(n_draws: int, block_lens: list[int], seed: int) -> None:
    mret = monthly_returns()
    s5 = load_state5()
    vz, dd, mz = flags(s5, mret)
    dates = s5["Date"]
    tg = s5[WCOLS].to_numpy(float)
    states = s5["hsi_state5"].to_numpy()
    valid, R = align_returns(dates, mret)

    # 실제 dynamic_v1 (F)
    lam_real = dyn_lambda(states, vz, dd, mz)
    real = bt_metrics(apply_lambda_arr(tg, lam_real), valid, R)
    print("실제 dynamic_v1:", {k: round(v, 3) for k, v in real.items()})

    rng = np.random.default_rng(seed)
    rows = []
    for block in block_lens:
        for d in range(n_draws):
            idx = block_shuffle_index(len(s5), block, rng)
            tg_s, st_s = tg[idx], states[idx]
            lam_s = dyn_lambda(st_s, vz, dd, mz)  # 시장 플래그(vz/dd/mz)는 실제 시간축 유지
            m = bt_metrics(apply_lambda_arr(tg_s, lam_s), valid, R)
            rows.append({"block": block, "draw": d, **m})
    dist = pd.DataFrame(rows)
    dist.to_csv(TAB / "main_v2_shuffle_mc_distribution.csv", index=False, encoding="utf-8-sig")

    # 요약: 백분위·p-value (Calmar·CAGR·Sharpe는 클수록, MDD는 0에 가까울수록 좋음)
    summary = []
    for block in block_lens:
        db = dist[dist["block"] == block]
        N = len(db)
        for metric, better_high in [("CAGR_pct", True), ("MDD_pct", True), ("Sharpe", True), ("Calmar", True)]:
            x = db[metric].to_numpy()
            rv = real[metric]
            n_ge = int((x >= rv).sum()) if better_high else int((x <= rv).sum())
            summary.append({
                "block": block, "metric": metric, "real": rv,
                "shuffle_mean": x.mean(), "shuffle_std": x.std(ddof=1),
                "shuffle_p5": np.percentile(x, 5), "shuffle_p95": np.percentile(x, 95),
                "pct_rank_of_real": (x < rv).mean() * 100,
                "p_value": (1 + n_ge) / (N + 1),
            })
    sm = pd.DataFrame(summary)
    sm.to_csv(TAB / "main_v2_shuffle_mc_summary.csv", index=False, encoding="utf-8-sig")
    print(sm.round(3).to_string(index=False))

    # exposure 보존 sanity check
    chk = dist.groupby("block")["avg_w_risky_pct"].agg(["mean", "std"])
    print("\n[sanity] 위험자산(069500) 시간평균 비중 — 실제 "
          f"{real['avg_w_risky_pct']:.2f}% vs 셔플 {chk['mean'].round(2).to_dict()} (std {chk['std'].round(3).to_dict()})")

    # ---------------- 그림: 지표별 셔플 분포 + 실제값 ----------------
    metrics = [("Calmar", "Calmar (높을수록 좋음)"), ("MDD_pct", "MDD % (0에 가까울수록 좋음)"),
               ("CAGR_pct", "CAGR %"), ("Sharpe", "Sharpe")]
    fig, axes = plt.subplots(len(block_lens), len(metrics), figsize=(4.2 * len(metrics), 3.2 * len(block_lens)))
    axes = np.atleast_2d(axes)
    for i, block in enumerate(block_lens):
        db = dist[dist["block"] == block]
        for k, (mcol, mlabel) in enumerate(metrics):
            ax = axes[i, k]
            ax.hist(db[mcol], bins=40, color="#9fc2e8", edgecolor="white")
            ax.axvline(real[mcol], color="#C44E52", lw=2)
            pct = (db[mcol] < real[mcol]).mean() * 100
            ax.set_title(f"{mlabel}\n{block}M 블록 · 실제={real[mcol]:.2f} (상위 {100-pct:.1f}%)", fontsize=9.5)
            ax.tick_params(labelsize=8)
    fig.suptitle(f"HSI 목표비중 블록 셔플 몬테카를로 (N={n_draws}/블록, seed={seed}) — 실제 dynamic_v1 vs 셔플 분포",
                 fontsize=12.5)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG / "main_v2_shuffle_mc_distributions.png", dpi=150)
    print(f"\n[저장] {TAB/'main_v2_shuffle_mc_distribution.csv'}")
    print(f"[저장] {TAB/'main_v2_shuffle_mc_summary.csv'}")
    print(f"[저장] {FIG/'main_v2_shuffle_mc_distributions.png'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--blocks", type=int, nargs="+", default=[3, 6])
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    run(a.n, a.blocks, a.seed)
