# -*- coding: utf-8 -*-
"""
35_visual_report_pack.py — 보고서용 시각화 패키지 + 그림 안내문 생성

목적
----
강사님 피드백에 맞춰 다음 산출물을 보고서용으로 정리한다.

1) 리밸런싱 일자별 포트폴리오 구성 비중
2) IS/OOS/FULL 성과-위험 요약
3) OOS net10bp adoption decision 요약
4) 36개월 rolling factor exposure
5) 보고서에 붙일 그림별 소개·해석 가이드(md)

주의
----
이 스크립트는 백테스트 규칙을 바꾸지 않는다.
이미 생성된 main_final_* / flex_* 산출물을 읽어 시각화만 수행한다.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C


# ------------------------------------------------------------
# 공통 설정
# ------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parents[2]
TABLE_DIR = C.TABLE_DIR
FIGURE_DIR = C.FIGURE_DIR
REPORT_DIR = PROJECT_DIR / "reports"

FINAL = C.FINAL_PREFIX
INTERIM = C.INTERIM_PREFIX

TICKERS = list(C.TICKERS)
TICKER_LABELS = {
    "069500": "069500 위험자산",
    "114260": "114260 채권형 방어",
    "153130": "153130 현금성 방어",
}

CORE_STRATEGIES = [
    "lambda_0.1",
    "lambda_0.3",
    "asym_up0.1_down0.3",
    "dynamic_v1",
    "dynamic_v1_macro",
]

PERF_ORDER = [
    "FixedBM_70_20_10",
    "EW",
    "lambda_0.1",
    "lambda_0.3",
    "asym_up0.1_down0.3",
    "dynamic_v1",
    "dynamic_v1_macro",
]


def ensure_dirs() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"파일이 없습니다: {path}")
    return pd.read_csv(path, **kwargs)


def savefig(fig, filename: str) -> Path:
    out = FIGURE_DIR / filename
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def clean_strategy_name(name: str) -> str:
    mapping = {
        "FixedBM_70_20_10": "Fixed 70/20/10 BM",
        "EW": "EW",
        "lambda_0.1": "lambda 0.1",
        "lambda_0.3": "lambda 0.3",
        "asym_up0.1_down0.3": "asym up0.1/down0.3",
        "dynamic_v1": "dynamic v1",
        "dynamic_v1_macro": "dynamic v1 macro",
    }
    return mapping.get(name, name)


# ------------------------------------------------------------
# 1. 리밸런싱 구성 비중 차트
# ------------------------------------------------------------
def plot_weights(strategy: str) -> Path:
    path = TABLE_DIR / f"{FINAL}portfolio_composition_{strategy}.csv"
    df = read_csv(path)

    # index 컬럼이 저장되어 있을 수 있으므로 apply_date 후보 처리
    if "apply_date" in df.columns:
        date_col = "apply_date"
    elif "Unnamed: 0" in df.columns:
        date_col = "Unnamed: 0"
    else:
        date_col = df.columns[0]

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    weight_cols = [f"w_{t}" for t in TICKERS]
    missing = [c for c in weight_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{strategy} 구성표에 비중 열이 없습니다: {missing}")

    fig, ax = plt.subplots(figsize=(12, 5.5))
    x = df[date_col]
    ys = [df[c] * 100 for c in weight_cols]

    ax.stackplot(
        x,
        ys,
        labels=[TICKER_LABELS.get(t, t) for t in TICKERS],
        alpha=0.85,
    )

    ax.set_title(f"리밸런싱 일자별 포트폴리오 구성 비중 — {strategy}", fontsize=13)
    ax.set_ylabel("구성 비중 (%)")
    ax.set_xlabel("리밸런싱 적용월")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(loc="upper left", ncol=3, fontsize=9)

    # IS/OOS 경계선
    if hasattr(C, "OOS_START"):
        oos_start = pd.to_datetime(C.OOS_START)
        ax.axvline(oos_start, linestyle="--", linewidth=1.2, alpha=0.8)
        ax.text(
            oos_start,
            102,
            "OOS 시작",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    return savefig(fig, f"{FINAL}fig_weights_{strategy}.png")


# ------------------------------------------------------------
# 2. 성과-위험 요약 차트
# ------------------------------------------------------------
def plot_performance_risk_summary() -> Path:
    path = TABLE_DIR / f"{FINAL}is_oos_performance_table.csv"
    df = read_csv(path)

    full = df[df["segment"] == "FULL"].copy()
    full["strategy_label"] = full["strategy"].map(clean_strategy_name)
    full["order"] = full["strategy"].apply(
        lambda x: PERF_ORDER.index(x) if x in PERF_ORDER else 999
    )
    full = full.sort_values("order")

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    axes = axes.flatten()

    metrics = [
        ("cagr_pct", "CAGR (%)", "높을수록 유리"),
        ("ann_vol_pct", "연환산 변동성 (%)", "낮을수록 안정적"),
        ("mdd_pct", "MDD (%)", "덜 음수일수록 유리"),
        ("calmar", "Calmar", "높을수록 유리"),
    ]

    for ax, (col, title, note) in zip(axes, metrics):
        ax.barh(full["strategy_label"], full[col])
        ax.set_title(f"{title} — FULL")
        ax.grid(True, axis="x", alpha=0.25)
        ax.set_xlabel(note)

        if col == "mdd_pct":
            ax.axvline(0, linewidth=0.8)

    fig.suptitle("전략별 성과-위험 요약 — FULL 구간", fontsize=15, y=1.02)
    return savefig(fig, f"{FINAL}fig_performance_risk_summary_FULL.png")


# ------------------------------------------------------------
# 3. Adoption decision 요약 차트
# ------------------------------------------------------------
def plot_adoption_decision() -> Path:
    path = TABLE_DIR / f"{FINAL}adoption_decision.csv"
    df = read_csv(path)
    df["strategy_label"] = df["strategy"].map(clean_strategy_name)

    order = [
        "asym_up0.1_down0.3",
        "asym_up0.1_down0.5",
        "asym_up0.2_down0.3",
        "dynamic_v1",
        "dynamic_v1_macro",
    ]
    df["order"] = df["strategy"].apply(lambda x: order.index(x) if x in order else 999)
    df = df.sort_values("order")

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    axes = axes.flatten()

    metrics = [
        ("calmar_net", "OOS net10bp Calmar"),
        ("mdd_pct", "OOS net10bp MDD (%)"),
        ("tail_avg_pct", "Tail-month 평균수익 (%)"),
        ("avg_turnover_pct", "평균 Turnover (%)"),
    ]

    for ax, (col, title) in zip(axes, metrics):
        ax.barh(df["strategy_label"], df[col])
        ax.set_title(title)
        ax.grid(True, axis="x", alpha=0.25)
        if col == "mdd_pct":
            ax.axvline(0, linewidth=0.8)

    fig.suptitle("Adoption decision 요약 — OOS, 10bp 비용차감", fontsize=15, y=1.02)
    return savefig(fig, f"{FINAL}fig_adoption_decision_summary.png")


# ------------------------------------------------------------
# 4. Rolling factor exposure 차트
# ------------------------------------------------------------
def normalize_factor_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    """
    flex_factor_loading_timeseries.csv의 가능한 형태를 최대한 자동 인식한다.

    기대 형태 예:
    - date/window_end + strategy + dependent + beta_Market ...
    - Date + strategy + beta_Market ...
    """
    out = df.copy()

    # 날짜 열 찾기
    date_candidates = [
        "Date", "date", "window_end", "end_date", "asof_date",
        "month", "year_month", "Unnamed: 0"
    ]
    date_col = None
    for c in date_candidates:
        if c in out.columns:
            date_col = c
            break

    if date_col is None:
        raise ValueError(
            "rolling factor timeseries에서 날짜 열을 찾지 못했습니다. "
            f"columns={list(out.columns)}"
        )

    out[date_col] = pd.to_datetime(out[date_col])
    out = out.rename(columns={date_col: "Date"})

    # dependent가 있으면 excess_vs_BM 우선, 없으면 raw도 허용
    if "dependent" in out.columns:
        if (out["dependent"] == "excess_vs_BM").any():
            out = out[out["dependent"] == "excess_vs_BM"].copy()
        elif (out["dependent"] == "raw").any():
            out = out[out["dependent"] == "raw"].copy()

    if "strategy" not in out.columns:
        raise ValueError(
            "rolling factor timeseries에서 strategy 열을 찾지 못했습니다. "
            f"columns={list(out.columns)}"
        )

    return out


def find_beta_col(df: pd.DataFrame, factor: str) -> str | None:
    candidates = [
        f"beta_{factor}",
        f"beta{factor}",
        factor,
        factor.lower(),
        f"rolling_beta_{factor}",
        f"{factor}_beta",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def plot_rolling_factor_exposure() -> Path | None:
    path = TABLE_DIR / f"{INTERIM}factor_loading_timeseries.csv"
    if not path.exists():
        # 혹시 파일명이 flex_로 고정 생성되어 있는 경우
        path = TABLE_DIR / "flex_factor_loading_timeseries.csv"

    if not path.exists():
        print("[경고] rolling factor timeseries 파일이 없어 rolling exposure 그림을 건너뜁니다.")
        return None

    raw = read_csv(path)
    df = normalize_factor_timeseries(raw)

    factors = [
        ("Market", "36개월 Rolling Market Beta"),
        ("Bond", "36개월 Rolling Bond Beta"),
        ("Volatility", "36개월 Rolling Volatility Beta"),
        ("MacroRisk", "36개월 Rolling MacroRisk Exposure"),
    ]

    available = []
    for factor, title in factors:
        col = find_beta_col(df, factor)
        if col is not None:
            available.append((factor, title, col))

    if not available:
        print("[경고] beta_* 열을 찾지 못해 rolling exposure 그림을 건너뜁니다.")
        print("columns=", list(df.columns))
        return None

    fig, axes = plt.subplots(len(available), 1, figsize=(13, 3.2 * len(available)), sharex=True)
    if len(available) == 1:
        axes = [axes]

    for ax, (factor, title, col) in zip(axes, available):
        for strategy in CORE_STRATEGIES:
            sub = df[df["strategy"] == strategy].sort_values("Date")
            if sub.empty or col not in sub.columns:
                continue
            ax.plot(sub["Date"], sub[col], label=clean_strategy_name(strategy), linewidth=1.7)

        ax.axhline(0, linewidth=0.8, alpha=0.6)
        if factor == "Market":
            ax.axhline(1, linestyle="--", linewidth=0.8, alpha=0.6)
        ax.set_title(title)
        ax.set_ylabel("Beta / exposure")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best", fontsize=8)

    axes[-1].set_xlabel("Rolling window end")
    fig.suptitle("주요 후보의 36개월 Rolling Factor Exposure 비교", fontsize=15, y=1.01)

    return savefig(fig, f"{FINAL}fig_rolling_factor_exposure_core.png")


# ------------------------------------------------------------
# 5. OOS 누적수익률 집중 차트
# ------------------------------------------------------------
def plot_oos_candidate_cumret_focus() -> Path:
    path = TABLE_DIR / f"{FINAL}is_oos_performance_table.csv"
    _ = read_csv(path)  # 파일 존재 확인용

    # 33번의 기본 누적수익률 그림은 이미 있으므로,
    # 여기서는 33번 산출물이 생성되어 있음을 안내하기 위한 빈 재계산 대신
    # 기존 그림 파일명을 보고서 가이드에 포함한다.
    # 실제 추가 차트가 필요하면 추후 series 파일 생성 스크립트를 확장한다.
    return FIGURE_DIR / f"{FINAL}fig_cumret_OOS.png"


# ------------------------------------------------------------
# 6. 그림 안내문 / 보고서 삽입 가이드
# ------------------------------------------------------------
def write_figure_guide(paths: dict[str, Path | None]) -> Path:
    guide = REPORT_DIR / "main_final_figure_guide.md"

    text = f"""# HSI Overlay 프로젝트 — 보고서용 시각화 안내문

본 문서는 35_visual_report_pack.py가 생성한 그림을 최종 보고서에 삽입할 때 사용할 소개·분석·해석 초안이다.  
각 그림은 단순 장식이 아니라 강사님 피드백의 핵심 항목인 리밸런싱 구성, IS/OOS 성과, BM 비교, 변동성, MDD, Sharpe, factor loading, adoption decision을 설명하기 위한 근거 자료이다.

---

## 1. 리밸런싱 일자별 포트폴리오 구성 비중 — dynamic_v1

파일: `{paths.get("weights_dynamic_v1")}`

### 그림 소개
이 그림은 dynamic_v1 전략이 각 리밸런싱 적용월에 069500, 114260, 153130에 어떤 비중을 배분했는지 보여준다. 069500은 위험자산, 114260은 채권형 방어자산, 153130은 현금성 방어자산으로 해석한다.

### 분석
dynamic_v1은 HSI 상태별 목표비중을 바로 따라가는 전략이 아니라, annualized volatility, rolling drawdown, risk_relief 지속 조건에 따라 목표비중 반영 속도 λ를 조정한다. 따라서 동일한 HSI 상태 변화가 있더라도 실제 포트폴리오 비중은 λ에 의해 완만하게 이동한다.

### 해석
이 그림은 본 전략이 고정비중 포트폴리오가 아니라 월별 시장상태와 위험조건에 따라 실제 비중을 조정하는 방어형 Overlay임을 보여준다. 다만 이 결과는 수익률 예측이 아니라 상태 해석과 실행속도 조절의 결과로 해석해야 한다.

---

## 2. 리밸런싱 일자별 포트폴리오 구성 비중 — dynamic_v1_macro

파일: `{paths.get("weights_dynamic_v1_macro")}`

### 그림 소개
이 그림은 MacroRisk 조건을 추가한 dynamic_v1_macro 전략의 월별 포트폴리오 구성 비중을 보여준다.

### 분석
dynamic_v1_macro는 기존 dynamic_v1 조건에 MacroRisk >= 2 조건을 추가하였다. MacroRisk는 rate_up_flag와 fx_up_flag의 단순 합이며, MacroRisk >= 2는 금리 상승 압력과 환율 상승 압력이 동시에 관찰되는 달을 의미한다.

### 해석
dynamic_v1_macro는 macro 조건을 실제로 반영했지만, 검증 결과 기존 dynamic_v1 대비 CAGR, MDD, Calmar를 명확히 개선하지는 못했다. 대신 평균 Turnover와 연환산 변동성을 소폭 낮추는 효과가 있었다. 따라서 기본 시변 λ 후보는 dynamic_v1로 유지하고, dynamic_v1_macro는 macro-aware 저회전·보수 확장안으로 해석한다.

---

## 3. 전략별 성과-위험 요약 — FULL 구간

파일: `{paths.get("performance_risk")}`

### 그림 소개
이 그림은 Fixed 70/20/10 BM, EW, lambda_0.1, lambda_0.3, asym, dynamic_v1, dynamic_v1_macro의 FULL 구간 성과-위험 지표를 비교한다. 지표는 CAGR, 연환산 변동성, MDD, Calmar로 구성했다.

### 분석
Fixed 70/20/10 BM은 CAGR이 가장 높지만 MDD도 가장 크다. 반면 dynamic_v1과 dynamic_v1_macro는 CAGR은 FixedBM보다 낮지만 MDD와 Calmar 측면에서 더 안정적인 성과-위험 균형을 보인다.

### 해석
따라서 본 전략의 핵심은 BM 대비 단순 수익률 우위가 아니라 낙폭 통제와 위험조정 성과 개선이다. 이 프로젝트의 알파는 순수 수익률 알파가 아니라 가격 기반 시장상태 해석을 통한 방어형 낙폭 통제 엣지로 해석한다.

---

## 4. Adoption decision 요약 — OOS, 10bp 비용차감

파일: `{paths.get("adoption")}`

### 그림 소개
이 그림은 OOS 구간에서 10bp 거래비용을 차감한 뒤, 시변 layer 후보들의 Calmar, MDD, tail-month 평균수익, 평균 Turnover를 비교한다.

### 분석
dynamic_v1과 dynamic_v1_macro는 모두 사전등록 비열등 기준을 통과했다. dynamic_v1_macro는 dynamic_v1보다 Turnover가 낮지만, Calmar, MDD, tail-month 방어력은 소폭 낮았다.

### 해석
따라서 dynamic_v1은 기본 시변 λ 후보로 유지하고, dynamic_v1_macro는 MacroRisk 조건을 반영한 보수적 확장안으로 제시한다. 이 결론은 성과가 좋아 보이는 후보를 사후적으로 선택한 것이 아니라, 사전등록한 비열등 조건을 기준으로 판정한 결과이다.

---

## 5. 36개월 Rolling Factor Exposure

파일: `{paths.get("rolling_factor")}`

### 그림 소개
이 그림은 주요 후보의 36개월 rolling factor loading 변화를 보여준다. Market, Bond, Volatility, MacroRisk 노출이 시간에 따라 어떻게 달라졌는지 확인하기 위한 진단 자료이다.

### 분석
rolling factor exposure는 후보를 새로 고르기 위한 최적화 기준이 아니라, 최종 후보가 어떤 팩터 노출을 통해 성과를 만들었는지 설명하기 위한 사후 진단이다.

### 해석
이 그림은 전략의 성과가 단순히 한 구간의 우연한 결과인지, 또는 시장·채권·변동성·거시위험 노출 변화와 연결되어 있는지를 설명하는 데 사용한다. 다만 factor loading은 예측모형이 아니라 설명 도구이므로, 이를 근거로 새로운 λ 후보를 사후 선택하지 않는다.

---

## 6. 이미 생성된 기본 성과 시계열 차트

33_report_outputs.py에서 이미 생성된 기본 차트:

- `{FIGURE_DIR / f"{FINAL}fig_cumret_IS.png"}`
- `{FIGURE_DIR / f"{FINAL}fig_cumret_OOS.png"}`
- `{FIGURE_DIR / f"{FINAL}fig_cumret_FULL.png"}`
- `{FIGURE_DIR / f"{FINAL}fig_drawdown_FULL.png"}`

### 보고서 해석 방향
IS/OOS/FULL 누적수익률 차트는 전략이 특정 전체기간에만 의존하는지 확인하기 위한 자료이다. Drawdown 차트는 본 프로젝트의 핵심이 수익률 극대화가 아니라 낙폭 통제형 방어 Overlay임을 보여주는 핵심 그림이다.

---

## 최종 보고서 문장 요약

본 프로젝트는 동일한 3개 ETF 유니버스 안에서 FixedBM, EW, HSI baseline, 대칭 λ, 비대칭 λ, dynamic λ 후보를 비교하였다. 백테스트 결과를 그대로 신뢰하지 않고 가격-수익률 재현성 검증, factor input 원칙 감사, IS/OOS 분리, walk-forward 평가, 누수 audit, 비용 민감도, adoption decision을 순차적으로 수행하였다.

FixedBM은 CAGR이 가장 높았지만 MDD도 가장 컸다. HSI 기반 λ 전략은 수익률 극대화 전략이 아니라 낙폭 통제형 방어 Overlay로 해석하는 것이 적절하다. dynamic_v1은 OOS와 walk-forward에서 성과-위험 균형이 유지되었고, dynamic_v1_macro는 MacroRisk 조건을 실제로 반영했지만 기존 dynamic_v1을 명확히 개선하지는 못했다. 다만 Turnover와 연환산 변동성을 낮추는 효과가 있어 macro-aware 보수 확장안으로 제시한다.
"""

    guide.write_text(text, encoding="utf-8")
    return guide


# ------------------------------------------------------------
# main
# ------------------------------------------------------------
def main() -> None:
    ensure_dirs()

    paths = {}

    print("[35] 리밸런싱 구성 비중 차트 생성")
    for strategy in ["dynamic_v1", "dynamic_v1_macro"]:
        try:
            paths[f"weights_{strategy}"] = plot_weights(strategy)
            print(f"  - {strategy}: {paths[f'weights_{strategy}']}")
        except Exception as e:
            paths[f"weights_{strategy}"] = None
            print(f"  [경고] {strategy} weights 그림 실패: {e}")

    print("[35] 성과-위험 요약 차트 생성")
    try:
        paths["performance_risk"] = plot_performance_risk_summary()
        print(f"  - {paths['performance_risk']}")
    except Exception as e:
        paths["performance_risk"] = None
        print(f"  [경고] performance risk 그림 실패: {e}")

    print("[35] adoption decision 요약 차트 생성")
    try:
        paths["adoption"] = plot_adoption_decision()
        print(f"  - {paths['adoption']}")
    except Exception as e:
        paths["adoption"] = None
        print(f"  [경고] adoption decision 그림 실패: {e}")

    print("[35] rolling factor exposure 차트 생성")
    try:
        paths["rolling_factor"] = plot_rolling_factor_exposure()
        print(f"  - {paths['rolling_factor']}")
    except Exception as e:
        paths["rolling_factor"] = None
        print(f"  [경고] rolling factor exposure 그림 실패: {e}")

    print("[35] 그림 안내문 생성")
    guide_path = write_figure_guide(paths)
    print(f"  - {guide_path}")

    print("\n[완료] 35_visual_report_pack")
    print("생성된 그림과 reports/main_final_figure_guide.md를 확인한 뒤, 최종 보고서 본문 작성으로 이어가면 됩니다.")


if __name__ == "__main__":
    main()