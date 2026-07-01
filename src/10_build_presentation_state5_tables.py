from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SOURCE_TABLE_DIR = PROJECT_DIR / "output" / "tables"
EVENT_CALENDAR_PATH = PROJECT_DIR / "data" / "reference" / "event_calendar_us_kr.csv"

PRESENTATION_VERSION = "20260630_state5_midterm"
OUTPUT_DIR = PROJECT_DIR / "output" / "presentation" / PRESENTATION_VERSION / "tables"
OUTPUT_FIGURE_DIR = PROJECT_DIR / "output" / "presentation" / PRESENTATION_VERSION / "figures"

STATE5_ORDER = [
    "accident_zone",
    "risk_warning",
    "conflict",
    "neutral_watch",
    "risk_relief",
]

STATE5_LABELS_KR = {
    "risk_relief": "위험 완화 우세",
    "neutral_watch": "관찰·중립",
    "conflict": "충돌 상태",
    "risk_warning": "위험 악화 우세",
    "accident_zone": "강한 위험 악화",
}


def read_source_csv(filename: str) -> pd.DataFrame:
    path = SOURCE_TABLE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"입력 파일이 없습니다: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig")
    if df.empty:
        raise ValueError(f"입력 파일이 비어 있습니다: {path}")
    return df


def derive_state5(row: pd.Series) -> str:
    risk_score = row.get("risk_score", 0)
    overheat_score = row.get("overheat_score", 0)
    recovery_score = row.get("recovery_score", 0)
    large_down = row.get("large_down", 0)

    if risk_score >= 5 and large_down >= 2:
        return "accident_zone"
    if risk_score >= 4 and risk_score >= recovery_score + 2:
        return "risk_warning"
    if risk_score >= 3 and (overheat_score >= 3 or recovery_score >= 3):
        return "conflict"
    if overheat_score >= 4:
        return "conflict" if risk_score >= 2 else "neutral_watch"
    if recovery_score >= 3 and risk_score <= 2:
        return "risk_relief"
    return "neutral_watch"


def summarize_state(df: pd.DataFrame, state_col: str = "HSIState5") -> pd.DataFrame:
    summary = df[state_col].value_counts().reindex(STATE5_ORDER, fill_value=0).reset_index()
    summary.columns = [state_col, "Count"]
    total = summary["Count"].sum()
    summary["Share"] = summary["Count"] / total if total else 0
    summary["StateLabelKR"] = summary[state_col].map(STATE5_LABELS_KR)
    return summary


def split_design_validation(labels: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    temp = labels.copy()
    temp["Month"] = temp["Month"].astype(str).str.slice(0, 7)
    design = temp[(temp["Month"] >= "2014-03") & (temp["Month"] <= "2022-12")].copy()
    validation = temp[(temp["Month"] >= "2023-01") & (temp["Month"] <= "2026-06")].copy()
    return design, validation


def summarize_design_validation(labels: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period_name, period_df in zip(["design", "validation"], split_design_validation(labels)):
        summary = summarize_state(period_df)
        summary.insert(0, "Period", period_name)
        rows.append(summary)
    return pd.concat(rows, ignore_index=True)


def month_range_mask(labels: pd.DataFrame, start: str, end: str) -> pd.Series:
    month = labels["Month"].astype(str).str.slice(0, 7)
    start_month = str(start)[:7]
    end_month = str(end)[:7]
    return (month >= start_month) & (month <= end_month)


def subject_particle(text: str) -> str:
    if not text:
        return "가"
    code = ord(text[-1])
    if 0xAC00 <= code <= 0xD7A3:
        return "이" if (code - 0xAC00) % 28 else "가"
    return "이"


def build_event_distribution(labels: pd.DataFrame) -> pd.DataFrame:
    if not EVENT_CALENDAR_PATH.exists():
        raise FileNotFoundError(f"사건 달력 파일이 없습니다: {EVENT_CALENDAR_PATH}")

    calendar = pd.read_csv(EVENT_CALENDAR_PATH, encoding="utf-8-sig")
    rows = []

    for _, event in calendar.iterrows():
        start = str(event.get("StartDate", ""))[:7]
        end = str(event.get("EndDate", ""))[:7]
        sub = labels[month_range_mask(labels, start, end)].copy()
        if sub.empty:
            continue

        counts = sub["HSIState5"].value_counts().reindex(STATE5_ORDER, fill_value=0)
        total = counts.sum()

        for state, count in counts.items():
            if count == 0:
                continue
            rows.append(
                {
                    "Market": event.get("Market", ""),
                    "EventName": event.get("EventName", ""),
                    "EventType": event.get("EventType", ""),
                    "ExpectedHSIDirection": event.get("ExpectedHSIDirection", ""),
                    "StartMonth": start,
                    "EndMonth": end,
                    "HSIState5": state,
                    "StateLabelKR": STATE5_LABELS_KR[state],
                    "Count": int(count),
                    "Share": count / total if total else 0,
                }
            )

    return pd.DataFrame(rows)


def interpret_event(event_name: str, top_state: str, second_state: str) -> str:
    top_label = STATE5_LABELS_KR.get(top_state, top_state)
    second_label = STATE5_LABELS_KR.get(second_state, second_state)
    top_particle = subject_particle(top_label)

    if top_state in {"accident_zone", "risk_warning"}:
        return (
            f"{event_name} 구간에서는 {top_label}가 가장 많이 나타났다. "
            "이는 해당 사건 구간에서 HSI가 위험 악화 또는 강한 방어 전환 필요성을 포착했음을 의미한다."
        )
    if top_state == "conflict":
        return (
            f"{event_name} 구간에서는 {top_label}가 가장 많이 나타났다. "
            "위험 악화와 완화·과열 신호가 동시에 관측된 혼합 국면으로 해석하며, main_v2b 기준에서는 즉시 방어전환보다 관찰 상태로 둔다."
        )
    if top_state == "risk_relief":
        return (
            f"{event_name} 구간에서는 {top_label}가 가장 많이 나타났다. "
            "가격 기반 회복 신호가 우세했음을 뜻하지만, 외부 사건 달력은 전략 입력값이 아니라 사후 해석용 기준 구간이다."
        )
    return (
        f"{event_name} 구간에서는 {top_label}{top_particle} 가장 많이 나타났고, {second_label}도 함께 관측되었다. "
        "따라서 단일 방향으로 단정하기보다 관찰 구간으로 해석한다."
    )


def build_event_summary(event_distribution: pd.DataFrame) -> pd.DataFrame:
    if event_distribution.empty:
        return pd.DataFrame()

    group_cols = [
        "Market",
        "EventName",
        "EventType",
        "ExpectedHSIDirection",
        "StartMonth",
        "EndMonth",
    ]
    rows = []
    for keys, group in event_distribution.groupby(group_cols, dropna=False):
        group = group.sort_values("Share", ascending=False).reset_index(drop=True)
        top = group.iloc[0]
        second = group.iloc[1] if len(group) > 1 else None
        second_state = second["HSIState5"] if second is not None else ""

        market, event_name, event_type, expected_direction, start_month, end_month = keys
        rows.append(
            {
                "Market": market,
                "EventName": event_name,
                "EventType": event_type,
                "ExpectedHSIDirection": expected_direction,
                "StartMonth": start_month,
                "EndMonth": end_month,
                "TopState": top["HSIState5"],
                "TopStateLabelKR": top["StateLabelKR"],
                "TopStateShare": top["Share"],
                "SecondState": second_state,
                "SecondStateLabelKR": second["StateLabelKR"] if second is not None else "",
                "SecondStateShare": second["Share"] if second is not None else 0.0,
                "Interpretation": interpret_event(event_name, top["HSIState5"], second_state),
            }
        )

    return pd.DataFrame(rows)


def write_manifest(output_files: list[Path]) -> None:
    manifest_path = OUTPUT_DIR.parent / "README.md"
    lines = [
        f"# {PRESENTATION_VERSION}",
        "",
        "중간 발표용 HSI 5상태 파생 데이터입니다.",
        "",
        "- 원본 8상태 CSV는 `output/tables`에 그대로 둡니다.",
        "- 이 버전은 중간 정리 문서의 5상태 체계(`risk_relief`, `neutral_watch`, `conflict`, `risk_warning`, `accident_zone`)에 맞춘 표시용 데이터입니다.",
        "- 외부 사건 달력은 전략 입력값이 아니라 HSI 상태 산출 이후 사후 해석용 기준 구간입니다.",
        "",
        "## Files",
        "",
    ]
    lines.extend(f"- `tables/{path.name}`" for path in output_files)
    if OUTPUT_FIGURE_DIR.exists():
        lines.extend(["", "## Figures", ""])
        lines.extend(f"- `figures/{path.name}`" for path in sorted(OUTPUT_FIGURE_DIR.glob("*.png")))
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_state_distribution_figure(summary: pd.DataFrame) -> Path:
    OUTPUT_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    plot_df = summary.copy()
    plot_df["Display"] = plot_df["HSIState5"] + "\n" + plot_df["StateLabelKR"]
    plot_df["SharePct"] = plot_df["Share"] * 100

    colors = {
        "accident_zone": "#c2410c",
        "risk_warning": "#ef4444",
        "conflict": "#f59e0b",
        "neutral_watch": "#64748b",
        "risk_relief": "#0f766e",
    }

    fig, ax = plt.subplots(figsize=(10, 5.6))
    bars = ax.bar(
        plot_df["Display"],
        plot_df["Count"],
        color=[colors[state] for state in plot_df["HSIState5"]],
    )
    ax.set_title("HSI 5상태 분포 - 중간 발표용 파생 기준", fontsize=15, pad=16)
    ax.set_ylabel("관측치 수")
    ax.grid(axis="y", alpha=0.25)

    for bar, share in zip(bars, plot_df["SharePct"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{share:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    fig.tight_layout()
    output_path = OUTPUT_FIGURE_DIR / "fig12_hsi_state5_distribution.png"
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path


def save_hourglass_concept_figure() -> Path:
    OUTPUT_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    risk_color = "#c2410c"
    relief_color = "#0f766e"
    conflict_color = "#f59e0b"
    neutral_color = "#64748b"

    ax.fill([2.0, 5.0, 8.0], [8.6, 5.0, 8.6], color="#fee2e2", alpha=0.88, ec=risk_color, lw=2)
    ax.fill([2.0, 5.0, 8.0], [1.4, 5.0, 1.4], color="#dcfce7", alpha=0.88, ec=relief_color, lw=2)
    ax.plot([5, 5], [1.05, 8.95], color="#94a3b8", lw=1.4, ls="--")
    ax.plot([1.55, 8.45], [5, 5], color="#94a3b8", lw=1.4)
    ax.scatter([5], [5], s=130, color=neutral_color, zorder=5)

    ax.annotate("", xy=(5, 8.25), xytext=(5, 5.15), arrowprops=dict(arrowstyle="->", lw=3, color=risk_color))
    ax.annotate("", xy=(5, 1.75), xytext=(5, 4.85), arrowprops=dict(arrowstyle="->", lw=3, color=relief_color))
    ax.annotate("", xy=(7.05, 6.4), xytext=(5.2, 5.05), arrowprops=dict(arrowstyle="->", lw=2.6, color=conflict_color))
    ax.annotate("", xy=(2.95, 3.6), xytext=(4.8, 4.95), arrowprops=dict(arrowstyle="->", lw=2.6, color=conflict_color))

    ax.text(5, 9.35, "HSI 모래시계 개념도", ha="center", fontsize=22, fontweight="bold", color="#111827")
    ax.text(5, 8.9, "가격 기반 신호를 위험 악화 방향과 위험 완화 방향으로 나누어 해석", ha="center", fontsize=12, color="#475569")

    ax.text(5, 8.15, "위험 악화 신호 축적", ha="center", fontsize=15, fontweight="bold", color=risk_color)
    ax.text(5, 1.45, "위험 완화·회복 신호 축적", ha="center", fontsize=15, fontweight="bold", color=relief_color)
    ax.text(5.18, 5.25, "중립\n관찰", ha="left", va="bottom", fontsize=11, color="#111827")

    ax.text(8.35, 7.9, "accident_zone\n강한 위험 악화", ha="left", va="center", fontsize=12, color=risk_color, fontweight="bold")
    ax.text(8.35, 6.7, "risk_warning\n위험 악화 우세", ha="left", va="center", fontsize=12, color="#ef4444", fontweight="bold")
    ax.text(8.35, 5.05, "conflict\n양방향 신호 충돌", ha="left", va="center", fontsize=12, color=conflict_color, fontweight="bold")
    ax.text(8.35, 3.35, "neutral_watch\n관찰·중립", ha="left", va="center", fontsize=12, color=neutral_color, fontweight="bold")
    ax.text(8.35, 2.1, "risk_relief\n위험 완화 우세", ha="left", va="center", fontsize=12, color=relief_color, fontweight="bold")

    box = dict(boxstyle="round,pad=0.45", fc="#f8fafc", ec="#cbd5e1", lw=1.2)
    ax.text(0.7, 7.9, "입력 신호 예시", fontsize=13, fontweight="bold", color="#0f172a")
    ax.text(
        0.7,
        7.35,
        "수익률\n이동평균 이격도\n모멘텀\n변동성\n상대강도\n사건성 충격",
        fontsize=11,
        color="#334155",
        va="top",
        bbox=box,
    )
    ax.text(
        0.7,
        2.85,
        "방향 = 위험 악화/완화\n길이 = 신호 강도\n충돌 = 양방향 신호 공존",
        fontsize=11,
        color="#334155",
        va="top",
        bbox=box,
    )

    ax.text(
        5,
        0.35,
        "HSI는 매수·매도 명령이 아니라, ETF 위험자산 비중 조절을 돕는 시장상태 해석용 overlay 보조지표",
        ha="center",
        fontsize=12,
        color="#1f2937",
    )

    output_path = OUTPUT_FIGURE_DIR / "fig00_hsi_hourglass_concept.png"
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    labels = read_source_csv("monthly_hsi_state_labels.csv")
    labels["HSIStateLabelOriginal"] = labels["HSIStateLabel"]
    labels["HSIState5"] = labels.apply(derive_state5, axis=1)
    labels["StateLabelKR"] = labels["HSIState5"].map(STATE5_LABELS_KR)

    output_files = []

    state_labels_path = OUTPUT_DIR / "monthly_hsi_state_labels_state5.csv"
    labels.to_csv(state_labels_path, index=False, encoding="utf-8-sig")
    output_files.append(state_labels_path)

    state_summary = summarize_state(labels)
    state_summary_path = OUTPUT_DIR / "monthly_hsi_state_summary.csv"
    state_summary.to_csv(state_summary_path, index=False, encoding="utf-8-sig")
    output_files.append(state_summary_path)
    state_figure_path = save_state_distribution_figure(state_summary)
    hourglass_figure_path = save_hourglass_concept_figure()

    design_validation = summarize_design_validation(labels)
    design_validation_path = OUTPUT_DIR / "design_validation_state_summary.csv"
    design_validation.to_csv(design_validation_path, index=False, encoding="utf-8-sig")
    output_files.append(design_validation_path)

    event_distribution = build_event_distribution(labels)
    event_distribution_path = OUTPUT_DIR / "event_period_state_distribution.csv"
    event_distribution.to_csv(event_distribution_path, index=False, encoding="utf-8-sig")
    output_files.append(event_distribution_path)

    event_summary = build_event_summary(event_distribution)
    event_summary_path = OUTPUT_DIR / "event_hsi_interpretation_summary.csv"
    event_summary.to_csv(event_summary_path, index=False, encoding="utf-8-sig")
    output_files.append(event_summary_path)

    audit = (
        pd.crosstab(labels["HSIStateLabelOriginal"], labels["HSIState5"])
        .reindex(columns=STATE5_ORDER, fill_value=0)
        .reset_index()
    )
    audit_path = OUTPUT_DIR / "state5_mapping_audit.csv"
    audit.to_csv(audit_path, index=False, encoding="utf-8-sig")
    output_files.append(audit_path)

    write_manifest(output_files)

    print("[완료] 중간 발표용 HSI 5상태 데이터 생성")
    print(f"- 출력 디렉토리: {OUTPUT_DIR}")
    print(f"- 그림 디렉토리: {state_figure_path.parent}")
    print(f"- 개념도: {hourglass_figure_path.name}")
    print()
    print(state_summary.to_string(index=False))


if __name__ == "__main__":
    main()
