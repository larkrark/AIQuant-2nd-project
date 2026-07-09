"""
35_ablation_hsi_vs_lambda_monthly.py
HSI 방향 vs 변동성 기반 λ 기여 분리 — '월별 리밸런싱'(보고서 정본 실행방식) 버전.

34번(일별 리밸런싱)의 정본화: 월말 비중 w_t 를 다음 달 월수익률 r_{t+1} 1개에 적용
(look-ahead 차단), 연율화 12, turnover=0.5·Σ|Δw_월|.

주의: 정본 monthly_returns.csv(2012~)가 현재 커밋에 없어 월수익률은 일별가격
(korea_etf_price_clean.csv, 2014-03~)에서 복원 → 실효 구간 2014-04~2026-06.
state5 신호 자체는 2012-03~2026-06(172개월)이나 수익률 가용구간으로 제한됨.

Arm: A EW / B FixedBM / C HSI+λ0.3(HSI만) / D HSI+λ0.1 / E VolOnly(HSI×) / F dynamic_v1
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
TAB = ROOT/"output"/"tables"; FIG = ROOT/"output"/"figures"; PROC = ROOT/"data"/"processed"
FIG.mkdir(parents=True, exist_ok=True)
ASSETS = ["069500","114260","153130"]; WCOLS = [f"{a}_weight" for a in ASSETS]; MPY = 12

c = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if Path(c).exists():
    font_manager.fontManager.addfont(c); plt.rcParams["font.family"] = font_manager.FontProperties(fname=c).get_name()
plt.rcParams["axes.unicode_minus"] = False

DEF_W = [0.20,0.45,0.35]; BASE_W = [0.70,0.20,0.10]

def apply_lambda(df, lam):
    df = df.sort_values("Date").reset_index(drop=True); tg = df[WCOLS].to_numpy(float); n = len(df)
    la = np.full(n, float(lam)) if np.isscalar(lam) else np.asarray(lam, float)
    out = np.empty_like(tg); prev = tg[0].copy()
    for i in range(n):
        out[i] = prev if i == 0 else prev + la[i]*(tg[i]-prev); prev = out[i]
    r = df.copy(); r[WCOLS] = out; return r

def rz(s, w): return (s - s.rolling(w, min_periods=max(3,w//3)).mean())/s.rolling(w, min_periods=max(3,w//3)).std(ddof=1)

def monthly_returns():
    px = pd.read_csv(PROC/"korea_etf_price_clean.csv", index_col=0, parse_dates=True)[ASSETS].dropna().sort_index()
    m = (1+px.pct_change()).resample("ME").prod()-1
    m = m.dropna(); m.index.name = "Date"; return m

def load_state5():
    d = pd.read_csv(TAB/"main_v2_hsi_state5_table_rank.csv"); d["Date"] = pd.to_datetime(d["Date"])
    return d.sort_values("Date").reset_index(drop=True)

def flags(state5, mret):
    s = state5.copy(); s["p"] = s["Date"].dt.to_period("M")
    mm = mret.copy(); mm["p"] = mm.index.to_period("M")
    j = s.merge(mm[["p","069500"]], on="p", how="left")
    r = pd.to_numeric(j["069500"], errors="coerce").fillna(0.0)
    ann = r.rolling(12, min_periods=6).std(ddof=1)*np.sqrt(12); vz = rz(ann,36).to_numpy()
    idx = (1+r).cumprod(); dd = (idx/idx.rolling(12, min_periods=1).max()-1).to_numpy()
    mom = (1+r).rolling(12, min_periods=6).apply(np.prod, raw=True)-1; mz = rz(mom,36).to_numpy()
    return vz, dd, mz

def dyn_lambda(state5, vz, dd, mz):
    st = state5["hsi_state5"].to_numpy(); n = len(st); per = np.zeros(n,int); cc = 0
    for i,v in enumerate(st):
        cc = cc+1 if v == "risk_relief" else 0; per[i] = cc
    hr = (vz>1.0)|(dd<-0.10); es = (per>=3)&(vz<0)&(mz>0)
    lam = np.full(n,0.3); lam[es] = 0.5; lam[hr] = 0.1; return lam

def const_w(s5, w):
    o = s5[["Date"]].copy()
    for a,wv in zip(ASSETS,w): o[f"{a}_weight"] = wv
    return o

def volonly_w(s5, vz, dd):
    dfn = (vz>1.0)|(dd<-0.10); o = s5[["Date"]].copy()
    for k,a in enumerate(ASSETS): o[f"{a}_weight"] = np.where(dfn, DEF_W[k], BASE_W[k])
    return o

def bt_monthly(mw, mret):
    """월말 비중 w_t → 다음 달 r_{t+1}. turnover=0.5·Σ|Δw_월|."""
    w = mw.copy(); w["ret_p"] = w["Date"].dt.to_period("M")+1
    r = mret.reset_index(); r["ret_p"] = r["Date"].dt.to_period("M")
    j = w.merge(r[["ret_p"]+ASSETS], on="ret_p", how="inner").sort_values("Date").reset_index(drop=True)
    W = j[WCOLS].to_numpy(); R = j[ASSETS].to_numpy()
    sret = (W*R).sum(axis=1)
    turn = np.zeros(len(W)); turn[1:] = 0.5*np.abs(W[1:]-W[:-1]).sum(axis=1)
    cum = np.cumprod(1+sret); dd = cum/np.maximum.accumulate(cum)-1
    return pd.DataFrame({"Date": j["Date"].values, "ret": sret, "cum": cum, "dd": dd, "turn": turn})

def met(ts):
    r = ts["ret"]; n = len(r); cum = float(ts["cum"].iloc[-1]); cagr = cum**(MPY/n)-1
    vol = r.std(ddof=1)*np.sqrt(MPY); mdd = float(ts["dd"].min())
    return {"months": n, "CAGR_pct": cagr*100, "MDD_pct": mdd*100,
            "Sharpe": (r.mean()*MPY)/vol if vol>0 else np.nan,
            "Calmar": cagr/abs(mdd) if mdd<0 else np.nan,
            "avg_turnover_pct": ts["turn"].mean()*100, "total_turnover_pct": ts["turn"].sum()*100}

def main():
    mret = monthly_returns(); s5 = load_state5(); vz,dd,mz = flags(s5, mret)
    lam_dyn = dyn_lambda(s5, vz, dd, mz); sw = s5[["Date"]+WCOLS].copy()
    print(f"월수익률 구간: {mret.index.min().date()} ~ {mret.index.max().date()} ({len(mret)}개월)")
    arms = {
        "A. EW (HSI×,방어×)": const_w(s5,[1/3]*3),
        "B. FixedBM 70/20/10 (HSI×,방어×)": const_w(s5,BASE_W),
        "C. HSI + λ0.3 (HSI만)": apply_lambda(sw,0.3),
        "D. HSI + λ0.1 (HSI만,느린)": apply_lambda(sw,0.1),
        "E. VolOnly de-risk + λ0.3 (HSI×,vol방어O)": apply_lambda(volonly_w(s5,vz,dd),0.3),
        "F. dynamic_v1 = HSI + 동적λ (풀)": apply_lambda(sw,lam_dyn),
    }
    rows = {}; out = []
    for n,mw in arms.items():
        ts = bt_monthly(mw, mret); rows[n] = ts; out.append({"arm": n, **met(ts)})
    df = pd.DataFrame(out); df.to_csv(TAB/"main_v2_monthly_ablation_hsi_vs_lambda.csv", index=False, encoding="utf-8-sig")
    print(df.round(3).to_string(index=False))
    def g(n,k): return df[df.arm==n][k].iloc[0]
    C="C. HSI + λ0.3 (HSI만)"; E="E. VolOnly de-risk + λ0.3 (HSI×,vol방어O)"; F="F. dynamic_v1 = HSI + 동적λ (풀)"
    print("\n[분해 · MDD]")
    print(f"  vol방어만(E)={g(E,'MDD_pct'):.2f}%  HSI만(C)={g(C,'MDD_pct'):.2f}%  풀(F)={g(F,'MDD_pct'):.2f}%")
    print(f"  HSI 추가기여 F−E = {g(F,'MDD_pct')-g(E,'MDD_pct'):+.2f}%p | 동적λ 추가기여 F−C = {g(F,'MDD_pct')-g(C,'MDD_pct'):+.2f}%p")

    names = list(arms.keys()); short = [n.split(".")[0] for n in names]
    pal = ["#888","#000","#1f77b4","#17becf","#d62728","#9467bd"]
    fig,(a1,a2)=plt.subplots(1,2,figsize=(14,5.6))
    for ax,col,ttl,fmt in [(a1,"MDD_pct","|MDD| (%) — 낮을수록 방어",'%.1f'),(a2,"Calmar","Calmar — 높을수록 우수",'%.2f')]:
        vals=[abs(g(n,col)) if col=="MDD_pct" else g(n,col) for n in names]
        b=ax.bar(range(len(names)),vals,color=pal); ax.bar_label(b,fmt=fmt,fontsize=9)
        ax.set_xticks(range(len(names))); ax.set_xticklabels(short,fontsize=11)
        ax.set_title(ttl,fontsize=12,fontweight="bold"); ax.grid(alpha=0.3,axis="y")
    fig.suptitle("Ablation(월별 리밸런싱): HSI 방향 vs 변동성 기반 λ 기여 분리",fontsize=13,fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG/"main_v2_monthly_ablation_mdd_calmar.png",dpi=130); plt.close(fig)
    print("저장: main_v2_monthly_ablation_mdd_calmar.png, csv")

if __name__ == "__main__":
    main()
