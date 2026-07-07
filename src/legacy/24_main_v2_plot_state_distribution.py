from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


"""
24_main_v2_plot_state_distribution.py

목적
----
main_v2 HSI 5상태 분포를 시각화한다.

질문
----
rank와 zscore 방식은 HSI 5상태를 어떻게 다르게 분류하는가?

입력
----
output/tables/main_v2_hsi_state5_distribution.csv

출력
----
output/figures/main_v2_fig1_hsi_state5_distribution.png
output/tables/main_v2_fig1_hsi_state5_distribution_plot_data.csv
docs/main_v2_fig1_hsi_state5_distribution_note.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
FIGURE_DIR = PROJECT_ROOT / "output" / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_PATH = TABLE_DIR / "main_v2_hsi_state5_distribution.csv"

OUTPUT_FIGURE_PATH = FIGURE_DIR / "main_v2_fig1_hsi_state5_distribution.png"
OUTPUT_PLOT_DATA_PATH = TABLE_DIR / "main_v2_fig1_hsi_state5_distribution_plot_data.csv"
OUTPUT_NOTE_PATH = DOCS_DIR / "main_v2_fig1_hsi_state5_distribution_note.md"


# ============================================================
# 1. 표시 설정
# ============================================================

STATE_ORDER = [
    "risk_relief",
    "neutral_watch",
    "conflict",
    "risk_warning",
    "accident_zone",
]

STATE_NAME_KR = {
    "risk_relief": "위험 완화 우세",
    "neutral_watch": "관찰·중립",
    "conflict": "충돌 상태",
    "risk_warning": "위험 악화 우세",
    "accident_zone": "강한 위험 악화",
}


def set_korean_font() -> None:
    """
    Windows 환경에서 한글 깨짐을 줄이기 위한 설정.
    """
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


# ============================================================
# 2. 데이터 로드 및 정리
# ============================================================

def load_distribution() -> pd.DataFrame:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH)

    required_cols = ["method", "hsi_state5", "state_name_kr", "months", "total_months", "ratio"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(f"필요한 컬럼이 없습니다: {missing_cols}")

    df["hsi_state5"] = pd.Categorical(
        df["hsi_state5"],
        categories=STATE_ORDER,
        ordered=True,
    )

    df = df.sort_values(["method", "hsi_state5"]).reset_index(drop=True)
    df["ratio_pct"] = df["ratio"] * 100
    df["state_label"] = df["hsi_state5"].map(STATE_NAME_KR)

    return df


def make_plot_data(df: pd.DataFrame) -> pd.DataFrame:
    plot_data = df[
        [
            "method",
            "hsi_state5",
            "state_label",
            "months",
            "total_months",
            "ratio",
            "ratio_pct",
        ]
    ].copy()

    return plot_data


# ============================================================
# 3. 그래프 생성
# ============================================================

def plot_state_distribution(plot_data: pd.DataFrame) -> None:
    set_korean_font()

    pivot = plot_data.pivot(
        index="state_label",
        columns="method",
        values="ratio_pct",
    )

    # 상태 순서 유지
    ordered_labels = [STATE_NAME_KR[state] for state in STATE_ORDER]
    pivot = pivot.reindex(ordered_labels)

    ax = pivot.plot(
        kind="bar",
        figsize=(11, 6),
        width=0.75,
    )

    ax.set_title("Fig.1 HSI 5상태 분포 비교: rank vs zscore", fontsize=14)
    ax.set_xlabel("HSI 5상태")
    ax.set_ylabel("비중 (%)")
    ax.legend(title="점수화 방식")
    ax.grid(axis="y", alpha=0.3)

    for container in ax.containers:
        ax.bar_label(container, fmt="%.1f%%", fontsize=9)

    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(OUTPUT_FIGURE_PATH, dpi=150)
    plt.close()


# ============================================================
# 4. 해석 노트 생성
# ============================================================

def make_note(plot_data: pd.DataFrame) -> str:
    rank = plot_data[plot_data["method"] == "rank"].copy()
    zscore = plot_data[plot_data["method"] == "zscore"].copy()

    def get_ratio(method_df: pd.DataFrame, state: str) -> float:
        row = method_df[method_df["hsi_state5"].astype(str) == state]
        if row.empty:
            return 0.0
        return float(row["ratio_pct"].iloc[0])

    rank_conflict = get_ratio(rank, "conflict")
    zscore_conflict = get_ratio(zscore, "conflict")
    rank_neutral = get_ratio(rank, "neutral_watch")
    zscore_neutral = get_ratio(zscore, "neutral_watch")

    lines = []

    lines.append("# Fig.1 HSI 5상태 분포 해석 노트")
    lines.append("")
    lines.append("## 그림의 질문")
    lines.append("")
    lines.append("rank와 zscore 방식은 HSI 5상태를 어떻게 다르게 분류하는가?")
    lines.append("")
    lines.append("## 핵심 관찰")
    lines.append("")
    lines.append(
        f"- rank 기준 conflict 비중은 약 {rank_conflict:.1f}%이다."
    )
    lines.append(
        f"- zscore 기준 conflict 비중은 약 {zscore_conflict:.1f}%이다."
    )
    lines.append(
        f"- rank 기준 neutral_watch 비중은 약 {rank_neutral:.1f}%이다."
    )
    lines.append(
        f"- zscore 기준 neutral_watch 비중은 약 {zscore_neutral:.1f}%이다."
    )
    lines.append("")
    lines.append("## 해석")
    lines.append("")
    lines.append(
        "rank 방식은 상대적 위치를 기준으로 판단하기 때문에 conflict 상태를 더 민감하게 포착하는 경향이 있다."
    )
    lines.append(
        "반면 zscore 방식은 평균과 표준편차 기준으로 극단성을 판단하므로 neutral_watch 상태에 더 오래 머무르는 경향이 있다."
    )
    lines.append(
        "이 차이는 이후 overlay 규칙에서 conflict를 방어 신호로 볼지, 관찰 신호로 볼지 판단하는 근거가 된다."
    )
    lines.append("")
    lines.append("## 보고서 연결 문장")
    lines.append("")
    lines.append(
        "HSI 5상태 분포를 비교한 결과, rank 방식은 zscore 방식보다 conflict 상태를 더 자주 포착하였다. "
        "이는 rank 기반 분류가 시장 내 상대적 위치 변화에 더 민감하게 반응한다는 점을 시사한다. "
        "따라서 conflict 상태를 즉시 방어전환으로 사용할 경우 불필요한 비중 조정과 Turnover가 증가할 수 있으므로, "
        "후속 실험에서는 conflict를 관찰 상태로 처리하는 완화형 overlay 규칙을 함께 비교하였다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 5. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("24_main_v2_plot_state_distribution.py 실행 시작")
    print("=" * 70)

    df = load_distribution()
    plot_data = make_plot_data(df)

    plot_data.to_csv(OUTPUT_PLOT_DATA_PATH, index=False, encoding="utf-8-sig")
    plot_state_distribution(plot_data)

    note = make_note(plot_data)
    OUTPUT_NOTE_PATH.write_text(note, encoding="utf-8")

    print("[저장 완료]")
    print(f"- {OUTPUT_FIGURE_PATH}")
    print(f"- {OUTPUT_PLOT_DATA_PATH}")
    print(f"- {OUTPUT_NOTE_PATH}")

    print("\n[그래프용 데이터]")
    print(plot_data)

    print("\n" + "=" * 70)
    print("24_main_v2_plot_state_distribution.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()