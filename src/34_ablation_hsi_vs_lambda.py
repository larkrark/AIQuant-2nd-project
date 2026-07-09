"""
34_ablation_hsi_vs_lambda.py — HSI 방향 vs 변동성 기반 λ 기여 분리(ablation).

교란 문제: 위기 때 HSI(방향)와 vol/dd 기반 λ(속도)가 같은 달·같은 방어방향으로
동시에 켜져, 낙폭통제 성과의 원인을 분리할 수 없음.

분리 설계(2요인 ablation): HSI 방향(있음/없음) × λ 속도(고정/vol동적).
  A EW                         : HSI X, 방어 X          (베이스)
  B FixedBM 70/20/10           : HSI X, 방어 X          (공격 베이스)
  C HSI + λ=0.3(고정)          : HSI O, vol-λ X         (HSI 방향만)
  D HSI + λ=0.1(고정)          : HSI O, vol-λ X (느린)
  E VolOnly de-risk + λ=0.3    : HSI X, vol 방어 O      (HSI 없이 변동성만)
  F dynamic_v1 = HSI + 동적λ   : HSI O, vol-λ O         (풀버전)

해석:
  F vs E : HSI가 vol 방어 위에 추가로 기여하나? (E≈F면 HSI 잉여 의심)
  F vs C : vol 동적 λ가 HSI 위에 추가로 기여하나?
  E vs A : HSI 없는 순수 vol 방어의 효과
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "output" / "tables"; FIG = ROOT / "output" / "figures"
PROC = ROOT / "data" / "processed"; FIG.mkdir(parents=True, exist_ok=True)
ASSETS = ["069500", "114260", "153130"]; WCOLS = [f"{a}_weight" for a in ASSETS]; TD = 252

c = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if Path(c).exists():
    font_manager.fontManager.addfont(c)
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=c).get_name()
plt.rcParams["axes.unicode_minus"] = False

DEF_W = [0.20, 0.45, 0.35]   # risk_warning 방어 배분(디자인 상수, 방어 target 벡터)
BASE_W = [0.70, 0.20, 0.10]  # vol-only 베이스(평시)

def apply_lambda(df, lam):
    df = df.sort_values("Date").reset_index(drop=True)
    tg = df[WCOLS].to_numpy(float); n = len(df)
    la = np.full(n, float(lam)) if np.isscalar(lam) else np.asarray(lam, float)
    out = np.empty_like(tg); prev = tg[0].copy()
    for i in range(n):
        cur = prev if i == 0 else prev + la[i]*(tg[i]-prev)
        out[i] = cur; prev = cur
    r = df.copy(); r[WCOLS] = out; return r

def rz(s, w):
    return (s - s.rolling(w, min_periods=max(3, w//3)).mean()) / s.rolling(w, min_periods=max(3, w//3)).std(ddof=1)

def load_daily():
    px = pd.read_csv(PROC/"korea_etf_price_clean.csv", index_col=0, parse_dates=True)[ASSETS].dropna().sort_index()
    r = px.pct_change().dropna(); r.index.name = "Date"; return r

def load_state5():
    d = pd.read_csv(TAB/"main_v2_hsi_state5_table_rank.csv"); d["Date"] = pd.to_datetime(d["Date"])
    return d.sort_values("Date").reset_index(drop=True)

def vol_dd_flags(state5, daily):
    mret = (1+daily).resample("ME").prod()-1; mret = mret.copy(); mret["p"] = mret.index.to_period("M")
    s = state5.copy(); s["p"] = s["Date"].dt.to_period("M")
    j = s.merge(mret[["p","069500"]], on="p", how="left")
    r = pd.to_numeric(j["069500"], errors="coerce").fillna(0.0)
    ann = r.rolling(12, min_periods=6).std(ddof=1)*np.sqrt(12); vz = rz(ann, 36).to_numpy()
    idx = (1+r).cumprod(); dd = (idx/idx.rolling(12, min_periods=1).max()-1).to_numpy()
    mom = (1+r).rolling(12, min_periods=6).apply(np.prod, raw=True)-1; mz = rz(mom, 36).to_numpy()
    return vz, dd, mz

def dyn_lambda(state5, vz, dd, mz):
    st = state5["hsi_state5"].to_numpy(); n = len(st)
    per = np.zeros(n, int); cc = 0
    for i, v in enumerate(st):
        cc = cc+1 if v == "risk_relief" else 0; per[i] = cc
    hr = (vz > 1.0) | (dd < -0.10); es = (per >= 3) & (vz < 0) & (mz > 0)
    lam = np.full(n, 0.3); lam[es] = 0.5; lam[hr] = 0.1; return lam

def const_w(state5, w):
    o = state5[["Date"]].copy()
    for a, wv in zip(ASSETS, w): o[f"{a}_weight"] = wv
    return o

def volonly_w(state5, vz, dd):
    """HSI 미사용: vol_z>1 또는 dd<-10%면 방어 배분, 아니면 베이스."""
    defensive = (vz > 1.0) | (dd < -0.10)
    o = state5[["Date"]].copy()
    for k, a in enumerate(ASSETS):
        o[f"{a}_weight"] = np.where(defensive, DEF_W[k], BASE_W[k])
    return o

def bt(mw, daily):
    mw = mw.copy(); mw["am"] = mw["Date"].dt.to_period("M")+1
    d = daily.reset_index(); d["am"] = d["Date"].dt.to_period("M")
    m = d.merge(mw[["am"]+WCOLS], on="am", how="inner").sort_values("Date").reset_index(drop=True)
    tg = m[WCOLS].to_numpy(); rr = m[ASSETS].to_numpy(); port = (tg*rr).sum(axis=1)
    drift = tg*(1+rr)/(1+port)[:,None]; turn = np.zeros(len(tg)); turn[1:] = 0.5*np.abs(tg[1:]-drift[:-1]).sum(axis=1)
    cum = np.cumprod(1+port); dd = cum/np.maximum.accumulate(cum)-1
    return pd.DataFrame({"Date": m["Date"].values, "cum": cum, "dd": dd, "ret": port, "turn": turn})

def met(ts):
    r = ts["ret"]; n = len(r); cum = float(ts["cum"].iloc[-1]); cagr = cum**(TD/n)-1
    vol = r.std(ddof=1)*np.sqrt(TD); mdd = float(ts["dd"].min())
    return {"CAGR_pct": cagr*100, "MDD_pct": mdd*100, "Sharpe": (r.mean()*TD)/vol if vol>0 else np.nan,
            "Calmar": cagr/abs(mdd) if mdd < 0 else np.nan, "total_turnover_pct": ts["turn"].sum()*100}

def main():
    daily = load_daily(); s5 = load_state5(); vz, dd, mz = vol_dd_flags(s5, daily)
    lam_dyn = dyn_lambda(s5, vz, dd, mz)
    sw = s5[["Date"]+WCOLS].copy()
    arms = {
        "A. EW (HSI×,방어×)": const_w(s5, [1/3]*3),
        "B. FixedBM 70/20/10 (HSI×,방어×)": const_w(s5, BASE_W),
        "C. HSI + λ0.3 (HSI만)": apply_lambda(sw, 0.3),
        "D. HSI + λ0.1 (HSI만,느린)": apply_lambda(sw, 0.1),
        "E. VolOnly de-risk + λ0.3 (HSI×,vol방어O)": apply_lambda(volonly_w(s5, vz, dd), 0.3),
        "F. dynamic_v1 = HSI + 동적λ (풀)": apply_lambda(sw, lam_dyn),
    }
    rows = {}; 
    out = []
    for name, mw in arms.items():
        ts = bt(mw, daily); rows[name] = ts; out.append({"arm": name, **met(ts)})
    df = pd.DataFrame(out)
    df.to_csv(TAB/"main_v2_daily_ablation_hsi_vs_lambda.csv", index=False, encoding="utf-8-sig")
    print(df.round(3).to_string(index=False))

    # 분해 요약
    def g(n, k): return df[df.arm==n][k].iloc[0]
    A="A. EW (HSI×,방어×)"; C="C. HSI + λ0.3 (HSI만)"; E="E. VolOnly de-risk + λ0.3 (HSI×,vol방어O)"; F="F. dynamic_v1 = HSI + 동적λ (풀)"
    print("\n[분해] MDD 기준")
    print(f"  vol 방어만(E) MDD           : {g(E,'MDD_pct'):.2f}%")
    print(f"  HSI 방향만(C) MDD           : {g(C,'MDD_pct'):.2f}%")
    print(f"  풀(F) MDD                   : {g(F,'MDD_pct'):.2f}%")
    print(f"  F−E (HSI의 추가 기여)       : {g(F,'MDD_pct')-g(E,'MDD_pct'):+.2f}%p")
    print(f"  F−C (동적λ의 추가 기여)     : {g(F,'MDD_pct')-g(C,'MDD_pct'):+.2f}%p")

    # 그림: MDD / Calmar 그룹바
    names = list(arms.keys()); short = [n.split(".")[0] for n in names]
    palette = ["#888","#000","#1f77b4","#17becf","#d62728","#9467bd"]
    fig,(a1,a2)=plt.subplots(1,2,figsize=(14,5.6))
    for ax,col,ttl,fmt in [(a1,"MDD_pct","|MDD| (%) — 낮을수록 방어",'%.1f'),(a2,"Calmar","Calmar — 높을수록 우수",'%.2f')]:
        vals=[abs(g(n,col)) if col=="MDD_pct" else g(n,col) for n in names]
        b=ax.bar(range(len(names)),vals,color=palette); ax.bar_label(b,fmt=fmt,fontsize=9)
        ax.set_xticks(range(len(names))); ax.set_xticklabels(short,fontsize=11)
        ax.set_title(ttl,fontsize=12,fontweight="bold"); ax.grid(alpha=0.3,axis="y")
    fig.suptitle("Ablation: HSI 방향 vs 변동성 기반 λ 기여 분리",fontsize=14,fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG/"main_v2_daily_ablation_mdd_calmar.png",dpi=130); plt.close(fig)

    fig,ax=plt.subplots(figsize=(12.5,6))
    for n,cl in zip(names,palette):
        ax.plot(rows[n]["Date"],rows[n]["dd"]*100,label=n.split(" (")[0],color=cl,lw=1.4)
    ax.set_title("Ablation: 드로다운 경로 비교",fontsize=14,fontweight="bold")
    ax.set_ylabel("Drawdown (%)"); ax.grid(alpha=0.3); ax.legend(fontsize=8,loc="lower left")
    fig.tight_layout(); fig.savefig(FIG/"main_v2_daily_ablation_drawdown.png",dpi=130); plt.close(fig)
    print("\n저장: ablation_mdd_calmar.png, ablation_drawdown.png, csv")

if __name__ == "__main__":
    main()
