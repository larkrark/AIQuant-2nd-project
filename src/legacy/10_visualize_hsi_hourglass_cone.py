from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, Polygon, Rectangle


PROJECT_DIR = Path(__file__).resolve().parents[2]
LABEL_PATH = PROJECT_DIR / "output" / "tables" / "monthly_hsi_state_labels.csv"
OUTPUT_FIGURE_DIR = PROJECT_DIR / "output" / "figures"
OUTPUT_TABLE_DIR = PROJECT_DIR / "output" / "tables"

OUTPUT_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)


RISK_COLOR = "#e33b2f"
EASE_COLOR = "#2567c9"
NEUTRAL_COLOR = "#9aa3ad"
NAVY = "#0b2a5b"
LIGHT_BLUE = "#eef5ff"
LIGHT_RED = "#fff0ec"


VECTOR_SPECS = [
    {
        "label": "1M 수익률",
        "column": "ret21",
        "positive": "최근 수익률 상승 -> 과열 가능성",
        "negative": "최근 수익률 하락 -> 위험 완화/저평가 후보",
    },
    {
        "label": "3M 모멘텀",
        "column": "ret63",
        "positive": "중기 모멘텀 강함 -> 추세 과열 가능성",
        "negative": "중기 모멘텀 약화 -> 리스크 완화",
    },
    {
        "label": "60D SMA 위치",
        "column": "ma60_gap",
        "positive": "가격이 60일선 상회 -> 상승 압력",
        "negative": "가격이 60일선 하회 -> 방어/저평가 신호",
    },
    {
        "label": "변동성 변화",
        "column": "vol_change",
        "positive": "단기 변동성 확대 -> 위험 증가",
        "negative": "단기 변동성 축소 -> 위험 완화",
    },
    {
        "label": "상대강도",
        "column": "rel_strength_63",
        "positive": "상대강도 강함 -> 추격 과열 가능성",
        "negative": "상대강도 약함 -> 회복 여지",
    },
]


def configure_korean_font() -> str:
    """Configure a Korean-capable font and prevent minus signs from breaking."""
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
    selected = next((name for name in candidates if name in available), None)

    if selected is None:
        selected = "DejaVu Sans"
        print("[주의] 한글 폰트를 찾지 못했습니다. 그래프 한글이 깨지면 Malgun Gothic 또는 NanumGothic을 설치하세요.")

    plt.rcParams["font.family"] = selected
    plt.rcParams["axes.unicode_minus"] = False
    return selected


def load_labels(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"HSI 상태 라벨 파일이 없습니다: {path}")

    df = pd.read_csv(path, encoding="utf-8-sig")
    df["Month"] = df["Month"].astype(str)
    df["Ticker"] = df["Ticker"].astype(str).str.zfill(6)

    if "MonthEndDate" in df.columns:
        df["MonthEndDate"] = pd.to_datetime(df["MonthEndDate"], errors="coerce")

    if "vol_change" not in df.columns:
        df["vol_change"] = df["vol20"] - df["vol60"]

    return df


def choose_row(df: pd.DataFrame, month: str | None, ticker: str | None) -> pd.Series:
    selected_month = month or df["Month"].max()
    month_df = df[df["Month"] == selected_month].copy()

    if month_df.empty:
        raise ValueError(f"선택 월에 해당하는 데이터가 없습니다: {selected_month}")

    if ticker:
        selected_ticker = str(ticker).zfill(6)
        sub = month_df[month_df["Ticker"] == selected_ticker]
        if sub.empty:
            raise ValueError(f"{selected_month}에 해당 티커가 없습니다: {selected_ticker}")
        return sub.iloc[0]

    score_col = "hsi_direction_score_draft"
    if score_col in month_df.columns:
        return month_df.loc[month_df[score_col].abs().idxmax()]

    return month_df.iloc[0]


def robust_z_score(series: pd.Series, value: float) -> float:
    valid = pd.to_numeric(series, errors="coerce").dropna()
    if len(valid) < 3:
        return 0.0

    std = valid.std()
    if pd.isna(std) or std == 0:
        return 0.0

    return float((value - valid.mean()) / std)


def build_vector_table(df: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    month_df = df[df["Month"] == row["Month"]].copy()
    rows = []

    for i, spec in enumerate(VECTOR_SPECS, start=1):
        raw_value = pd.to_numeric(row.get(spec["column"], np.nan), errors="coerce")
        z_score = robust_z_score(month_df[spec["column"]], raw_value)
        vector_score = float(np.clip(z_score / 2.0, -1.0, 1.0))

        rows.append({
            "Rank": i,
            "Indicator": spec["label"],
            "Column": spec["column"],
            "RawValue": raw_value,
            "CrossSectionZ": z_score,
            "VectorScore": vector_score,
            "AbsVectorScore": abs(vector_score),
            "Direction": "위험 악화" if vector_score >= 0 else "위험 완화",
            "PositiveMeaning": spec["positive"],
            "NegativeMeaning": spec["negative"],
        })

    table = pd.DataFrame(rows)
    return table.sort_values("AbsVectorScore", ascending=False).reset_index(drop=True)


def add_panel_label(ax, label: str) -> None:
    ax.text(
        0.02,
        0.98,
        label,
        transform=ax.transAxes,
        va="top",
        ha="left",
        color="white",
        fontsize=12,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.28", facecolor=NAVY, edgecolor=NAVY),
    )


def draw_hourglass_panel(ax, vectors: pd.DataFrame, row: pd.Series) -> None:
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-1.25, 1.25)
    ax.axis("off")
    add_panel_label(ax, "A. 원뿔형 벡터")

    top = Polygon([(-0.82, 0.82), (0, 0), (0.82, 0.82)], closed=True, facecolor=LIGHT_RED, edgecolor=RISK_COLOR, alpha=0.62)
    bottom = Polygon([(-0.82, -0.82), (0, 0), (0.82, -0.82)], closed=True, facecolor=LIGHT_BLUE, edgecolor=EASE_COLOR, alpha=0.62)
    ax.add_patch(top)
    ax.add_patch(bottom)
    ax.add_patch(Ellipse((0, 0.82), 1.64, 0.18, facecolor="#fde8e3", edgecolor=RISK_COLOR, lw=1.2, alpha=0.9))
    ax.add_patch(Ellipse((0, -0.82), 1.64, 0.18, facecolor="#e4efff", edgecolor=EASE_COLOR, lw=1.2, alpha=0.9))
    ax.axvline(0, color="#8a8a8a", ls="--", lw=1.0, dashes=(4, 4))
    ax.axhline(0, color="#bcbcbc", lw=0.9)
    ax.add_patch(Circle((0, 0), 0.045, color="#808080", ec="#333333", zorder=5))
    ax.text(-0.12, -0.06, "O", fontsize=12, fontweight="bold")

    angles = np.linspace(-58, 58, len(vectors))
    by_rank = vectors.sort_values("Rank").reset_index(drop=True)
    for angle_deg, (_, item) in zip(angles, by_rank.iterrows()):
        score = float(item["VectorScore"])
        color = RISK_COLOR if score >= 0 else EASE_COLOR
        direction = 1 if score >= 0 else -1
        length = 0.22 + 0.78 * abs(score)
        angle = math.radians(angle_deg)
        x = math.sin(angle) * length
        y = direction * math.cos(angle) * length
        ax.add_patch(FancyArrowPatch((0, 0), (x, y), arrowstyle="-|>", mutation_scale=12, lw=2.0, color=color))
        ax.scatter([x], [y], s=42, color=color, zorder=6)
        ax.text(x + (0.04 if x >= 0 else -0.04), y, str(int(item["Rank"])), color=color, fontsize=10, fontweight="bold",
                ha="left" if x >= 0 else "right", va="center")

    ax.text(-1.13, 0.55, "+ 위험 악화\n(위쪽 원뿔)", color=RISK_COLOR, fontsize=12, fontweight="bold", ha="left")
    ax.text(-1.13, -0.68, "- 위험 완화\n(아래쪽 원뿔)", color=EASE_COLOR, fontsize=12, fontweight="bold", ha="left")
    ax.text(
        0,
        -1.12,
        f"{row['Month']} / {row['Ticker']} / {row.get('HSIStateLabel', '')}",
        ha="center",
        fontsize=11,
        color=NAVY,
        fontweight="bold",
    )


def draw_sorted_section_panel(ax, vectors: pd.DataFrame) -> None:
    ax.set_xlim(-1.2, 1.55)
    ax.set_ylim(-0.5, len(vectors) + 0.8)
    ax.axis("off")
    add_panel_label(ax, "B. 길이순 정렬 단면")

    ordered = vectors.sort_values("AbsVectorScore", ascending=False).reset_index(drop=True)
    ax.axvline(0, color="#888888", lw=1.0)
    ax.text(-0.02, len(vectors) + 0.36, "O", ha="right", va="center", color="#444444", fontsize=11)

    for i, item in ordered.iterrows():
        y = len(vectors) - i
        score = float(item["VectorScore"])
        color = RISK_COLOR if score >= 0 else EASE_COLOR
        ax.plot([0, score], [y, y], color=color, lw=3.0)
        ax.scatter([0, score], [y, y], color=color, s=[20, 42])
        ax.text(-1.15, y, f"{int(item['Rank'])}. {item['Indicator']}", va="center", fontsize=10, color="#222222")
        ax.text(1.36, y, f"{score:+.2f}", va="center", ha="right", fontsize=10, color=color, fontweight="bold")

    ax.text(-1.15, 0.35, "절댓값이 큰 순서로 정렬해 신호 강도 비교", fontsize=10, color="#555555")


def draw_top_view_panel(ax, vectors: pd.DataFrame) -> None:
    add_panel_label(ax, "C. 위에서 본 단면")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 1.08)
    ax.set_yticklabels([])
    ax.grid(True, ls="--", color="#bcbcbc", alpha=0.75)
    ax.spines["polar"].set_color("#666666")

    by_rank = vectors.sort_values("Rank").reset_index(drop=True)
    angles = np.linspace(0, 2 * np.pi, len(by_rank), endpoint=False)

    for angle, (_, item) in zip(angles, by_rank.iterrows()):
        radius = float(item["AbsVectorScore"])
        color = RISK_COLOR if item["VectorScore"] >= 0 else EASE_COLOR
        ax.plot([angle, angle], [0, radius], color=color, lw=2.0, ls="--")
        ax.scatter([angle], [radius], color=color, s=46)
        ax.text(angle, min(1.05, radius + 0.11), f"{int(item['Rank'])}", color=color, fontweight="bold", ha="center", va="center")

    ax.set_xticklabels([])


def draw_summary_panel(ax, vectors: pd.DataFrame, row: pd.Series) -> None:
    ax.axis("off")
    add_panel_label(ax, "D. 도넛 요약")

    pos = vectors.loc[vectors["VectorScore"] > 0, "AbsVectorScore"].sum()
    neg = vectors.loc[vectors["VectorScore"] < 0, "AbsVectorScore"].sum()
    neutral = max(0.0, len(vectors) - pos - neg)
    total = pos + neg + neutral
    direction_hsi = (pos - neg) / (pos + neg) if pos + neg else 0.0
    intensity_hsi = (pos + neg) / len(vectors)
    collision_hsi = (2 * min(pos, neg) / (pos + neg)) if pos + neg else 0.0

    sizes = [pos / total, neg / total, neutral / total]
    colors = [RISK_COLOR, EASE_COLOR, NEUTRAL_COLOR]
    labels = ["위험 악화", "위험 완화", "중립"]

    wedges, _ = ax.pie(
        sizes,
        colors=colors,
        startangle=90,
        counterclock=False,
        radius=0.72,
        wedgeprops=dict(width=0.26, edgecolor="white"),
    )

    ax.text(0, 0.05, "HSI\n요약", ha="center", va="center", fontsize=12, fontweight="bold", color=NAVY)
    ax.text(0, -0.22, f"{row['Month']}", ha="center", va="center", fontsize=10, color="#555555")

    y0 = -0.92
    for i, (label, value, color) in enumerate(zip(labels, sizes, colors)):
        ax.add_patch(Rectangle((0.92, y0 + i * 0.24), 0.08, 0.08, color=color, transform=ax.transData, clip_on=False))
        ax.text(1.04, y0 + i * 0.24 + 0.04, f"{label}: {value:.0%}", va="center", fontsize=10, color="#333333")

    summary_text = (
        f"Direction HSI = {direction_hsi:+.2f}\n"
        f"Absolute Intensity = {intensity_hsi:.2f}\n"
        f"Collision HSI = {collision_hsi:.2f}\n"
        f"risk={row.get('risk_score', np.nan)}, overheat={row.get('overheat_score', np.nan)}, recovery={row.get('recovery_score', np.nan)}"
    )
    ax.text(-1.18, -1.18, summary_text, fontsize=10, color="#333333", va="top")


def save_visualization(labels: pd.DataFrame, row: pd.Series, vector_table: pd.DataFrame, output_stem: str) -> tuple[Path, Path]:
    fig = plt.figure(figsize=(16, 10), dpi=150)
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "HSI(Hourglass Signal Index) 원뿔형 시각화",
        fontsize=24,
        fontweight="bold",
        color=NAVY,
        y=0.992,
    )
    fig.text(
        0.5,
        0.935,
        "실제 HSI 입력 지표 기반 - 방향은 부호, 길이는 동월 단면 표준화 강도",
        ha="center",
        fontsize=12,
        color="#333333",
    )

    gs = fig.add_gridspec(2, 2, left=0.04, right=0.97, top=0.885, bottom=0.06, wspace=0.16, hspace=0.18)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0], projection="polar")
    ax_d = fig.add_subplot(gs[1, 1])

    draw_hourglass_panel(ax_a, vector_table, row)
    draw_sorted_section_panel(ax_b, vector_table)
    draw_top_view_panel(ax_c, vector_table)
    draw_summary_panel(ax_d, vector_table, row)

    png_path = OUTPUT_FIGURE_DIR / f"{output_stem}.png"
    svg_path = OUTPUT_FIGURE_DIR / f"{output_stem}.svg"
    fig.savefig(png_path, bbox_inches="tight", facecolor="white")
    fig.savefig(svg_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return png_path, svg_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HSI 원뿔형 시각화 생성")
    parser.add_argument("--month", default=None, help="시각화할 월. 예: 2026-06. 생략하면 최신 월")
    parser.add_argument("--ticker", default=None, help="시각화할 ETF 티커. 생략하면 해당 월에서 방향 점수가 가장 큰 티커")
    parser.add_argument("--output-stem", default=None, help="출력 파일명 stem")
    return parser.parse_args()


def main() -> None:
    font_name = configure_korean_font()
    labels = load_labels(LABEL_PATH)
    row = choose_row(labels, month=args.month, ticker=args.ticker)
    vector_table = build_vector_table(labels, row)

    output_stem = args.output_stem or f"fig16_hsi_hourglass_cone_{row['Month']}_{row['Ticker']}"
    table_path = OUTPUT_TABLE_DIR / f"{output_stem}_vectors.csv"
    vector_table.to_csv(table_path, index=False, encoding="utf-8-sig")

    png_path, svg_path = save_visualization(labels, row, vector_table, output_stem)

    print("[완료] HSI 원뿔형 시각화 생성")
    print(f"- 한글 폰트: {font_name}")
    print(f"- 선택 월/티커: {row['Month']} / {row['Ticker']}")
    print(f"- 상태명: {row.get('HSIStateLabel', '')}")
    print(f"- 벡터 표: {table_path}")
    print(f"- PNG: {png_path}")
    print(f"- SVG: {svg_path}")


if __name__ == "__main__":
    args = parse_args()
    main()
