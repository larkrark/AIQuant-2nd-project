from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = PROJECT_ROOT / "tmp"
FIGURE_DIR = PROJECT_ROOT / "output" / "figures" / "hsi_candidate_visuals"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

TS_PATH = TMP_DIR / "23_main_final_report_candidate_timeseries_subset.csv"
DEDUP_TS_PATH = TMP_DIR / "23_main_final_report_candidate_timeseries_subset_dedup.csv"
SHORTLIST_PATH = TMP_DIR / "23_main_final_report_candidate_shortlist.csv"
COST_PIVOT_PATH = TMP_DIR / "23_main_final_report_candidate_cost_pivot.csv"

DISPLAY_STRATEGIES = [
    "EW",
    "HSI_final_baseline_overlay",
    "lambda_0.1",
    "lambda_0.3",
    "lambda_0.5",
    "HSI_event_balance_filter_overlay",
]

LABEL_MAP = {
    "EW": "EW",
    "HSI_final_baseline_overlay": "HSI Baseline",
    "lambda_0.1": "Lambda 0.1",
    "lambda_0.3": "Lambda 0.3",
    "lambda_0.5": "Lambda 0.5",
    "HSI_event_balance_filter_overlay": "Event Filter",
}

ROLE_MAP = {
    "EW": "Sharpe가 가장 높은 단순 비교 기준",
    "HSI_final_baseline_overlay": "최종 후보가 아닌 기준선",
    "lambda_0.1": "MDD와 Turnover 완화 후보",
    "lambda_0.3": "수익성, Calmar, Turnover 균형 후보",
    "lambda_0.5": "중간 부분조정 후보",
    "HSI_event_balance_filter_overlay": "진단 및 보조 필터 후보",
}

COLOR_MAP = {
    "EW": "#4C566A",
    "HSI Baseline": "#C44E52",
    "Lambda 0.1": "#55A868",
    "Lambda 0.3": "#1F77B4",
    "Lambda 0.5": "#8172B2",
    "Event Filter": "#DD8452",
}


def add_common_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        template="plotly_white",
        hovermode="x unified",
        legend_title_text="전략",
        margin={"l": 64, "r": 28, "t": 72, "b": 56},
        font={"family": "Arial, Malgun Gothic, sans-serif", "size": 13},
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#ECEFF4")
    return fig


def write_figure(fig: go.Figure, filename: str) -> str:
    path = FIGURE_DIR / filename
    fig.write_html(path, include_plotlyjs="cdn", full_html=True)
    return path.name


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ts = pd.read_csv(TS_PATH, encoding="utf-8-sig")
    ts = (
        ts.assign(year_month=pd.to_datetime(ts["year_month"]))
        .sort_values(["strategy_name", "year_month"])
        .drop_duplicates(subset=["strategy_name", "year_month"], keep="last")
        .reset_index(drop=True)
    )
    ts.to_csv(DEDUP_TS_PATH, index=False, encoding="utf-8-sig")

    shortlist = pd.read_csv(SHORTLIST_PATH, encoding="utf-8-sig")
    cost_pivot = pd.read_csv(COST_PIVOT_PATH, encoding="utf-8-sig")

    for frame in (ts, shortlist, cost_pivot):
        frame["strategy_label"] = frame["strategy_name"].map(LABEL_MAP).fillna(frame["strategy_name"])

    return ts, shortlist, cost_pivot


def filter_display(frame: pd.DataFrame) -> pd.DataFrame:
    filtered = frame[frame["strategy_name"].isin(DISPLAY_STRATEGIES)].copy()
    filtered["strategy_name"] = pd.Categorical(
        filtered["strategy_name"],
        categories=DISPLAY_STRATEGIES,
        ordered=True,
    )
    sort_columns = ["strategy_name"]
    if "year_month" in filtered.columns:
        sort_columns.append("year_month")
    if "cost_bps" in filtered.columns:
        sort_columns.append("cost_bps")
    return filtered.sort_values(sort_columns)


def cumulative_return_fig(plot_ts: pd.DataFrame) -> go.Figure:
    fig = px.line(
        plot_ts,
        x="year_month",
        y="cumulative_return",
        color="strategy_label",
        color_discrete_map=COLOR_MAP,
        labels={
            "year_month": "월",
            "cumulative_return": "누적수익 지수",
            "strategy_label": "전략",
        },
        hover_data={
            "strategy_name": False,
            "strategy_label": False,
            "year_month": "|%Y-%m",
            "cumulative_return": ":.3f",
            "strategy_return": ":.2%",
            "drawdown": ":.2%",
            "turnover": ":.2%",
        },
    )
    fig.update_yaxes(tickformat=".2f")
    return add_common_layout(fig, "주요 비교 전략 누적수익률")


def drawdown_fig(plot_ts: pd.DataFrame) -> go.Figure:
    fig = px.line(
        plot_ts,
        x="year_month",
        y="drawdown",
        color="strategy_label",
        color_discrete_map=COLOR_MAP,
        labels={
            "year_month": "월",
            "drawdown": "Drawdown",
            "strategy_label": "전략",
        },
        hover_data={
            "strategy_name": False,
            "strategy_label": False,
            "year_month": "|%Y-%m",
            "drawdown": ":.2%",
            "cumulative_return": ":.3f",
            "strategy_return": ":.2%",
            "turnover": ":.2%",
        },
    )
    fig.update_yaxes(tickformat=".0%")
    return add_common_layout(fig, "주요 비교 전략 Drawdown")


def metric_summary_fig(shortlist: pd.DataFrame) -> go.Figure:
    metrics = filter_display(shortlist)
    metrics["MDD_abs_pct"] = metrics["MDD_pct"].abs()
    metrics["role_note"] = metrics["strategy_name"].map(ROLE_MAP)

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("CAGR", "MDD 절대값", "Calmar", "평균 Turnover"),
        horizontal_spacing=0.1,
        vertical_spacing=0.18,
    )

    panels = [
        ("CAGR_pct", "CAGR (%)", 1, 1),
        ("MDD_abs_pct", "|MDD| (%)", 1, 2),
        ("Calmar", "Calmar", 2, 1),
        ("avg_turnover_pct", "평균 Turnover (%)", 2, 2),
    ]
    for col_name, trace_name, row, col in panels:
        fig.add_trace(
            go.Bar(
                x=metrics["strategy_label"],
                y=metrics[col_name],
                marker_color=[COLOR_MAP[label] for label in metrics["strategy_label"]],
                name=trace_name,
                text=[f"{value:.2f}" for value in metrics[col_name]],
                textposition="outside",
                customdata=metrics[["Sharpe", "role_note"]],
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    + trace_name
                    + ": %{y:.2f}<br>"
                    + "Sharpe: %{customdata[0]:.3f}<br>"
                    + "%{customdata[1]}<extra></extra>"
                ),
                showlegend=False,
            ),
            row=row,
            col=col,
        )
        fig.update_yaxes(title_text=trace_name, gridcolor="#ECEFF4", row=row, col=col)

    fig.update_xaxes(tickangle=-20)
    fig.update_layout(
        title={"text": "성과, 위험, 회전율 요약", "x": 0.02, "xanchor": "left"},
        template="plotly_white",
        margin={"l": 64, "r": 28, "t": 84, "b": 80},
        font={"family": "Arial, Malgun Gothic, sans-serif", "size": 13},
        height=760,
    )
    return fig


def calmar_turnover_fig(shortlist: pd.DataFrame) -> go.Figure:
    metrics = filter_display(shortlist)
    metrics["MDD_abs_pct"] = metrics["MDD_pct"].abs()
    metrics["role_note"] = metrics["strategy_name"].map(ROLE_MAP)

    fig = px.scatter(
        metrics,
        x="avg_turnover_pct",
        y="Calmar",
        size="CAGR_pct",
        color="strategy_label",
        color_discrete_map=COLOR_MAP,
        text="strategy_label",
        labels={
            "avg_turnover_pct": "평균 Turnover (%)",
            "Calmar": "Calmar",
            "strategy_label": "전략",
            "CAGR_pct": "CAGR (%)",
        },
        hover_data={
            "strategy_name": False,
            "strategy_label": False,
            "CAGR_pct": ":.2f",
            "MDD_abs_pct": ":.2f",
            "Sharpe": ":.3f",
            "role_note": True,
        },
    )
    fig.update_traces(textposition="top center", marker={"line": {"width": 1, "color": "white"}})
    return add_common_layout(fig, "Calmar와 Turnover 관점 후보 비교")


def cost_sensitivity_fig(cost_pivot: pd.DataFrame) -> go.Figure:
    cost_selected = filter_display(cost_pivot)
    fig = px.line(
        cost_selected,
        x="cost_bps",
        y="CAGR_pct_after_cost_est",
        color="strategy_label",
        markers=True,
        color_discrete_map=COLOR_MAP,
        labels={
            "cost_bps": "거래비용 가정 (bps)",
            "CAGR_pct_after_cost_est": "비용 반영 후 추정 CAGR (%)",
            "strategy_label": "전략",
        },
        hover_data={
            "strategy_name": False,
            "strategy_label": False,
            "CAGR_pct_before_cost": ":.2f",
            "avg_turnover_pct": ":.2f",
            "annual_cost_drag_pct_est": ":.3f",
            "CAGR_pct_after_cost_est": ":.2f",
        },
    )
    fig.update_yaxes(ticksuffix="%")
    return add_common_layout(fig, "거래비용 민감도")


def turnover_fig(plot_ts: pd.DataFrame) -> go.Figure:
    fig = px.line(
        plot_ts,
        x="year_month",
        y="turnover",
        color="strategy_label",
        color_discrete_map=COLOR_MAP,
        labels={
            "year_month": "월",
            "turnover": "월별 Turnover",
            "strategy_label": "전략",
        },
        hover_data={
            "strategy_name": False,
            "strategy_label": False,
            "year_month": "|%Y-%m",
            "turnover": ":.2%",
            "strategy_return": ":.2%",
        },
    )
    fig.update_yaxes(tickformat=".0%")
    return add_common_layout(fig, "월별 Turnover")


def dashboard_html(figures: dict[str, go.Figure], shortlist: pd.DataFrame, files: dict[str, str]) -> None:
    metrics = filter_display(shortlist).copy()
    metrics["MDD_abs_pct"] = metrics["MDD_pct"].abs()
    metrics["strategy_label"] = metrics["strategy_name"].map(LABEL_MAP)

    cards = []
    for _, row in metrics.iterrows():
        cards.append(
            f"""
            <article class="metric-card">
              <h3>{row['strategy_label']}</h3>
              <p>{ROLE_MAP[row['strategy_name']]}</p>
              <dl>
                <div><dt>CAGR</dt><dd>{row['CAGR_pct']:.2f}%</dd></div>
                <div><dt>MDD</dt><dd>{row['MDD_pct']:.2f}%</dd></div>
                <div><dt>Sharpe</dt><dd>{row['Sharpe']:.3f}</dd></div>
                <div><dt>Turnover</dt><dd>{row['avg_turnover_pct']:.2f}%</dd></div>
              </dl>
            </article>
            """
        )

    table_rows = []
    columns = [
        ("strategy_label", "전략"),
        ("CAGR_pct", "CAGR"),
        ("MDD_pct", "MDD"),
        ("Sharpe", "Sharpe"),
        ("Calmar", "Calmar"),
        ("avg_turnover_pct", "Avg Turnover"),
        ("goldfriend_judgement", "해석"),
    ]
    for _, row in metrics.iterrows():
        cells = []
        for key, _ in columns:
            value = row[key]
            if key in {"CAGR_pct", "MDD_pct", "avg_turnover_pct"}:
                value = f"{value:.2f}%"
            elif key in {"Sharpe", "Calmar"}:
                value = f"{value:.3f}"
            cells.append(f"<td>{value}</td>")
        table_rows.append("<tr>" + "".join(cells) + "</tr>")

    embedded = "\n".join(
        f"<section><div class='plot'>{fig.to_html(include_plotlyjs='cdn' if i == 0 else False, full_html=False)}</div></section>"
        for i, fig in enumerate(figures.values())
    )

    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HSI 후보 전략 시각화 자료</title>
  <style>
    :root {{
      --ink: #20242c;
      --muted: #5d6675;
      --line: #dde3ea;
      --panel: #f7f9fb;
      --accent: #1f77b4;
    }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #ffffff;
      font-family: Arial, "Malgun Gothic", sans-serif;
      line-height: 1.55;
    }}
    main {{
      width: min(1180px, calc(100vw - 40px));
      margin: 0 auto;
      padding: 36px 0 56px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 22px;
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: clamp(28px, 4vw, 44px);
      letter-spacing: 0;
    }}
    h2 {{
      margin: 34px 0 14px;
      font-size: 22px;
      letter-spacing: 0;
    }}
    p {{
      margin: 0 0 10px;
      color: var(--muted);
    }}
    .takeaway {{
      max-width: 940px;
      color: var(--ink);
      font-size: 16px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(245px, 1fr));
      gap: 12px;
      margin: 22px 0 28px;
    }}
    .metric-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      background: #fff;
    }}
    .metric-card h3 {{
      margin: 0 0 6px;
      font-size: 17px;
    }}
    .metric-card p {{
      min-height: 48px;
      font-size: 13px;
    }}
    dl {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px 12px;
      margin: 14px 0 0;
    }}
    dt {{
      color: var(--muted);
      font-size: 12px;
    }}
    dd {{
      margin: 0;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: var(--panel);
      color: #303744;
      font-weight: 700;
    }}
    .plot {{
      border-top: 1px solid var(--line);
      padding-top: 18px;
      margin-top: 18px;
    }}
    .files {{
      background: var(--panel);
      border-radius: 8px;
      padding: 14px 16px;
      color: var(--muted);
      font-size: 13px;
    }}
    a {{
      color: var(--accent);
    }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>HSI 후보 전략 시각화 자료</h1>
    <p class="takeaway">
      HSI Baseline은 최종 후보가 아니라 비교 기준선입니다. Lambda 0.1과 Lambda 0.3은
      baseline 대비 MDD와 Turnover를 완화한 후보이며, EW는 Sharpe가 가장 높기 때문에
      Lambda 후보를 모든 지표에서 우월하다고 표현하기보다 수익성, Calmar, Turnover,
      비용 민감도 측면에서 검토 가치가 있는 후보로 해석하는 것이 적절합니다.
    </p>
  </header>

  <h2>요약 카드</h2>
  <div class="cards">
    {''.join(cards)}
  </div>

  <h2>후보별 지표 표</h2>
  <table>
    <thead><tr>{''.join(f'<th>{label}</th>' for _, label in columns)}</tr></thead>
    <tbody>{''.join(table_rows)}</tbody>
  </table>

  <h2>그래프</h2>
  {embedded}

  <h2>생성 파일</h2>
  <div class="files">
    <p>중복 제거 시계열: {DEDUP_TS_PATH.name}</p>
    <p>개별 HTML: {', '.join(files.values())}</p>
  </div>
</main>
</body>
</html>"""
    (FIGURE_DIR / "hsi_candidate_visual_dashboard.html").write_text(html, encoding="utf-8")


def main() -> None:
    ts, shortlist, cost_pivot = load_data()
    plot_ts = filter_display(ts)

    figures = {
        "cumulative": cumulative_return_fig(plot_ts),
        "drawdown": drawdown_fig(plot_ts),
        "summary": metric_summary_fig(shortlist),
        "calmar_turnover": calmar_turnover_fig(shortlist),
        "cost": cost_sensitivity_fig(cost_pivot),
        "turnover": turnover_fig(plot_ts),
    }

    files = {
        "cumulative": write_figure(figures["cumulative"], "01_hsi_candidate_cumulative_return.html"),
        "drawdown": write_figure(figures["drawdown"], "02_hsi_candidate_drawdown.html"),
        "summary": write_figure(figures["summary"], "03_hsi_candidate_metric_summary.html"),
        "calmar_turnover": write_figure(figures["calmar_turnover"], "04_hsi_candidate_calmar_turnover.html"),
        "cost": write_figure(figures["cost"], "05_hsi_candidate_cost_sensitivity.html"),
        "turnover": write_figure(figures["turnover"], "06_hsi_candidate_monthly_turnover.html"),
    }
    dashboard_html(figures, shortlist, files)

    print("Created:")
    print(f"  {DEDUP_TS_PATH}")
    for filename in files.values():
        print(f"  {FIGURE_DIR / filename}")
    print(f"  {FIGURE_DIR / 'hsi_candidate_visual_dashboard.html'}")


if __name__ == "__main__":
    main()
