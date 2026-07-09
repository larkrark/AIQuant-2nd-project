"""
33_main_v2_plot_lambda_smoothing_comparison.py

목적
----
"즉시반영(λ=1) vs 평활(λ=0.3/0.1/dynamic_v1)" 차이를 같은 일별 리밸런싱
프레임에서 EW·FixedBM 70/20/10 과 함께 비교한다.

설계
----
- λ 부분조정은 리포트대로 '월별' 신호에 적용(smoothed monthly weight),
  실행은 31번과 동일한 일별 리밸런싱.
- dynamic_v1 규칙: 기본 λ=0.3, 고위험(vol_z>1 | dd<-10% | macro>=2)→0.1,
  안정완화(risk_relief 3개월 지속 & vol_z<0 & mom_z>0)→0.5.
- look-ahead 차단: 월말 신호 → 다음 달 모든 거래일 적용.
- λ 로직은 브랜치 의존성 제거 위해 이 파일에 자체 내장.

입력 : output/tables/main_v2_hsi_state5_table_rank.csv, data/processed/korea_etf_price_clean.csv
출력 : output/tables/main_v2_daily_lambda_cmp_summary.csv,
       output/figures/main_v2_daily_cmp_fig1~4.png
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
FIGURE_DIR = PROJECT_ROOT / "output" / "figures"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

STATE5_PATH = TABLE_DIR / "main_v2_hsi_state5_table_rank.csv"
DAILY_PRICE_PATH = PROCESSED_DIR / "korea_etf_price_clean.csv"

ASSETS = ["069500", "114260", "153130"]
WCOLS = [f"{a}_weight" for a in ASSETS]
TRADING_DAYS = 252


def setup_font():
    c = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if Path(c).exists():
        font_manager.fontManager.addfont(c)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=c).get_name()
    plt.rcParams["axes.unicode_minus"] = False


setup_font()


# ---------- λ 로직 (자체 내장) ----------
def apply_lambda(target_df, lam):
    df = target_df.sort_values("Date").reset_index(drop=True)
    targets = df[WCOLS].to_numpy(dtype=float)
    n = len(df)
    lam_arr = np.full(n, float(lam)) if np.isscalar(lam) else np.asarray(lam, dtype=float)
    realized = np.empty_like(targets)
    prev = targets[0].copy()
    for i in range(n):
        cur = prev if i == 0 else prev + lam_arr[i] * (targets[i] - prev)
        realized[i] = cur
        prev = cur
    out = df.copy(); out[WCOLS] = realized
    return out


def rolling_z(s, window):
    m = s.rolling(window, min_periods=max(3, window // 3)).mean()
    sd = s.rolling(window, min_periods=max(3, window // 3)).std(ddof=1)
    return (s - m) / sd


def dynamic_v1_lambda(state5, monthly_069500_ret):
    r = pd.to_numeric(monthly_069500_ret, errors="coerce").fillna(0.0).reset_index(drop=True)
    ann_vol = r.rolling(12, min_periods=6).std(ddof=1) * np.sqrt(12)
    vol_z = rolling_z(ann_vol, 36).to_numpy()
    idx = (1 + r).cumprod()
    dd = (idx / idx.rolling(12, min_periods=1).max() - 1).to_numpy()
    mom = (1 + r).rolling(12, min_periods=6).apply(np.prod, raw=True) - 1
    mom_z = rolling_z(mom, 36).to_numpy()
    state = state5["hsi_state5"].to_numpy()

    persist = np.zeros(len(state), dtype=int); c = 0
    for i, v in enumerate(state):
        c = c + 1 if v == "risk_relief" else 0
        persist[i] = c

    n = len(state)
    macro = np.zeros(n)
    high_risk = (vol_z > 1.0) | (dd < -0.10) | (macro >= 2)
    easing = (persist >= 3) & (vol_z < 0) & (mom_z > 0)
    lam = np.full(n, 0.3); labels = np.full(n, "default", dtype=object)
    lam[easing] = 0.5; labels[easing] = "easing"
    lam[high_risk] = 0.1; labels[high_risk] = "high_risk"
    return lam, labels


# ---------- 데이터 ----------
def load_daily_returns():
    px = pd.read_csv(DAILY_PRICE_PATH, index_col=0, parse_dates=True)[ASSETS].dropna().sort_index()
    r = px.pct_change().dropna(); r.index.name = "Date"
    return r


def load_state5():
    df = pd.read_csv(STATE5_PATH); df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def monthly_069500(state5, daily):
    mret = (1 + daily).resample("ME").prod() - 1
    mret = mret.copy(); mret["period"] = mret.index.to_period("M")
    s = state5.copy(); s["period"] = s["Date"].dt.to_period("M")
    j = s.merge(mret[["period", "069500"]], on="period", how="left")
    return j["069500"]


def const_weights(state5, w):
    out = state5[["Date"]].copy()
    for a, wv in zip(ASSETS, w):
        out[f"{a}_weight"] = wv
    return out


def expand_and_backtest(monthly_w, daily, name):
    mw = monthly_w.copy(); mw["apply_month"] = mw["Date"].dt.to_period("M") + 1
    d = daily.reset_index(); d["apply_month"] = d["Date"].dt.to_period("M")
    merged = d.merge(mw[["apply_month"] + WCOLS], on="apply_month", how="inner").sort_values("Date").reset_index(drop=True)
    target = merged[WCOLS].to_numpy(); rets = merged[ASSETS].to_numpy()
    port = (target * rets).sum(axis=1)
    drift = target * (1 + rets) / (1 + port)[:, None]
    turn = np.zeros(len(target)); turn[1:] = 0.5 * np.abs(target[1:] - drift[:-1]).sum(axis=1)
    cum = np.cumprod(1 + port); dd = cum / np.maximum.accumulate(cum) - 1.0
    ts = pd.DataFrame({"Date": merged["Date"].values, "cum": cum, "dd": dd, "ret": port, "turn": turn})
    ts["name"] = name
    return ts


def metrics(ts):
    r = ts["ret"]; n = len(r); cum = float(ts["cum"].iloc[-1])
    cagr = cum ** (TRADING_DAYS / n) - 1
    vol = r.std(ddof=1) * np.sqrt(TRADING_DAYS)
    mdd = float(ts["dd"].min())
    return {"CAGR_pct": cagr*100, "vol_pct": vol*100, "MDD_pct": mdd*100,
            "Sharpe": (r.mean()*TRADING_DAYS)/vol if vol > 0 else np.nan,
            "Calmar": cagr/abs(mdd) if mdd < 0 else np.nan,
            "avg_daily_turnover_pct": ts["turn"].mean()*100,
            "total_turnover_pct": ts["turn"].sum()*100}


def main():
    print("=" * 70); print("33 lambda smoothing comparison"); print("=" * 70)
    daily = load_daily_returns(); state5 = load_state5()
    m069 = monthly_069500(state5, daily)
    lam_dyn, labels = dynamic_v1_lambda(state5, m069)
    print("dynamic_v1 λ 라벨 분포:", pd.Series(labels).value_counts().to_dict())

    state_w = state5[["Date"] + WCOLS].copy()
    candidates = {
        "EW (BM)": const_weights(state5, [1/3, 1/3, 1/3]),
        "FixedBM 70/20/10 (BM)": const_weights(state5, [0.70, 0.20, 0.10]),
        "overlay λ=1.0 (즉시반영)": apply_lambda(state_w, 1.0),
        "overlay λ=0.3 (평활)": apply_lambda(state_w, 0.3),
        "overlay λ=0.1 (강평활)": apply_lambda(state_w, 0.1),
        "dynamic_v1 (규칙형 λ)": apply_lambda(state_w, lam_dyn),
    }
    all_ts = {}; rows = []
    for name, mw in candidates.items():
        ts = expand_and_backtest(mw, daily, name); all_ts[name] = ts
        rows.append({"strategy": name, **metrics(ts)})
    summ = pd.DataFrame(rows)
    summ.to_csv(TABLE_DIR / "main_v2_daily_lambda_cmp_summary.csv", index=False, encoding="utf-8-sig")
    print(summ.round(3).to_string(index=False))

    colors = {"EW (BM)": "#888888", "FixedBM 70/20/10 (BM)": "#000000",
              "overlay λ=1.0 (즉시반영)": "#d62728", "overlay λ=0.3 (평활)": "#1f77b4",
              "overlay λ=0.1 (강평활)": "#2ca02c", "dynamic_v1 (규칙형 λ)": "#9467bd"}
    names = list(candidates.keys()); short = [n.split(" (")[0] for n in names]

    fig, ax = plt.subplots(figsize=(12.5, 6))
    for n in names:
        ts = all_ts[n]
        ax.plot(ts["Date"], ts["cum"], label=n, color=colors[n],
                lw=2.0 if "BM" in n else 1.5, ls="--" if "BM" in n else "-")
    ax.axhline(1, color="k", lw=0.7, ls=":", alpha=0.5)
    ax.set_title("즉시반영 vs 평활: 일별 리밸런싱 누적수익률", fontsize=14, fontweight="bold")
    ax.set_ylabel("누적 성장배수 (배)"); ax.set_xlabel("날짜"); ax.grid(alpha=0.3); ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout(); fig.savefig(FIGURE_DIR / "main_v2_daily_cmp_fig1_cumulative.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(12.5, 5.5))
    for n in names:
        ts = all_ts[n]
        ax.plot(ts["Date"], ts["dd"]*100, label=n, color=colors[n],
                lw=1.8 if "BM" in n else 1.3, ls="--" if "BM" in n else "-")
    ax.set_title("즉시반영 vs 평활: 드로다운(낙폭)", fontsize=14, fontweight="bold")
    ax.set_ylabel("Drawdown (%)"); ax.set_xlabel("날짜"); ax.grid(alpha=0.3); ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout(); fig.savefig(FIGURE_DIR / "main_v2_daily_cmp_fig2_drawdown.png", dpi=130); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    barcols = [colors[n] for n in names]
    for ax, col, title, fmt in [(axes[0], "CAGR_pct", "CAGR (%)", "%.1f"),
                                (axes[1], "MDD_pct", "|MDD| (%)", "%.1f"),
                                (axes[2], "Calmar", "Calmar", "%.2f")]:
        vals = [abs(summ[summ.strategy == n][col].iloc[0]) if col == "MDD_pct"
                else summ[summ.strategy == n][col].iloc[0] for n in names]
        b = ax.bar(range(len(names)), vals, color=barcols); ax.bar_label(b, fmt=fmt, fontsize=8, padding=2)
        ax.set_xticks(range(len(names))); ax.set_xticklabels(short, rotation=35, ha="right", fontsize=8)
        ax.set_title(title, fontsize=12, fontweight="bold"); ax.grid(alpha=0.3, axis="y")
    fig.suptitle("성과지표 비교 (연율화 252일)", fontsize=14, fontweight="bold")
    fig.tight_layout(); fig.savefig(FIGURE_DIR / "main_v2_daily_cmp_fig3_metrics.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    vals = [summ[summ.strategy == n]["total_turnover_pct"].iloc[0] for n in names]
    b = ax.bar(range(len(names)), vals, color=barcols); ax.bar_label(b, fmt="%.0f", fontsize=9, padding=2)
    ax.set_xticks(range(len(names))); ax.set_xticklabels(short, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("총 회전율 (%, 전체기간 합)")
    ax.set_title("실행부담: 총 회전율 (평활할수록 감소)", fontsize=14, fontweight="bold"); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(FIGURE_DIR / "main_v2_daily_cmp_fig4_turnover.png", dpi=130); plt.close(fig)
    print("완료: cmp_fig1~4")


if __name__ == "__main__":
    main()
