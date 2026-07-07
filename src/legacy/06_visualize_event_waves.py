from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


def configure_korean_font() -> str:
    candidates = [
        "Malgun Gothic",
        "맑은 고딕",
        "AppleGothic",
        "NanumGothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "Arial Unicode MS",
    ]
    available = {font.name for font in fm.fontManager.ttflist}
    selected = next((name for name in candidates if name in available), "DejaVu Sans")
    plt.rcParams["font.family"] = selected
    plt.rcParams["axes.unicode_minus"] = False
    return selected


configure_korean_font()

PROJECT_DIR = Path(__file__).resolve().parents[2]

LABEL_PATH = PROJECT_DIR / "output" / "tables" / "monthly_hsi_state_labels.csv"
OUTPUT_TABLE_DIR = PROJECT_DIR / "output" / "tables"
OUTPUT_FIGURE_DIR = PROJECT_DIR / "output" / "figures"

OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def load_labels(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"상태명 파일이 없습니다: {path}")

    df = pd.read_csv(path, encoding="utf-8-sig")
    df["Month"] = df["Month"].astype(str)
    df["Ticker"] = df["Ticker"].astype(str).str.zfill(6)

    if "MonthEndDate" in df.columns:
        df["MonthEndDate"] = pd.to_datetime(df["MonthEndDate"], errors="coerce")

    return df


def add_wave_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    for col in [
        "medium_up", "medium_down",
        "large_up", "large_down",
        "vol20", "vol60",
        "risk_score", "overheat_score", "recovery_score"
    ]:
        if col not in result.columns:
            result[col] = 0

    # P파: 큰 사건 전의 중간 강도 흔들림
    result["p_wave_count"] = result["medium_up"] + result["medium_down"]

    # S파: 실제 큰 사건
    result["s_wave_count"] = result["large_up"] + result["large_down"]

    # 상승 큰 사건과 하락 큰 사건의 동시성
    result["two_sided_large_count"] = result["large_up"] + result["large_down"]

    result["two_sided_shock_ratio"] = np.where(
        result["two_sided_large_count"] > 0,
        np.minimum(result["large_up"], result["large_down"]) / result["two_sided_large_count"],
        0
    )

    # 단기 변동성이 중기 변동성보다 큰지
    result["vol_spike"] = result["vol20"] > result["vol60"]

    # 고변동성 혼합구간:
    # 큰 상승과 큰 하락이 모두 있고, 단기 변동성이 중기 변동성보다 큰 경우
    result["high_vol_mixed_zone"] = (
        (result["large_up"] >= 1) &
        (result["large_down"] >= 1) &
        (result["vol_spike"])
    )

    # 보기 편한 숫자형 플래그
    result["vol_spike_flag"] = result["vol_spike"].astype(int)
    result["high_vol_mixed_flag"] = result["high_vol_mixed_zone"].astype(int)

    return result


def make_market_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df
        .groupby("Month")
        .agg(
            asset_count=("Ticker", "nunique"),
            p_wave_avg=("p_wave_count", "mean"),
            s_wave_avg=("s_wave_count", "mean"),
            large_up_avg=("large_up", "mean"),
            large_down_avg=("large_down", "mean"),
            two_sided_shock_ratio_avg=("two_sided_shock_ratio", "mean"),
            vol_spike_share=("vol_spike_flag", "mean"),
            high_vol_mixed_share=("high_vol_mixed_flag", "mean"),
            risk_score_avg=("risk_score", "mean"),
            overheat_score_avg=("overheat_score", "mean"),
            recovery_score_avg=("recovery_score", "mean"),
        )
        .reset_index()
    )

    summary["MonthDate"] = pd.to_datetime(summary["Month"] + "-01", errors="coerce")

    return summary


def save_csvs(wave_df: pd.DataFrame, market_summary: pd.DataFrame) -> None:
    wave_df.to_csv(
        OUTPUT_TABLE_DIR / "monthly_wave_features.csv",
        index=False,
        encoding="utf-8-sig"
    )

    market_summary.to_csv(
        OUTPUT_TABLE_DIR / "monthly_wave_market_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )


def plot_p_s_wave(market_summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(
        market_summary["MonthDate"],
        market_summary["p_wave_avg"],
        label="P-wave pressure: medium events"
    )
    ax.plot(
        market_summary["MonthDate"],
        market_summary["s_wave_avg"],
        label="S-wave pressure: large events"
    )

    ax.set_title("P-wave and S-wave event pressure over time")
    ax.set_xlabel("Month")
    ax.set_ylabel("Average monthly event count per ETF")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURE_DIR / "fig09_p_s_wave_event_pressure.png", dpi=160)
    plt.close(fig)


def plot_two_sided_shock(market_summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(
        market_summary["MonthDate"],
        market_summary["two_sided_shock_ratio_avg"],
        label="Two-sided shock ratio"
    )
    ax.plot(
        market_summary["MonthDate"],
        market_summary["high_vol_mixed_share"],
        label="High-volatility mixed-zone share"
    )

    ax.set_title("Two-sided shock and high-volatility mixed zones")
    ax.set_xlabel("Month")
    ax.set_ylabel("Ratio or share")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURE_DIR / "fig10_two_sided_shock_mixed_zone.png", dpi=160)
    plt.close(fig)


def plot_risk_overheat_recovery(market_summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(
        market_summary["MonthDate"],
        market_summary["risk_score_avg"],
        label="Risk-worsening score"
    )
    ax.plot(
        market_summary["MonthDate"],
        market_summary["overheat_score_avg"],
        label="Overheating score"
    )
    ax.plot(
        market_summary["MonthDate"],
        market_summary["recovery_score_avg"],
        label="Recovery score"
    )

    ax.set_title("Average HSI state scores over time")
    ax.set_xlabel("Month")
    ax.set_ylabel("Average score per ETF")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURE_DIR / "fig11_hsi_state_score_trend.png", dpi=160)
    plt.close(fig)


def plot_state_distribution(wave_df: pd.DataFrame) -> None:
    if "HSIStateLabel" not in wave_df.columns:
        return

    counts = (
        wave_df["HSIStateLabel"]
        .value_counts()
        .sort_values(ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.barh(counts.index, counts.values)

    ax.set_title("Distribution of monthly HSI state labels")
    ax.set_xlabel("Count")
    ax.set_ylabel("HSI state label")

    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURE_DIR / "fig12_hsi_state_distribution.png", dpi=160)
    plt.close(fig)


def main() -> None:
    labels = load_labels(LABEL_PATH)
    wave_df = add_wave_features(labels)
    market_summary = make_market_summary(wave_df)

    save_csvs(wave_df, market_summary)

    plot_p_s_wave(market_summary)
    plot_two_sided_shock(market_summary)
    plot_risk_overheat_recovery(market_summary)
    plot_state_distribution(wave_df)

    print("[완료] P파/S파 및 고변동성 혼합구간 시각화")
    print()
    print("[생성 표]")
    print(f"- {OUTPUT_TABLE_DIR / 'monthly_wave_features.csv'}")
    print(f"- {OUTPUT_TABLE_DIR / 'monthly_wave_market_summary.csv'}")
    print()
    print("[생성 그림]")
    print(f"- {OUTPUT_FIGURE_DIR / 'fig09_p_s_wave_event_pressure.png'}")
    print(f"- {OUTPUT_FIGURE_DIR / 'fig10_two_sided_shock_mixed_zone.png'}")
    print(f"- {OUTPUT_FIGURE_DIR / 'fig11_hsi_state_score_trend.png'}")
    print(f"- {OUTPUT_FIGURE_DIR / 'fig12_hsi_state_distribution.png'}")
    print()
    print("[최근 10개월 시장 요약]")
    show_cols = [
        "Month",
        "p_wave_avg",
        "s_wave_avg",
        "two_sided_shock_ratio_avg",
        "vol_spike_share",
        "high_vol_mixed_share",
        "risk_score_avg",
        "overheat_score_avg",
        "recovery_score_avg"
    ]
    print(market_summary[show_cols].tail(10).to_string(index=False))


if __name__ == "__main__":
    main()
