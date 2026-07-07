"""HSI 모래시계 개념 검증 시각화.

risk / overheat / recovery 점수를 3극(pole) 벡터로 변환해
월별 상태 벡터가 실제로 모래시계(상·하 원뿔) 안에 모이는지 확인한다.

- 극 배치: 위험(아래, 270도), 회복(왼쪽 위, 150도), 과열(오른쪽 위, 30도)
- 월별 벡터 v = risk*u_risk + overheat*u_overheat + recovery*u_recovery
- 왼쪽 패널: 전체 기간 벡터(회색) + COVID crash 구간(2019-12~2020-12) 강조
- 오른쪽 패널: COVID 구간 3개 점수 시계열

실행: python src/24_visualize_hsi_vector_hourglass_covid.py
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, Polygon


PROJECT_DIR = Path(__file__).resolve().parents[1]
LABEL_PATH = PROJECT_DIR / "output" / "tables" / "monthly_hsi_state_labels.csv"
OUTPUT_FIGURE_DIR = PROJECT_DIR / "output" / "figures"
OUTPUT_TABLE_DIR = PROJECT_DIR / "output" / "tables"

TICKER = 69500
COVID_START, COVID_END = "2019-12", "2020-12"
CONE_HALF_ANGLE_DEG = 45.0

# 3극 단위벡터: 위험(아래), 회복(왼쪽 위), 과열(오른쪽 위)
U_RISK = np.array([0.0, -1.0])
U_RECOVERY = np.array([-math.sin(math.radians(60)), math.cos(math.radians(60))])
U_OVERHEAT = np.array([math.sin(math.radians(60)), math.cos(math.radians(60))])

PHASE_COLORS = {
    "crash": "#e33b2f",
    "neutral": "#9aa3ad",
    "recovery": "#2e9e5b",
    "overheat": "#e88a1a",
}


def configure_korean_font() -> None:
    candidates = [
        "Malgun Gothic", "맑은 고딕", "AppleGothic", "NanumGothic",
        "Noto Sans CJK KR", "Noto Sans KR", "Noto Sans CJK JP",
    ]
    available = {font.name for font in fm.fontManager.ttflist}
    selected = next((name for name in candidates if name in available), None)
    if selected is None:
        selected = next((n for n in sorted(available) if "CJK" in n), "DejaVu Sans")
    plt.rcParams["font.family"] = selected
    plt.rcParams["axes.unicode_minus"] = False


def phase_of(state: str) -> str:
    if "위험" in state:
        return "crash"
    if "과열" in state:
        return "overheat"
    if "회복" in state:
        return "recovery"
    return "neutral"


def build_vectors(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    vec = (
        out["risk_score"].to_numpy()[:, None] * U_RISK
        + out["overheat_score"].to_numpy()[:, None] * U_OVERHEAT
        + out["recovery_score"].to_numpy()[:, None] * U_RECOVERY
    )
    out["vx"], out["vy"] = vec[:, 0], vec[:, 1]
    out["magnitude"] = np.hypot(out["vx"], out["vy"])
    # 수직축(위/아래)에서 벗어난 각도. 0 = 완전한 수직, 90 = 완전한 수평
    with np.errstate(invalid="ignore", divide="ignore"):
        out["off_vertical_deg"] = np.degrees(np.arctan2(np.abs(out["vx"]), np.abs(out["vy"])))
    out["in_cone"] = out["off_vertical_deg"] <= CONE_HALF_ANGLE_DEG
    out["phase"] = out["HSIStateLabel"].astype(str).map(phase_of)
    return out


def draw_cones(ax: plt.Axes, radius: float) -> None:
    half = math.radians(CONE_HALF_ANGLE_DEG)
    for sign in (1, -1):
        pts = [(0, 0)]
        for a in np.linspace(-half, half, 40):
            pts.append((radius * math.sin(a), sign * radius * math.cos(a)))
        ax.add_patch(Polygon(pts, closed=True, facecolor="#eef5ff" if sign > 0 else "#fff0ec",
                             edgecolor="#b8cdea" if sign > 0 else "#eec5bb", lw=1.0, zorder=0))
    ax.text(0, radius * 1.04, "과열·회복 (상단 원뿔)", ha="center", fontsize=10, color="#0b2a5b")
    ax.text(0, -radius * 1.09, "위험 악화 (하단 원뿔)", ha="center", fontsize=10, color="#8a2216")


def main() -> None:
    configure_korean_font()

    df = pd.read_csv(LABEL_PATH)
    df = df[df["Ticker"] == TICKER].copy()
    df["Month"] = df["Month"].astype(str)
    df = df.dropna(subset=["risk_score", "overheat_score", "recovery_score"]).reset_index(drop=True)

    vec = build_vectors(df)
    covid = vec[vec["Month"].between(COVID_START, COVID_END)].reset_index(drop=True)

    active = vec[vec["magnitude"] > 0]
    in_cone_pct = active["in_cone"].mean() * 100
    covid_active = covid[covid["magnitude"] > 0]
    covid_in_cone_pct = covid_active["in_cone"].mean() * 100

    radius = float(vec["magnitude"].max()) * 1.08

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(15.5, 8.2), gridspec_kw={"width_ratios": [1.15, 1.0]}
    )

    # ---------- 왼쪽: 벡터 평면 (모래시계 검증) ----------
    draw_cones(ax1, radius)

    for _, r in vec.iterrows():
        if r["magnitude"] == 0 or r["Month"] in set(covid["Month"]):
            continue
        ax1.plot([0, r["vx"]], [0, r["vy"]], color="#c3c7cd", lw=0.8, alpha=0.55, zorder=1)

    for _, r in covid.iterrows():
        if r["magnitude"] == 0:
            continue
        color = PHASE_COLORS[r["phase"]]
        ax1.add_patch(FancyArrowPatch((0, 0), (r["vx"], r["vy"]),
                                      arrowstyle="-|>", mutation_scale=16,
                                      color=color, lw=2.0, zorder=3))
        ax1.annotate(r["Month"][2:], (r["vx"], r["vy"]),
                     textcoords="offset points", xytext=(5, 4),
                     fontsize=8.5, color=color, fontweight="bold", zorder=4)

    # COVID 궤적(시간 순 연결)
    cc = covid[covid["magnitude"] > 0]
    ax1.plot(cc["vx"], cc["vy"], color="#5c6672", lw=0.9, ls="--", alpha=0.7, zorder=2)

    ax1.axhline(0, color="#9aa3ad", lw=0.8)
    ax1.axvline(0, color="#dfe3e8", lw=0.6)
    ax1.set_xlim(-radius * 1.15, radius * 1.15)
    ax1.set_ylim(-radius * 1.2, radius * 1.18)
    ax1.set_aspect("equal")
    ax1.set_title(
        f"HSI 상태 벡터 평면 — 모래시계 형태 검증\n"
        f"원뿔(수직 ±{CONE_HALF_ANGLE_DEG:.0f}°) 안 비율: 전체 {in_cone_pct:.0f}% / COVID 구간 {covid_in_cone_pct:.0f}%",
        fontsize=12,
    )
    ax1.set_xlabel("← 회복 성향        과열 성향 →", fontsize=10)
    ax1.set_ylabel("← 위험 악화        완화/상승 →", fontsize=10)

    handles = [plt.Line2D([0], [0], color=c, lw=2.4) for c in PHASE_COLORS.values()]
    ax1.legend(handles, ["위험 악화(crash)", "중립/혼조", "회복", "과열"],
               loc="lower left", fontsize=9, framealpha=0.9)

    # ---------- 오른쪽: COVID 구간 점수 시계열 ----------
    x = np.arange(len(covid))
    width = 0.28
    ax2.bar(x - width, covid["risk_score"], width, label="risk", color=PHASE_COLORS["crash"], alpha=0.85)
    ax2.bar(x, covid["overheat_score"], width, label="overheat", color=PHASE_COLORS["overheat"], alpha=0.85)
    ax2.bar(x + width, covid["recovery_score"], width, label="recovery", color=PHASE_COLORS["recovery"], alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels([m[2:] for m in covid["Month"]], rotation=45, fontsize=9)
    ax2.set_ylabel("점수")
    ax2.set_title("COVID crash 구간 3개 점수 추이 (069500)", fontsize=12)
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", color="#eceff3", lw=0.8)
    ax2.set_axisbelow(True)

    for i, (_, r) in enumerate(covid.iterrows()):
        ax2.annotate(str(r["HSIStateLabel"]), (x[i], max(r["risk_score"], r["overheat_score"], r["recovery_score"]) + 0.15),
                     ha="center", fontsize=7, rotation=90, color="#5c6672")

    fig.suptitle("HSI 개념도 검증 — risk/overheat/recovery 벡터화와 COVID crash 궤적", fontsize=14, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.965])

    OUTPUT_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    fig_path = OUTPUT_FIGURE_DIR / "fig17_hsi_vector_hourglass_covid.png"
    fig.savefig(fig_path, dpi=150)

    table_path = OUTPUT_TABLE_DIR / "fig17_hsi_vector_hourglass_covid_vectors.csv"
    vec[["Month", "risk_score", "overheat_score", "recovery_score",
         "vx", "vy", "magnitude", "off_vertical_deg", "in_cone", "phase", "HSIStateLabel"]].to_csv(
        table_path, index=False, encoding="utf-8-sig")

    print(f"[저장] {fig_path}")
    print(f"[저장] {table_path}")
    print(f"원뿔 안 비율: 전체 {in_cone_pct:.1f}% ({int(active['in_cone'].sum())}/{len(active)}), "
          f"COVID {covid_in_cone_pct:.1f}% ({int(covid_active['in_cone'].sum())}/{len(covid_active)})")


if __name__ == "__main__":
    main()
