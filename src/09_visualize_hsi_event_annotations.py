from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# =========================
# 0. 기본 경로 설정
# =========================

ROOT_DIR = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT_DIR / "output" / "tables"
FIGURE_DIR = ROOT_DIR / "output" / "figures"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# 1. 한글 폰트 설정
# =========================

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# =========================
# 2. 데이터 불러오기
# =========================

def load_monthly_wave_summary() -> pd.DataFrame:
    """
    월별 P파/S파, 혼합충격, 상태 점수 요약표를 불러온다.
    """
    path = TABLE_DIR / "monthly_wave_market_summary.csv"

    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    df = pd.read_csv(path)

    if "Month" not in df.columns:
        raise ValueError("monthly_wave_market_summary.csv 안에 Month 컬럼이 필요합니다.")

    df["Date"] = pd.to_datetime(df["Month"].astype(str) + "-01")

    numeric_cols = [
        "p_wave_avg",
        "s_wave_avg",
        "two_sided_shock_ratio_avg",
        "vol_spike_share",
        "high_vol_mixed_share",
        "risk_score_avg",
        "overheat_score_avg",
        "recovery_score_avg",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values("Date")


def load_event_windows() -> list[dict]:
    """
    사건별 HSI 해석 요약표에서 사건 구간을 불러온다.
    파일이 없거나 필요한 컬럼이 없으면 기본 사건 구간을 사용한다.
    """
    path = TABLE_DIR / "event_hsi_interpretation_summary.csv"

    fallback_events = [
        {
            "name": "COVID crash",
            "market": "US/KR",
            "event_type": "Risk Crisis",
            "start": "2020-02",
            "end": "2020-03",
        },
        {
            "name": "COVID liquidity rebound",
            "market": "US",
            "event_type": "Recovery and Overheating",
            "start": "2020-03",
            "end": "2021-12",
        },
        {
            "name": "Inflation and rate-hike shock",
            "market": "US",
            "event_type": "Risk Worsening",
            "start": "2022-01",
            "end": "2022-10",
        },
        {
            "name": "Battery-theme overheating",
            "market": "KR",
            "event_type": "Overheating",
            "start": "2023-04",
            "end": "2023-08",
        },
        {
            "name": "Global tech and carry-trade shock",
            "market": "KR",
            "event_type": "Risk Crisis",
            "start": "2024-08",
            "end": "2024-08",
        },
    ]

    if not path.exists():
        print("[주의] event_hsi_interpretation_summary.csv가 없어 기본 사건 구간을 사용합니다.")
        return fallback_events

    df = pd.read_csv(path)

    required_cols = {"EventName", "StartMonth", "EndMonth"}
    if not required_cols.issubset(df.columns):
        print("[주의] 사건 요약표에 필요한 컬럼이 없어 기본 사건 구간을 사용합니다.")
        return fallback_events

    events = []

    for _, row in df.iterrows():
        events.append(
            {
                "name": str(row.get("EventName", "")),
                "market": str(row.get("Market", "")),
                "event_type": str(row.get("EventType", "")),
                "start": str(row.get("StartMonth", "")),
                "end": str(row.get("EndMonth", "")),
            }
        )

    # 같은 사건명이 중복될 수 있어, 사건명+기간 기준으로 중복 제거
    unique_events = []
    seen = set()

    for event in events:
        key = (event["name"], event["start"], event["end"])
        if key not in seen:
            unique_events.append(event)
            seen.add(key)

    return unique_events


# =========================
# 3. 사건 구간 표시 함수
# =========================

def get_event_color(event_type: str) -> str:
    """
    사건 성격에 따라 배경색을 선택한다.
    """
    event_type_lower = event_type.lower()

    if "risk" in event_type_lower or "crisis" in event_type_lower:
        return "mistyrose"

    if "recovery" in event_type_lower:
        return "honeydew"

    if "overheat" in event_type_lower:
        return "moccasin"

    return "lightgray"


def short_event_label(name: str) -> str:
    """
    그래프에 표시할 짧은 사건명 라벨을 만든다.
    """
    mapping = {
        "COVID crash": "COVID\ncrash",
        "COVID liquidity rebound": "COVID\nrebound",
        "Inflation and rate-hike shock": "Rate hike\nshock",
        "Battery-theme overheating": "Battery\noverheat",
        "Global tech and carry-trade shock": "Carry-trade\nshock",
    }

    return mapping.get(name, name[:12])


def add_event_backgrounds(ax, events: list[dict]) -> None:
    """
    그래프에 사건 구간 배경색과 라벨을 추가한다.
    """
    for event in events:
        start = event.get("start", "")
        end = event.get("end", "")

        if not start or not end or start == "nan" or end == "nan":
            continue

        start_date = pd.to_datetime(start + "-01")
        end_date = pd.to_datetime(end + "-01") + pd.offsets.MonthEnd(0)

        color = get_event_color(event.get("event_type", ""))
        label = short_event_label(event.get("name", ""))

        ax.axvspan(
            start_date,
            end_date,
            color=color,
            alpha=0.35,
            zorder=0,
        )

        ax.text(
            start_date,
            0.98,
            label,
            transform=ax.get_xaxis_transform(),
            fontsize=8,
            va="top",
            ha="left",
            rotation=90,
        )


def add_important_event_marker(ax, df: pd.DataFrame, target_month: str, y_col: str, label: str) -> None:
    """
    특정 월에 원형 마커와 주석을 추가한다.
    """
    target_date = pd.to_datetime(target_month + "-01")
    row = df[df["Date"] == target_date]

    if row.empty or y_col not in df.columns:
        return

    y_value = row[y_col].iloc[0]

    ax.scatter(
        target_date,
        y_value,
        s=120,
        facecolors="none",
        edgecolors="red",
        linewidths=2,
        zorder=5,
    )

    ax.annotate(
        label,
        xy=(target_date, y_value),
        xytext=(target_date, y_value * 1.10 if y_value != 0 else 0.5),
        arrowprops=dict(arrowstyle="->", color="red", linewidth=1),
        fontsize=9,
        color="red",
    )


# =========================
# 4. 그림 생성 함수
# =========================

def save_p_s_wave_with_events(df: pd.DataFrame, events: list[dict]) -> None:
    """
    P파/S파 사건 압력에 사건 구간을 표시한 그림을 저장한다.
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    add_event_backgrounds(ax, events)

    ax.plot(df["Date"], df["p_wave_avg"], label="P-wave: medium event pressure")
    ax.plot(df["Date"], df["s_wave_avg"], label="S-wave: large event pressure")

    add_important_event_marker(
        ax=ax,
        df=df,
        target_month="2024-08",
        y_col="s_wave_avg",
        label="2024-08\nshock",
    )

    ax.set_title("P파/S파 사건 압력과 주요 사건 구간")
    ax.set_xlabel("월")
    ax.set_ylabel("평균 사건 압력")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()

    output_path = FIGURE_DIR / "fig13_p_s_wave_with_event_annotations.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    print(f"[저장] {output_path}")


def save_state_score_with_events(df: pd.DataFrame, events: list[dict]) -> None:
    """
    위험악화, 과열, 회복 점수에 사건 구간을 표시한 그림을 저장한다.
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    add_event_backgrounds(ax, events)

    if "risk_score_avg" in df.columns:
        ax.plot(df["Date"], df["risk_score_avg"], label="Risk worsening score")

    if "overheat_score_avg" in df.columns:
        ax.plot(df["Date"], df["overheat_score_avg"], label="Overheating score")

    if "recovery_score_avg" in df.columns:
        ax.plot(df["Date"], df["recovery_score_avg"], label="Recovery score")

    add_important_event_marker(
        ax=ax,
        df=df,
        target_month="2024-08",
        y_col="risk_score_avg",
        label="2024-08\nrisk spike",
    )

    ax.set_title("HSI 상태 점수와 주요 사건 구간")
    ax.set_xlabel("월")
    ax.set_ylabel("평균 상태 점수")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()

    output_path = FIGURE_DIR / "fig14_hsi_state_score_with_event_annotations.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    print(f"[저장] {output_path}")


def save_mixed_zone_with_events(df: pd.DataFrame, events: list[dict]) -> None:
    """
    양방향 충격과 고변동성 혼합구간에 사건 구간을 표시한 그림을 저장한다.
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    add_event_backgrounds(ax, events)

    if "two_sided_shock_ratio_avg" in df.columns:
        ax.plot(
            df["Date"],
            df["two_sided_shock_ratio_avg"],
            label="Two-sided shock ratio",
        )

    if "high_vol_mixed_share" in df.columns:
        ax.plot(
            df["Date"],
            df["high_vol_mixed_share"],
            label="High-vol mixed zone share",
        )

    add_important_event_marker(
        ax=ax,
        df=df,
        target_month="2024-08",
        y_col="high_vol_mixed_share",
        label="2024-08\nmixed zone",
    )

    ax.set_title("양방향 충격과 고변동성 혼합구간")
    ax.set_xlabel("월")
    ax.set_ylabel("비율")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()

    output_path = FIGURE_DIR / "fig15_mixed_zone_with_event_annotations.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    print(f"[저장] {output_path}")


# =========================
# 5. 실행
# =========================

def main() -> None:
    print("[시작] 사건 구간 표시 시각화 생성")

    df = load_monthly_wave_summary()
    events = load_event_windows()

    print(f"- 월별 요약 rows: {len(df)}")
    print(f"- 사건 구간 수: {len(events)}")

    save_p_s_wave_with_events(df, events)
    save_state_score_with_events(df, events)
    save_mixed_zone_with_events(df, events)

    print("[완료] 사건 구간 표시 시각화 생성 종료")


if __name__ == "__main__":
    main()