from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import final_project_config as cfg


"""
37b_plot_cagr_gap_attribution.py

37번 스크립트 산출물을 읽어 보고서용 그림 2개를 생성한다.
- 그림 A: 월별 exposure/timing effect 누적 기여도 (FULL 구간)
- 그림 B: 구간별(FULL/IS/OOS) exposure vs timing effect 비교 막대그래프

한글 폰트 설정은 프로젝트 기존 스크립트(예: 22번 fontfix 버전)의 설정을 
따르는 것을 권장한다. 여기서는 시스템 기본 한글 폰트를 시도하되,
실패 시 경고만 출력하고 계속 진행한다.
"""


MONTHLY_CSV = cfg.TABLE_DIR / "main_final_cagr_gap_attribution_monthly.csv"
SUMMARY_CSV = cfg.TABLE_DIR / "main_final_cagr_gap_attribution_summary.csv"

FIG_CUMULATIVE = cfg.FIGURE_DIR / "main_final_cagr_gap_attribution_cumulative.png"
FIG_SUMMARY_BAR = cfg.FIGURE_DIR / "main_final_cagr_gap_attribution_period_summary.png"


def set_korean_font() -> None:
    candidates = ["Malgun Gothic", "NanumGothic", "AppleGothic"]
    for name in candidates:
        try:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False
            return
        except Exception:
            continue
    print("    경고: 한글 폰트를 찾지 못했습니다. 그림의 한글이 깨질 수 있습니다.")


def plot_cumulative(monthly: pd.DataFrame) -> None:
    full = monthly[monthly["period"] == "FULL"].copy()
    full["Date"] = pd.to_datetime(full["Date"])
    full = full.sort_values("Date")

    full["cum_exposure"] = full["exposure_effect"].cumsum() * 100
    full["cum_timing"] = full["timing_effect"].cumsum() * 100
    full["cum_excess"] = full["excess_return"].cumsum() * 100

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(full["Date"], full["cum_exposure"], label="Exposure Effect (누적)", color="#c0392b")
    ax.plot(full["Date"], full["cum_timing"], label="Timing Effect (누적)", color="#2980b9")
    ax.plot(full["Date"], full["cum_excess"], label="산술 초과수익 합 (누적)", color="#2c3e50", linestyle="--")
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_title("dynamic_v1 vs FixedBM_70_20_10 — 월별 초과수익 누적 분해 (FULL)")
    ax.set_xlabel("월")
    ax.set_ylabel("누적 산술초과수익 (%)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_CUMULATIVE, dpi=150)
    plt.close(fig)


def plot_period_summary(summary: pd.DataFrame) -> None:
    periods = summary["period"].tolist()
    exposure = summary["sum_exposure_effect_pct"].tolist()
    timing = summary["sum_timing_effect_pct"].tolist()

    x = range(len(periods))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar([i - width / 2 for i in x], exposure, width, label="Exposure Effect", color="#c0392b")
    ax.bar([i + width / 2 for i in x], timing, width, label="Timing Effect", color="#2980b9")
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(periods)
    ax.set_ylabel("산술 합산 기여도 (%p)")
    ax.set_title("구간별 Exposure Effect vs Timing Effect")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_SUMMARY_BAR, dpi=150)
    plt.close(fig)


def main() -> None:
    print("=" * 80)
    print("37b_plot_cagr_gap_attribution.py 실행 시작")
    print("=" * 80)

    set_korean_font()

    cfg.require_file(MONTHLY_CSV, label="월별 분해 결과")
    cfg.require_file(SUMMARY_CSV, label="구간별 요약 결과")

    monthly = pd.read_csv(MONTHLY_CSV)
    summary = pd.read_csv(SUMMARY_CSV)

    print("[1] 누적 기여도 그림 생성")
    plot_cumulative(monthly)
    print(f"    저장: {FIG_CUMULATIVE}")

    print("[2] 구간별 요약 막대그래프 생성")
    plot_period_summary(summary)
    print(f"    저장: {FIG_SUMMARY_BAR}")

    print("=" * 80)
    print("37b_plot_cagr_gap_attribution.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()