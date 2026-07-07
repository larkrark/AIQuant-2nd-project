"""
22_build_additional_report_figures.py

수정 포인트(v2)
- matplotlib 한글 깨짐 방지용 폰트 설정을 추가했다.
- Windows에서는 보통 Malgun Gothic(맑은 고딕)을 자동 사용한다.
- 한글 폰트를 찾지 못하면 차트 제목/축 라벨을 영어로 대체해 깨진 네모 문자가 나오지 않게 한다.

목적
- 결과보고서에 추가로 넣을 권장 시각화 2종을 생성한다.
  1) HSI 5상태 분포 가로 막대바
  2) 후보 판단 분포 도넛차트 (+ 가로 막대바)

입력(기본 경로)
- output/tables/main_final_hsi_state5_distribution.csv
- output/tables/main_final_candidate_selection_summary.csv

출력
- output/figures/main_final_report_hsi_state_distribution_bar.png
- output/figures/main_final_report_candidate_decision_donut.png
- output/figures/main_final_report_candidate_decision_bar.png

사용 예시
(.venv) PS ...> python src/22_build_additional_report_figures.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager


# ============================================================
# 0. 경로 설정
# ============================================================

def find_project_root() -> Path:
    """
    현재 파일 위치 또는 실행 위치를 기준으로 프로젝트 루트를 찾는다.
    기대 구조:
      AIQuant-2nd-project/
        ├─ src/
        ├─ output/
        └─ docs/
    """
    here = Path(__file__).resolve()

    # 1) 보통은 src/ 밑에서 실행
    if here.parent.name == "src":
        return here.parent.parent

    # 2) 상위 폴더들 중 output 또는 docs가 있는 곳 탐색
    for p in [here.parent, *here.parents]:
        if (p / "output").exists() or (p / "docs").exists():
            return p

    # 3) 실패 시 현재 작업폴더
    return Path.cwd().resolve()


PROJECT_ROOT = find_project_root()
OUTPUT_TABLES = PROJECT_ROOT / "output" / "tables"
OUTPUT_FIGURES = PROJECT_ROOT / "output" / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"

OUTPUT_FIGURES.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 1. 한글 폰트 설정
# ============================================================

def setup_korean_font() -> tuple[bool, str]:
    """
    matplotlib에서 한글이 □□□로 깨지는 문제를 막기 위한 설정.
    Windows에서는 C:/Windows/Fonts/malgun.ttf 또는 Malgun Gothic을 우선 사용한다.
    """
    candidate_font_files = [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/malgunbd.ttf"),
        Path("/System/Library/Fonts/AppleGothic.ttf"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]

    for font_path in candidate_font_files:
        if font_path.exists():
            try:
                font_manager.fontManager.addfont(str(font_path))
                font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
                plt.rcParams["font.family"] = font_name
                plt.rcParams["axes.unicode_minus"] = False
                return True, font_name
            except Exception:
                pass

    # 이미 등록된 폰트 이름 기준 탐색
    candidate_font_names = [
        "Malgun Gothic",
        "맑은 고딕",
        "AppleGothic",
        "NanumGothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}

    for font_name in candidate_font_names:
        if font_name in available:
            plt.rcParams["font.family"] = font_name
            plt.rcParams["axes.unicode_minus"] = False
            return True, font_name

    # fallback: 한글 폰트를 찾지 못하면 영어 라벨을 사용한다.
    plt.rcParams["axes.unicode_minus"] = False
    return False, "fallback-English-labels"


KOREAN_FONT_OK, FONT_NAME = setup_korean_font()


def ko(ko_text: str, en_text: str) -> str:
    """한글 폰트가 있으면 한글, 없으면 영어 라벨을 반환한다."""
    return ko_text if KOREAN_FONT_OK else en_text


# ============================================================
# 2. 공통 유틸
# ============================================================

def print_header(title: str) -> None:
    print("=" * 80)
    print(title)
    print("=" * 80)


def find_first_existing(candidates: Iterable[Path]) -> Path:
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "후보 파일을 찾지 못했습니다.\n"
        + "\n".join(f" - {str(p)}" for p in candidates)
    )


def normalize_label(value) -> str:
    if pd.isna(value):
        return "unknown"
    return str(value).strip()


def pct_text(x: float) -> str:
    if pd.isna(x):
        return "-"
    return f"{x:.2f}%"


# ============================================================
# 3. HSI 상태분포 로드 및 그림 생성
# ============================================================

def load_state_distribution() -> pd.DataFrame:
    candidates = [
        OUTPUT_TABLES / "main_final_hsi_state5_distribution.csv",
        OUTPUT_TABLES / "main_final_hsi_state_distribution.csv",
        OUTPUT_TABLES / "main_final_state5_distribution.csv",
    ]
    path = find_first_existing(candidates)
    print(f"[상태분포] 사용 파일: {path}")

    df = pd.read_csv(path)

    state_col_candidates = [
        "hsi_state",
        "state",
        "state_name",
        "report_state_name",
    ]
    count_col_candidates = [
        "count",
        "n_months",
        "months",
        "freq",
        "frequency",
    ]
    pct_col_candidates = [
        "ratio_pct",
        "share_pct",
        "weight_pct",
        "pct",
        "percent",
        "proportion_pct",
    ]

    state_col = next((c for c in state_col_candidates if c in df.columns), None)
    count_col = next((c for c in count_col_candidates if c in df.columns), None)
    pct_col = next((c for c in pct_col_candidates if c in df.columns), None)

    if count_col is None:
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if numeric_cols:
            count_col = numeric_cols[0]

    if state_col is None or count_col is None:
        raise KeyError(
            "상태분포 파일에서 필요한 컬럼을 찾지 못했습니다. "
            f"columns={list(df.columns)}"
        )

    out = df[[state_col, count_col]].copy()
    out.columns = ["state", "count"]
    out["state"] = out["state"].map(normalize_label)
    out["count"] = pd.to_numeric(out["count"], errors="coerce")

    if pct_col is not None:
        out["ratio_pct"] = pd.to_numeric(df[pct_col], errors="coerce")
    else:
        total = out["count"].sum()
        out["ratio_pct"] = (out["count"] / total * 100.0) if total and total > 0 else float("nan")

    preferred_order = [
        "risk_relief",
        "neutral_watch",
        "conflict",
        "risk_warning",
        "accident_zone",
        "insufficient_data",
    ]
    rank_map = {name: i for i, name in enumerate(preferred_order)}
    out["order"] = out["state"].map(lambda x: rank_map.get(x, 999))
    out = out.sort_values(["order", "state"]).reset_index(drop=True)
    return out


def plot_state_distribution_bar(df: pd.DataFrame, save_path: Path) -> None:
    plot_df = df.copy()

    fig, ax = plt.subplots(figsize=(10.8, 5.8))
    ax.barh(plot_df["state"], plot_df["count"])
    ax.invert_yaxis()

    ax.set_title(ko("HSI 5상태 분포", "HSI 5-state distribution"), fontsize=14)
    ax.set_xlabel(ko("개월 수", "Number of months"))
    ax.set_ylabel(ko("상태", "State"))

    max_count = plot_df["count"].max()
    x_offset = max(1.0, max_count * 0.012)

    unit = ko("개월", "months")
    for i, row in plot_df.iterrows():
        label = f'{int(row["count"])}{unit} ({pct_text(row["ratio_pct"])})'
        ax.text(row["count"] + x_offset, i, label, va="center")

    # 오른쪽 텍스트가 잘리지 않도록 여백 확장
    ax.set_xlim(0, max_count * 1.18)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 4. 후보 판단 분포 로드 및 그림 생성
# ============================================================

def load_candidate_decision_summary() -> pd.DataFrame:
    summary_candidates = [
        OUTPUT_TABLES / "main_final_candidate_selection_summary.csv",
        OUTPUT_TABLES / "main_final_candidate_decision_summary.csv",
    ]

    judgement_candidates = [
        OUTPUT_TABLES / "main_final_candidate_final_judgement.csv",
        OUTPUT_TABLES / "main_final_candidate_judgement.csv",
    ]

    try:
        path = find_first_existing(summary_candidates)
        print(f"[후보분포] 사용 파일(요약표): {path}")
        df = pd.read_csv(path)

        decision_col_candidates = ["final_decision", "decision", "judgement", "result"]
        count_col_candidates = ["count", "n", "freq", "frequency"]

        decision_col = next((c for c in decision_col_candidates if c in df.columns), None)
        count_col = next((c for c in count_col_candidates if c in df.columns), None)

        if decision_col is None or count_col is None:
            raise KeyError("요약표 컬럼 탐색 실패")

        out = df[[decision_col, count_col]].copy()
        out.columns = ["final_decision", "count"]
        out["final_decision"] = out["final_decision"].map(normalize_label)
        out["count"] = pd.to_numeric(out["count"], errors="coerce")
        return out

    except Exception as e:
        print(f"  [요약표 fallback] {e}")
        path = find_first_existing(judgement_candidates)
        print(f"[후보분포] 사용 파일(판단표): {path}")
        raw = pd.read_csv(path)

        decision_col_candidates = ["final_decision", "decision", "judgement", "result"]
        decision_col = next((c for c in decision_col_candidates if c in raw.columns), None)
        if decision_col is None:
            raise KeyError(
                "후보 판단표에서 final_decision 계열 컬럼을 찾지 못했습니다. "
                f"columns={list(raw.columns)}"
            )

        out = (
            raw[decision_col]
            .map(normalize_label)
            .value_counts(dropna=False)
            .rename_axis("final_decision")
            .reset_index(name="count")
        )
        return out


def plot_candidate_decision_donut(df: pd.DataFrame, save_path: Path) -> None:
    plot_df = df.copy()
    plot_df = plot_df.sort_values("count", ascending=False).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(8.0, 6.8))
    ax.pie(
        plot_df["count"],
        labels=plot_df["final_decision"],
        autopct=lambda p: f"{p:.1f}%",
        startangle=90,
        wedgeprops=dict(width=0.45, edgecolor="white"),
        pctdistance=0.78,
        labeldistance=1.06,
    )

    total_n = int(plot_df["count"].sum())
    center_text = ko(f"전체\n{total_n}", f"Total\n{total_n}")
    ax.text(0, 0, center_text, ha="center", va="center", fontsize=13)
    ax.set_title(ko("후보 판단 분포", "Candidate decision distribution"), fontsize=14)
    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_candidate_decision_bar(df: pd.DataFrame, save_path: Path) -> None:
    plot_df = df.copy().sort_values("count", ascending=True).reset_index(drop=True)
    total_n = plot_df["count"].sum()
    plot_df["ratio_pct"] = plot_df["count"] / total_n * 100.0 if total_n > 0 else float("nan")

    fig, ax = plt.subplots(figsize=(9.8, 5.8))
    ax.barh(plot_df["final_decision"], plot_df["count"])
    ax.set_title(ko("후보 판단 분포", "Candidate decision distribution"), fontsize=14)
    ax.set_xlabel(ko("개수", "Count"))
    ax.set_ylabel(ko("판단 결과", "Decision"))
    ax.grid(axis="x", alpha=0.3)

    max_count = plot_df["count"].max()
    x_offset = max(0.5, max_count * 0.012)

    unit = ko("개", "")
    for i, row in plot_df.iterrows():
        label = f'{int(row["count"])}{unit} ({pct_text(row["ratio_pct"])})'
        ax.text(row["count"] + x_offset, i, label, va="center")

    ax.set_xlim(0, max_count * 1.18)
    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 5. 보고서 배치 메모 저장
# ============================================================

def write_placement_note(save_path: Path) -> None:
    note = """# 추가 그림 배치 메모

## 1. HSI 5상태 분포 가로 막대바
- 그림 파일: `output/figures/main_final_report_hsi_state_distribution_bar.png`
- 배치 위치: 결과보고서 3장 `HSI 상태분류 구조`
- 배치 문장:
  - "아래 그림은 HSI 상태가 전체 기간 동안 어떤 비율로 나타났는지 보여준다."
  - "이 그림은 HSI가 어떤 시장상태를 주로 생성했는지 확인하기 위한 기초 자료이다."

## 2. 후보 판단 분포 도넛차트
- 그림 파일: `output/figures/main_final_report_candidate_decision_donut.png`
- 대체 가능: `output/figures/main_final_report_candidate_decision_bar.png`
- 배치 위치: 결과보고서 9장 `최종 후보 선별 기준`
- 배치 문장:
  - "아래 그림은 전체 후보가 최종 선별 과정에서 어떻게 분류되었는지 보여준다."
  - "이 분포는 본 실험에서 Turnover가 핵심 필터였음을 보여준다."

## 3. 한글 폰트 안내
- Windows에서는 `Malgun Gothic`을 자동 사용하도록 설정했다.
- 한글 폰트를 찾지 못하는 환경에서는 차트 제목과 축 라벨을 영어로 대체한다.
"""
    save_path.write_text(note, encoding="utf-8")


# ============================================================
# 6. 메인 실행
# ============================================================

def main() -> None:
    print_header("22_build_additional_report_figures.py 실행 시작")
    print(f"[프로젝트 루트] {PROJECT_ROOT}")
    print(f"[matplotlib 폰트] {FONT_NAME} / Korean OK={KOREAN_FONT_OK}")

    # 1) HSI 상태분포 그림
    print("[1] HSI 5상태 분포 로드")
    state_df = load_state_distribution()
    print(state_df.to_string(index=False))

    state_fig = OUTPUT_FIGURES / "main_final_report_hsi_state_distribution_bar.png"
    plot_state_distribution_bar(state_df, state_fig)
    print(f"    저장: {state_fig}")

    # 2) 후보 판단 분포 그림
    print("[2] 후보 판단 분포 로드")
    decision_df = load_candidate_decision_summary()
    print(decision_df.to_string(index=False))

    donut_fig = OUTPUT_FIGURES / "main_final_report_candidate_decision_donut.png"
    bar_fig = OUTPUT_FIGURES / "main_final_report_candidate_decision_bar.png"

    plot_candidate_decision_donut(decision_df, donut_fig)
    print(f"    저장: {donut_fig}")

    plot_candidate_decision_bar(decision_df, bar_fig)
    print(f"    저장: {bar_fig}")

    # 3) 배치 메모
    print("[3] 그림 배치 메모 저장")
    note_path = DOCS_DIR / "experiment_notes" / "main_final_report_additional_figure_placement_note.md"
    write_placement_note(note_path)
    print(f"    저장: {note_path}")

    print_header("22_build_additional_report_figures.py 실행 완료")


if __name__ == "__main__":
    main()
