// Build two Word documents for the HSI-RA Asymmetric-Lambda follow-up:
//  1) 상세 수행 문서 (실험계획서 + 예비보고서 + 상세과정 통합)
//  2) 결과보고서 구성틀
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  PageBreak, VerticalAlign,
} = require("docx");

const CONTENT_W = 9000; // A4 content width (DXA) approx
const HEAD_FILL = "1F4E79";   // dark blue header
const HEAD_FONT = "FFFFFF";
const ALT_FILL = "EAF1FB";    // light zebra

// ---------- helpers ----------
function widths(weights) {
  const s = weights.reduce((a, b) => a + b, 0);
  const w = weights.map((x) => Math.round((x / s) * CONTENT_W));
  const diff = CONTENT_W - w.reduce((a, b) => a + b, 0);
  w[w.length - 1] += diff;
  return w;
}
function runs(text, opts = {}) {
  const arr = Array.isArray(text) ? text : [text];
  return arr.map((t, i) =>
    new Paragraph({
      spacing: { after: opts.after ?? 20, before: opts.before ?? 0, line: 264 },
      alignment: opts.align,
      children: [new TextRun({ text: t, bold: opts.bold, italics: opts.italics,
        color: opts.color, size: opts.size, font: opts.font })],
    })
  );
}
function cell(text, w, opts = {}) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER,
    shading: opts.fill ? { type: ShadingType.CLEAR, color: "auto", fill: opts.fill } : undefined,
    margins: { top: 40, bottom: 40, left: 90, right: 90 },
    children: runs(text, {
      bold: opts.bold,
      color: opts.header ? HEAD_FONT : opts.color,
      size: opts.size ?? 17,
      align: opts.align,
    }),
  });
}
function table(headers, rows, weightArr, opts = {}) {
  if (weightArr && weightArr.length !== headers.length)
    throw new Error(`weights(${weightArr.length}) != headers(${headers.length}): ${JSON.stringify(headers)}`);
  rows.forEach((r, ri) => {
    if (r.length !== headers.length)
      throw new Error(`row ${ri} cols(${r.length}) != headers(${headers.length}) in ${JSON.stringify(headers)}`);
  });
  const cw = widths(weightArr || headers.map(() => 1));
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => cell(h, cw[i], { bold: true, header: true, fill: HEAD_FILL, size: 17 })),
  });
  const bodyRows = rows.map((r, ri) =>
    new TableRow({
      children: r.map((c, i) =>
        cell(c, cw[i], { fill: ri % 2 === 1 ? ALT_FILL : undefined, size: opts.size ?? 17 })
      ),
    })
  );
  return new Table({
    columnWidths: cw,
    width: { size: CONTENT_W, type: WidthType.DXA },
    rows: [headerRow, ...bodyRows],
  });
}
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 260, after: 90 }, children: [new TextRun({ text: t, bold: true, size: 28, color: "1F4E79" })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 180, after: 70 }, children: [new TextRun({ text: t, bold: true, size: 23, color: "2E5496" })] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 120, after: 50 }, children: [new TextRun({ text: t, bold: true, size: 20, color: "333333" })] });
const P = (t, opts = {}) => runs(t, { after: opts.after ?? 90, size: 20, italics: opts.italics, bold: opts.bold, color: opts.color })[0];
const NOTE = (t) => new Paragraph({ spacing: { after: 90, line: 264 }, border: { left: { style: BorderStyle.SINGLE, size: 18, color: "9CC3E5", space: 12 } }, indent: { left: 160 }, children: [new TextRun({ text: t, italics: true, size: 19, color: "444444" })] });
const BUL = (items) => items.map((t) => new Paragraph({ bullet: { level: 0 }, spacing: { after: 24, line: 260 }, children: [new TextRun({ text: t, size: 20 })] }));
const NUM = (items, ref) => items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 24, line: 260 }, children: [new TextRun({ text: t, size: 20 })] }));
const GAP = (after = 80) => new Paragraph({ spacing: { after }, children: [] });
const RULE = () => new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: "BBBBBB", space: 4 } }, spacing: { after: 120 }, children: [] });
function cover(title, subtitle, meta) {
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200, after: 40 }, children: [new TextRun({ text: title, bold: true, size: 40, color: "1F4E79" })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 }, children: [new TextRun({ text: subtitle, size: 24, color: "2E5496" })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 }, children: [new TextRun({ text: meta, size: 18, color: "666666" })] }),
    RULE(),
  ];
}
const numberingConfig = {
  config: [
    { reference: "n1", levels: [{ level: 0, format: "decimal", text: "%1.", alignment: AlignmentType.START }] },
    { reference: "n2", levels: [{ level: 0, format: "decimal", text: "%1.", alignment: AlignmentType.START }] },
    { reference: "n3", levels: [{ level: 0, format: "decimal", text: "%1.", alignment: AlignmentType.START }] },
    { reference: "n4", levels: [{ level: 0, format: "decimal", text: "%1.", alignment: AlignmentType.START }] },
    { reference: "n5", levels: [{ level: 0, format: "decimal", text: "%1.", alignment: AlignmentType.START }] },
  ],
};
const baseStyles = {
  default: { document: { run: { font: "Malgun Gothic", size: 20 } } },
};
const pageA4 = { size: { width: 11906, height: 16838 }, margin: { top: 1200, bottom: 1200, left: 1200, right: 1200 } };

// =====================================================================
// DOCUMENT 1 — 상세 수행 문서
// =====================================================================
const d1 = [];
d1.push(...cover(
  "HSI RoboAdvisor · 비대칭 Lambda 상세 수행 문서",
  "실험계획서 + 예비보고서 + 상세 과정 통합본 (v2)",
  "AIQuant 2차 프로젝트 · 후속 실험 · 팀 공유/제출용 · 2026-07"
));

d1.push(H1("0. 문서 목적과 읽는 법"));
d1.push(P("본 문서는 비대칭·조건부 Lambda 후속 실험을 “결과를 먼저 만들고 해석을 나중에 맞추는” 방식이 아니라, 실험 전에 입력물·처리 과정·산출물·검증 기준을 고정하고, 결과보고서를 읽는 사람이 그 과정을 그대로 따라가며 감사(audit)할 수 있도록 설계한 상세 수행 문서이다."));
d1.push(P("구성은 요청에 따라 세 부분을 하나로 통합한다: Part 1 실험계획서(무엇을 왜 어떻게 할지 사전 확정), Part 2 예비보고서(대칭 λ에서 이미 확인된 사실과 비대칭이 필요한 이유), Part 3 상세 수행 과정(단계·입출력 구조표·검증 게이트·후보 선별·역할). 각 Part는 단독으로도 떼어 배포할 수 있도록 자기완결적으로 작성하였다."));
d1.push(NOTE("읽는 순서 권장: 계획(Part 1) → 예비 근거(Part 2) → 수행·검증(Part 3). 결과보고서(별도 구성틀 문서)는 이 문서의 산출물과 검증 기록을 그대로 인용해 채운다."));
d1.push(H3("용어 정리"));
d1.push(table(
  ["용어", "의미"],
  [
    ["λ (Lambda)", "HSI 상태별 목표비중이 실제 포트폴리오에 반영되는 속도. w_t = w_{t-1} + λ·(w*_t − w_{t-1})."],
    ["λ_up / λ_down", "위험자산(069500) 목표비중이 늘어나는 방향(re-risking)에는 λ_up, 줄어드는 방향(de-risking)에는 λ_down을 적용하는 비대칭 계수."],
    ["조건부(동적) λ", "변동성·낙폭·macro 위험 등 시장 조건에 따라 그 달의 λ_t를 규칙으로 정하는 구조. HSI 상태분류 자체는 바꾸지 않는다."],
    ["In-sample(IS)", "규칙·threshold·후보를 설계하는 데 사용하는 구간."],
    ["Out-of-sample(OOS)", "설계에 쓰지 않고 평가에만 쓰는 구간. threshold 재조정 금지."],
    ["Walk-forward", "일정 구간으로 규칙을 점검한 뒤 다음 구간을 평가하고, 창을 이동하며 반복하는 검증."],
    ["Robustness", "기간·상태·비용·인접 파라미터를 바꿔도 결과가 크게 무너지지 않는지 보는 강건성 검증."],
    ["데이터 누수(leakage)", "미래 정보 또는 평가 구간 정보가 설계 단계에 새어 들어가는 오류."],
    ["팩터로딩", "전략 수익을 시장·채권·모멘텀·변동성·macro 팩터에 회귀했을 때의 민감도(β)."],
  ],
  [2, 7]
));

// ---- PART 1 ----
d1.push(new Paragraph({ pageBreakBefore: true, children: [] }));
d1.push(H1("Part 1. 실험계획서"));

d1.push(H2("1.1 배경과 현재 위치"));
d1.push(P("현재 HSI RA 프로젝트의 최종 후보는 고정 λ=0.1(저회전·방어형)과 λ=0.3(수익성·Calmar 균형형)이다. 이는 optimizer로 구한 단일 최적값이 아니라 여러 λ를 비교한 sensitivity 실험(실험 10)의 결과이다. 실험 15는 macro overlay보다 “HSI 상태·시장 조건에 따라 λ를 다르게 주는 동적 λ 구조”를 후속 방향으로 명시했고, 본 계획서는 그 지점을 이어받는다."));
d1.push(P("핵심 아이디어는 두 가지다. 첫째, 지금까지의 λ는 위험자산 비중이 늘어날 때와 줄어들 때를 같은 속도로 처리하는 대칭 구조였다. 방어형 overlay라면 “위험은 빠르게 줄이고, 복귀는 신중하게”처럼 방향에 따라 속도를 다르게 두는 비대칭 구조가 더 자연스러울 수 있다. 둘째, 변동성·낙폭·macro 위험 같은 조건에 따라 λ를 낮추거나 높이는 조건부 λ가 추가 개선을 줄 수 있는지 확인한다."));

d1.push(H2("1.2 연구 질문(RQ)"));
d1.push(...BUL([
  "RQ1. λ_up ≠ λ_down 비대칭 구조가 대칭 λ의 성과-위험 frontier(CAGR·MDD·Turnover)를 개선하는가?",
  "RQ2. 방어형 가설 “λ_down ≥ λ_up (cut fast, add back slow)”이 데이터에서 지지되는가, 아니면 반대(빠른 재진입)가 유리한가?",
  "RQ3. 변동성·낙폭·macro 조건에 따른 조건부 λ가 비대칭 λ 위에서 추가 개선을 주는가?",
  "RQ4. 위 개선이 In-sample뿐 아니라 Out-of-sample·walk-forward에서도 유지되는가(과적합이 아닌가)?",
]));

d1.push(H2("1.3 실험 가설"));
d1.push(table(
  ["가설", "내용"],
  [
    ["H1", "비대칭 λ는 대칭 λ 대비 같은 CAGR에서 MDD를 낮추거나, 같은 MDD에서 CAGR을 높이는 조합이 존재한다."],
    ["H2", "방어형 목적에서는 λ_down(위험 축소 속도)을 크게, λ_up(위험 복귀 속도)을 작게 두는 영역에서 tail-month 방어가 개선된다."],
    ["H3", "그러나 λ_up을 지나치게 낮추면 회복장(예: 2023–2026)에서 재진입이 늦어 CAGR·Calmar가 훼손된다(반작용 존재)."],
    ["H4", "변동성 상승·낙폭 확대 구간에서 λ를 낮추면 과잉 매매와 비용을 완화하고 MDD를 개선할 수 있다."],
    ["H5", "macro 위험(금리·환율 동반 위험)은 λ 조절의 보조 조건으로만 유효하며, 단독으로 최종 후보를 바꿀 만큼 강하지 않다."],
  ],
  [1.2, 8]
));

d1.push(H2("1.4 후속 실험 구성"));
d1.push(P("실험 번호는 기존 초안(24 팩터로딩 진단, 28~30 비대칭·동적 λ)을 따른다. 24는 새 전략을 만드는 실험이 아니라 기존 λ 후보의 팩터 노출을 설명해 28~30의 설계 방향을 근거화하는 진단 실험이다."));
d1.push(table(
  ["번호", "실험", "핵심 질문", "성격"],
  [
    ["E24", "Factor loading diagnostic", "기존 λ 후보는 어떤 시장·채권·모멘텀·변동성·macro 팩터에 노출됐는가", "진단(설명)"],
    ["E28", "단일 λ 반응곡선(response curve)", "λ를 0→1로 세밀히 움직일 때 성과·비용의 형태와 안정 구간은", "재현·기준선"],
    ["E29", "비대칭 λ_up/λ_down grid search", "방향별 속도를 분리하면 대칭 frontier를 넘어서는가", "핵심 실험"],
    ["E30", "조건부(동적) λ", "변동성·낙폭·macro·상태 지속으로 λ_t를 정하면 추가 개선이 있는가", "확장 실험"],
  ],
  [0.8, 2.8, 4, 1.4]
));

d1.push(H2("1.5 고정 요소 (frozen) — 실험 간 동일하게 유지"));
d1.push(table(
  ["항목", "고정값"],
  [
    ["ETF 유니버스", "069500 KODEX 200(위험) · 114260 KODEX 국고채3년(채권형 방어) · 153130 KODEX 단기채권(현금성 방어)"],
    ["기간", "2012-03 ~ 2026-06 (월말가격 172개월, 월수익률 171~172개월)"],
    ["HSI 상태분류", "5상태(risk_relief·neutral_watch·conflict·risk_warning·accident_zone) + insufficient_data, θ=0.15 기준"],
    ["상태별 목표비중 w*", "risk_relief 70/20/10 · neutral_watch 50/35/15 · conflict 35/40/25 · risk_warning 20/45/35 · accident_zone 0/30/70 (069500/114260/153130)"],
    ["리밸런싱", "월간. t월 말 관측 신호로 목표비중 산출 → t+1월 수익률에 적용(look-ahead 방지)"],
    ["수익률 단위", "계산은 decimal, 보고 표는 %"],
    ["비교군(4층)", "Fixed 70/20/10 BM(메인 BM) · EW Benchmark(보조 BM) · HSI baseline(즉시비중 내부 기준선) · 대칭 λ=0.1/0.3(참조 후보)"],
    ["거래비용 가정", "0.00 / 0.05 / 0.10 / 0.20 % (Turnover×비용률 사후 차감, 민감도용)"],
  ],
  [1.6, 8]
));
d1.push(NOTE("주의(버전 정합성): 성과 기준선은 실험 10·20~23 계열 수치(EW CAGR 6.51%, λ=0.1 8.66%, λ=0.3 9.09%)로 통일한다. 16·17번 표는 동일 지표를 약 0.07~0.08%p 높게 적고 있어(EW 6.59, λ=0.1 8.69, λ=0.3 9.15), 후속 실험 시작 시 한 convention으로 재계산해 고정한다."));

d1.push(H2("1.6 사전 등록(pre-registration) grid와 범위"));
d1.push(P("과적합을 줄이기 위해 grid는 시작 전에 확정하고, 결과를 본 뒤 범위·간격을 바꾸지 않는다(변경 시 별도 기록)."));
d1.push(table(
  ["실험", "탐색 범위(사전 고정)", "셀 수", "비고"],
  [
    ["E28", "λ ∈ {0.00, 0.10, 0.20, 0.30, 0.50, 0.70, 1.00} (필요 시 0.05 간격 보조)", "7(+보조)", "0.1/0.3 위치와 안정 구간 확인"],
    ["E29", "λ_down ∈ {0.10, 0.20, 0.30, 0.50} × λ_up ∈ {0.10, 0.20, 0.30, 0.50}", "16", "대각선(λ_up=λ_down)은 대칭 참조. λ_down>λ_up 영역 우선 관찰"],
    ["E30", "기본 λ=0.3, 고위험→0.1, 안정완화→0.5 (규칙 v1). threshold는 IS에서만 결정", "규칙 1종+민감도", "규칙 확장은 v2로 분리"],
  ],
  [0.8, 5.4, 0.9, 2.9]
));

d1.push(H2("1.7 성공·판단 기준"));
d1.push(...BUL([
  "CAGR 1등을 채택 기준으로 쓰지 않는다. MDD·Calmar·Turnover·거래비용 drag를 함께 본다.",
  "채택 조건: 대칭 λ=0.1 또는 λ=0.3 대비 trade-off(예: 같은 CAGR에서 낮은 MDD, 또는 낮은 Turnover)를 개선하고, 그 개선이 OOS/walk-forward에서 유지될 때.",
  "제외/보류 조건: MDD가 대칭 대비 악화, Turnover 과다, CAGR·Calmar 큰 훼손, 특정 구간에만 성과가 몰림, 인접 파라미터에서 급격히 무너짐.",
  "채택 판정은 사전등록 결정규칙(비열등 기준)을 따른다: 방어형 사용자 목적(OOS·10bp 비용차감 기준 Calmar ≥ 대칭 최우수의 90%, MDD 악화 ≤ 2%p, tail-month 악화 ≤ 0.3%p, Turnover ≤ 대칭 0.3의 1.5배)을 만족하고 8게이트를 통과하면 시변 실행 layer(비대칭·조건부 λ)를 기본 추천으로 채택한다. 이는 시장 상태에 따라 매 시점 전략을 제시해야 하는 RA의 기본 의무를 반영한 것이다. 게이트 미통과 시에만 고정 λ(0.1/0.3)를 차선책(fallback)으로 유지하며, 이 경우에도 HSI 상태가 매월 목표비중을 바꾸므로 배분은 시변 적응 전략임을 명시한다(‘고정 λ로 후퇴’가 아니라 ‘동적 층의 증분이 제한적’으로 서술, 과장 금지).",
]));

// ---- PART 2 ----
d1.push(new Paragraph({ pageBreakBefore: true, children: [] }));
d1.push(H1("Part 2. 예비보고서"));

d1.push(H2("2.1 대칭 λ에서 이미 확인된 사실 (실험 10·16·17)"));
d1.push(P("대칭 λ 실험에서 λ가 커질수록 목표비중에 빠르게 다가가 CAGR은 중간(λ≈0.3)에서 정점을 보이고, MDD와 Turnover는 단조적으로 증가했다. 즉 “빠른 반영이 항상 좋은 것은 아니다”가 반복 메시지였고, 그 결과 λ=0.1(저회전·방어)과 λ=0.3(균형)이 남았다."));
d1.push(table(
  ["전략", "CAGR %", "연변동성 %", "MDD %", "Sharpe", "Calmar", "평균 Turnover %", "최대 Turnover %"],
  [
    ["EW Benchmark", "6.51", "7.97", "-13.57", "0.832", "0.480", "0.00", "0.00"],
    ["λ=0.1", "8.66", "11.26", "-14.74", "0.793", "0.587", "2.52", "6.02"],
    ["λ=0.3", "9.09", "12.05", "-15.22", "0.782", "0.597", "6.95", "20.01"],
    ["λ=0.5", "8.58", "12.20", "-17.52", "0.735", "0.490", "11.14", "34.83"],
    ["λ=0.7", "8.07", "12.51", "-19.97", "0.682", "0.404", "15.41", "48.99"],
    ["λ=1.0 (=HSI baseline)", "7.73", "13.67", "-23.46", "0.611", "0.330", "22.09", "70.00"],
  ],
  [2.3, 1.0, 1.25, 1.05, 0.95, 0.95, 1.3, 1.2]
));
d1.push(P("벤치마크 정렬(실험 17)에서 Fixed 70/20/10 BM은 CAGR 약 11.05%로 가장 높지만 MDD도 -25.67%로 가장 깊었다. λ 후보는 CAGR은 낮아도 MDD를 -15% 안팎으로 줄이고 Calmar를 개선했다 — 즉 “수익 극대화”가 아니라 “낙폭 대비 성과 개선”이 λ의 역할이다.", { after: 60 }));
d1.push(P("robustness(실험 16)에서 λ=0.1은 기간별 MDD 우위와 069500 하위 10% 손실월 방어에서, λ=0.3은 전체 CAGR·Calmar에서 강했다. 상태별 평균 월수익률을 보면 risk_relief 구간에서 HSI baseline(즉시 재진입)이 λ 후보보다 높았는데, 이는 “재진입 속도”가 성과 레버라는 단서다."));

d1.push(H2("2.2 비대칭 λ가 필요한 이유"));
d1.push(...BUL([
  "대칭 λ는 위험 축소(de-risking)와 위험 복귀(re-risking)를 같은 속도로 처리한다. 방어형 overlay의 목적(MDD·tail 방어)에 비추면 두 방향의 최적 속도가 같을 이유가 없다.",
  "2.1의 두 단서가 이를 뒷받침한다: (a) risk_relief에서 즉시 재진입한 baseline이 더 높은 평균수익 → 재진입은 빠른 편이 유리할 수 있음(λ_up↑). (b) λ=0.1이 tail-month 방어에 강함 → 위험 축소는 느린 것이 아니라, 오히려 충분히 빠르게 반영돼야 할 수 있음(λ_down↑).",
  "따라서 방어형 기본 가설은 λ_down ≥ λ_up(빠르게 줄이고 신중하게 복귀)이지만, 회복장 비중이 큰 본 표본에서는 λ_up을 너무 낮추면 CAGR이 손해일 수 있어, 두 방향을 분리해 실제 frontier를 확인할 필요가 있다.",
]));

d1.push(H2("2.3 예비 기대(정성적, 단정 아님)"));
d1.push(...BUL([
  "λ_down을 높이면 위기 진입 시 방어 비중으로 빠르게 이동 → tail 방어·MDD 개선, 단 Turnover 일부 증가.",
  "λ_up을 낮추면 상승 재진입이 늦어 회복장 CAGR·Calmar 손실 위험. 최적은 두 값의 특정 조합(frontier 위 영역)일 것.",
  "조건부 λ(E30)는 “평상시 0.3, 고위험 0.1, 안정완화 0.5”처럼 상황별로 속도를 바꿔 비대칭의 이점을 시점에 맞춰 실현하려는 시도.",
]));

d1.push(H2("2.4 팩터로딩 예비 관점 (E24)"));
d1.push(P("비대칭 설계에서 “어느 방향 속도를 조일지”를 감이 아니라 데이터로 정하기 위해, 기존 λ 후보가 시장·채권·모멘텀·변동성·macro 팩터에 어떻게 노출됐는지 먼저 회귀로 확인한다. 예컨대 λ 후보가 변동성 팩터에 음(−)의 노출(위험구간에서 방어)을 보인다면, 그 방어가 de-risking 속도에서 오는지 재진입 지연에서 오는지 구분해 λ_down/λ_up 설계에 반영한다."));

d1.push(H2("2.5 알려진 리스크와 한계"));
d1.push(...BUL([
  "표본이 172개월·자산 3종으로 제한적이라, 파라미터를 늘리는 비대칭·조건부 λ는 과적합 위험이 커진다 → grid를 작게 유지하고 OOS/walk-forward를 필수화한다.",
  "OOS 구간(2021–2026)이 강한 회복장을 포함해, 재진입 속도(λ_up)에 유리하게 편향될 수 있다 → 기간분할·walk-forward로 편향을 드러낸다.",
  "거래비용은 Turnover×비용률의 단순 가정이며 슬리피지·세금·스프레드는 미반영 → 민감도로만 해석한다.",
]));

// ---- PART 3 ----
d1.push(new Paragraph({ pageBreakBefore: true, children: [] }));
d1.push(H1("Part 3. 상세 수행 과정"));

d1.push(H2("3.1 전체 프로세스 구조"));
d1.push(table(
  ["단계", "작업", "상세", "주요 산출물"],
  [
    ["0", "실험 정의", "연구질문·가설·grid 범위 사전 확정", "experiment_plan.md"],
    ["1", "데이터 준비", "ETF 수익률·HSI 상태·목표비중·상태변수·팩터 정렬", "factor_inputs_monthly.csv"],
    ["2", "Baseline 재현", "Fixed BM·EW·HSI baseline·λ=0.1/0.3 재계산·검산", "baseline_check.csv"],
    ["3", "E24 팩터로딩", "전략/초과수익 회귀 + 36개월 rolling", "factor_loading_summary.csv"],
    ["4", "E28 단일 λ", "λ 반응곡선 백테스트", "lambda_response_metrics.csv"],
    ["5", "E29 비대칭 λ", "λ_up/λ_down grid search", "asymmetric_lambda_grid.csv"],
    ["6", "E30 조건부 λ", "규칙 v1 동적 λ 백테스트", "dynamic_lambda_comparison.csv"],
    ["7", "검증", "robustness·IS/OOS·walk-forward·누수 audit", "validation_audit_table.csv"],
    ["8", "후보선별·보고", "채택/보류/제외 + 결과표·그림·한계", "candidate_selection.md / report_sections.md"],
  ],
  [0.6, 1.4, 4.2, 2.6]
));

d1.push(H2("3.2 입력물 분류표"));
d1.push(table(
  ["분류", "입력물", "사용 목적", "주의"],
  [
    ["A. 가격/수익률", "069500·114260·153130 월수익률", "전략수익률·팩터 계산", "월말 기준 정렬"],
    ["B. 상태/비중", "HSI state, 목표비중 w*, 적용비중 w", "λ 적용·상태별 해석", "t월 상태 → t+1월 수익률"],
    ["C. 위험상태변수", "volatility_z, rolling_drawdown, momentum_z, macro_risk_score", "조건부 λ 판단", "rolling/expanding 계산(미래값 금지)"],
    ["D. 비교군", "Fixed BM, EW, HSI baseline, λ=0.1, λ=0.3", "새 후보와 비교", "동일 비용 가정"],
    ["E. 검증 설정", "grid 범위, 비용 bps, IS/OOS split, walk-forward 창", "재현성 확보", "사전 고정, 결과 후 변경 금지"],
    ["F. 팩터", "Market, Bond, Momentum, Volatility, MacroRisk", "E24 팩터로딩", "PIT·lag 처리, z-score는 rolling"],
  ],
  [1.5, 3, 2.4, 2.1]
));

d1.push(H2("3.3 출력물·산출물 분류표"));
d1.push(table(
  ["분류", "파일명", "내용", "용도 / 최종 사용"],
  [
    ["중간", "lambda_response_timeseries.csv", "λ별 월별 수익률·비중·turnover", "E28 검산"],
    ["중간", "lambda_response_metrics.csv", "λ별 CAGR·MDD·Calmar·Turnover", "단일축 후보 확인"],
    ["중간", "asymmetric_lambda_grid.csv", "λ_up/λ_down 조합별 성과", "2D 후보 영역"],
    ["중간", "dynamic_lambda_path.csv", "월별 λ_t와 조건 라벨", "조건부 λ 설명"],
    ["중간", "factor_loading_timeseries.csv", "36개월 rolling β", "노출 변화 해석"],
    ["최종", "candidate_selection_table.csv", "채택/보류/제외 근거", "보고서 본문(사용)"],
    ["최종", "validation_audit_table.csv", "OOS·robustness·leakage 통과 여부", "과적합 방어 근거(사용)"],
    ["최종", "factor_loading_summary.csv", "전략별 팩터 β·유의성", "attribution 절(사용)"],
    ["최종", "experiment_report.md", "실험 해석·결론·한계", "보고서 반영(사용)"],
  ],
  [0.8, 3.4, 3, 2.2]
));

d1.push(H2("3.4 E24 상세 — 팩터로딩 진단"));
d1.push(P("대상 전략(5): Fixed 70/20/10 BM, EW, HSI baseline, λ=0.1, λ=0.3. 종속변수는 (a) 전략 월수익률과 (b) Fixed BM 대비 초과수익률 두 가지를 각각 회귀한다."));
d1.push(P("기본 회귀식:  R_strategy,t − R_BM,t = α + β1·Market + β2·Bond + β3·Momentum + β4·Volatility + β5·MacroRisk + ε.  β가 팩터로딩이며, β4(변동성) 노출이 비대칭 λ 설계의 핵심 단서다.", { after: 60 }));
d1.push(...BUL([
  "전체기간 단일 회귀 + 36개월 rolling regression(24개월은 부록 민감도).",
  "산출물: factor_loading_summary.csv, factor_loading_timeseries.csv, factor_loading_heatmap.png, rolling_factor_exposure_lambda.png, 24_Factor_loading_diagnostic.md.",
  "해석 원칙: 팩터로딩은 ‘설명’이지 ‘예측’이 아니다. 다중공선성(시장-모멘텀, 실현변동성-VKOSPI 등)에 유의하고 1차 팩터는 5개로 제한한다.",
]));

d1.push(H2("3.5 E28 상세 — 단일 λ 반응곡선"));
d1.push(table(
  ["순서", "작업", "주의"],
  [
    ["1", "사전 고정한 λ grid 설정", "범위·간격 결과 후 변경 금지"],
    ["2", "각 λ에 동일 HSI 목표비중·동일 ETF 수익률로 백테스트", "백테스트 함수 동일성 확인"],
    ["3", "CAGR·MDD·Sharpe·Sortino·Calmar·Turnover·비용차감 성과 계산", "CAGR 단독 판단 금지"],
    ["4", "λ 증가에 따른 성과·비용 곡선 형태 확인", "0.1/0.3 위치 표시"],
    ["5", "최고점이 아닌 ‘안정 구간’ 선정", "인접 λ도 함께 확인"],
  ],
  [0.7, 5.5, 2.8]
));

d1.push(H2("3.6 E29 상세 — 비대칭 λ_up/λ_down grid search"));
d1.push(P("계산식(자산 i별):  w_{i,t} = w_{i,t-1} + λ_dir · (w*_{i,t} − w_{i,t-1}).  방향은 위험자산(069500) 목표비중 변화 부호로 판정한다: Δw*_069500 = w*_069500,t − w_069500,t-1 이 음수이면 de-risking → λ_dir = λ_down, 0 이상이면 re-risking → λ_dir = λ_up. 그 달 세 자산에 같은 λ_dir을 적용해 비중 합=1을 유지한다.", { after: 60 }));
d1.push(P("대각선(λ_up = λ_down)은 대칭 λ와 동일하므로 λ=0.1/0.3 참조점이 grid 안에 포함된다.", { after: 60 }));
d1.push(table(
  ["항목", "설정", "설명"],
  [
    ["축 정의", "x = λ_up, y = λ_down, z = 성과지표", "2D heatmap으로 확인"],
    ["탐색 범위", "λ_up, λ_down ∈ {0.10, 0.20, 0.30, 0.50} (16셀)", "대각선=대칭 참조"],
    ["관찰 우선", "λ_down > λ_up 영역(방어형 가설)", "반대 영역도 함께 기록"],
    ["판단 지표", "Calmar·MDD·Turnover·비용차감 성과", "단일 점수만 보지 않음"],
    ["후보 검증", "인접 조합에서도 성과 유지되는지", "고립된 최고점 배제(과적합 완화)"],
  ],
  [1.4, 4.4, 3.2]
));

d1.push(H2("3.7 E30 상세 — 조건부(동적) λ"));
d1.push(P("동적 λ:  w_t = w_{t-1} + λ_t · (w*_t − w_{t-1}).  λ_t는 그 달의 시장 조건으로 결정되며 HSI 상태분류 자체는 바꾸지 않는다.", { after: 60 }));
d1.push(H3("규칙 v1 (IS에서만 threshold 결정)"));
d1.push(table(
  ["조건", "정의", "λ_t"],
  [
    ["고위험", "volatility_z > 1  또는  rolling_drawdown < -10%  또는  macro_risk_score ≥ 2", "0.1 (방어 전환은 빠르게, 재진입은 느리게)"],
    ["안정 완화", "risk_relief 3개월 이상 지속  &  volatility_z < 0  &  momentum_z > 0", "0.5 (확인된 완화 구간에서 반영)"],
    ["그 외", "위 조건에 해당하지 않음", "0.3 (기본)"],
  ],
  [1.4, 5.4, 2.2]
));
d1.push(NOTE("확장(v2, 별도): E29의 방향 분리(λ_up/λ_down)와 E30의 조건부 규칙을 결합해 “조건×방향”별 λ를 줄 수 있으나, 파라미터가 늘어 과적합 위험이 커지므로 v1 통과 후에만 진행한다."));

d1.push(H2("3.8 검증 게이트웨이 (순서 고정)"));
d1.push(P("후보는 아래 게이트를 순서대로 통과할 때만 ‘채택’으로 승격한다. 앞 게이트를 통과하지 못하면 보류/제외로 기록하고 이유를 남긴다."));
d1.push(table(
  ["게이트", "확인 내용", "통과 기준(예시)"],
  [
    ["① 재현·검산", "baseline·대칭 λ 재계산이 기준선 수치와 일치", "λ=0.1/0.3 CAGR·MDD 재현"],
    ["② full-grid(필터 전)", "필터 전 전체 grid 성과를 먼저 표로 제시", "숨김 없이 전량 기록"],
    ["③ Turnover·비용", "Turnover 상한 및 0/5/10/20bp 비용 민감도", "avg_turnover·max_turnover·비용 drag 확인"],
    ["④ robustness", "기간분할(2012–15/16–19/20–22/23–26)·상태별·tail-month·인접 파라미터", "특정 구간·셀 의존 아님"],
    ["⑤ IS/OOS", "IS 설계 → OOS 고정 평가", "OOS에서 대칭 λ 대비 개선 유지"],
    ["⑥ walk-forward", "60개월 점검 → 12개월 평가, 창 이동 반복", "평가 구간 이어붙인 성과 확인"],
    ["⑦ 누수 audit", "시점·rolling·grid 고정·비용 항목 점검표", "전 항목 ‘통과’ 기록"],
    ["⑧ 과적합 점검", "파라미터 수 대비 표본, 인접 안정성, 단일지표 편중 여부", "설명 가능·안정 영역만 채택"],
  ],
  [1.4, 4.6, 3]
));

d1.push(H2("3.9 In-sample / Out-of-sample 및 Walk-forward 설계"));
d1.push(...BUL([
  "단순 분리: IS = 2012-04 ~ 2020-12(약 105개월, ≈60%), OOS = 2021-01 ~ 2026-06(약 66개월, ≈40%). grid·threshold는 IS에서만 결정하고 OOS는 고정 규칙으로만 평가(재조정 금지).",
  "Walk-forward: 앞 60개월로 규칙 점검 → 다음 12개월 평가 → 12개월 이동 → 반복. 평가 12개월 구간들을 이어붙여 OOS-like 성과곡선 산출.",
  "보고 시 IS 성과와 OOS 성과를 나란히 제시하고, 두 구간의 순위 역전 여부를 명시한다.",
]));

d1.push(H2("3.10 데이터 누수·과적합 방지 체크리스트"));
d1.push(table(
  ["항목", "확인 질문", "통과 기록"],
  [
    ["시점 정합", "t월 말 관측값만 사용해 t+1월 수익률에 적용했는가", "☐"],
    ["rolling 계산", "z-score·drawdown 계산에 미래값이 들어가지 않았는가(전구간 분위수 금지)", "☐"],
    ["팩터 PIT/lag", "macro·해외 지표에 발표 시차·전월 lag를 적용했는가", "☐"],
    ["grid 사전고정", "λ 범위·간격·threshold를 결과 확인 후 바꾸지 않았는가", "☐"],
    ["OOS 격리", "OOS 구간을 후보 선정 과정에서 한 번도 사용하지 않았는가", "☐"],
    ["비용 반영", "Turnover와 거래비용 민감도를 함께 확인했는가", "☐"],
    ["다지표 판단", "CAGR 단독이 아니라 MDD·Calmar·Turnover를 함께 봤는가", "☐"],
    ["보고 투명성", "개선되지 않은 결과도 보류/제외로 기록했는가", "☐"],
  ],
  [1.6, 5.4, 1]
));
d1.push(NOTE("과적합 감각(학습자료 연결): degree 15 다항회귀가 학습구간에만 과도하게 맞았던 사례처럼, λ 파라미터를 늘려 특정 구간 성과를 끌어올리는 것을 경계한다. ‘설명 가능하고 인접 조합에서도 안정적인’ 영역만 후보로 남긴다."));

d1.push(H2("3.11 후보 선별 절차"));
d1.push(table(
  ["단계", "기준", "목적"],
  [
    ["1차 필터", "결측·계산오류·비정상 turnover 후보 제거", "기술적 오류 제거"],
    ["2차 필터", "MDD·Turnover가 고정 λ 대비 과도하게 악화된 후보 제외", "방어형 목적 유지"],
    ["3차 필터", "Calmar/비용차감 성과가 인접 후보와 함께 안정적인 영역 확인", "과적합 완화"],
    ["4차 필터", "OOS·walk-forward에서 성과 유지 여부", "일반화 가능성"],
    ["최종 분류", "채택 / 보류 / 제외로 구분하고 근거 기록", "보고서 투명성"],
  ],
  [1.2, 5.2, 2.6]
));

d1.push(H2("3.12 팀 역할 분담"));
d1.push(table(
  ["역할", "주요 작업", "책임"],
  [
    ["데이터 담당", "ETF 수익률·HSI 상태·상태변수·팩터 정렬, 결측·PIT 확인", "입력 데이터 품질"],
    ["실험 담당", "E24·28·29·30 백테스트 함수 실행·결과 저장", "재현 가능한 실행"],
    ["검증 담당", "robustness·IS/OOS·walk-forward·비용 민감도·누수 audit", "후보 검증"],
    ["문서 담당", "후보선별표·결과표·한계·결론 작성, 결과보고서 반영", "보고서 반영"],
  ],
  [1.4, 5.4, 2.2]
));

d1.push(H2("3.13 수행 문서 결론"));
d1.push(P("본 문서는 λ_up과 λ_down을 분리한 비대칭 구조, 그리고 시장 조건에 따른 조건부 λ가 방어형 RA 목적과 어떻게 연결되는지를 사전에 정의한다. RA는 시장 상태에 따라 매 시점 전략을 제시하고 사용자 성향(방어적 참여자)에 맞춰 추천할 의무가 있으므로, 판정은 우월성 입증이 아니라 사전등록 비열등(non-inferiority) 기준을 따른다: 시변 실행 layer가 대칭 λ 대비 비열등하고 재현·full-grid·Turnover/비용·robustness·IS/OOS·walk-forward·누수 audit·과적합 점검의 8개 게이트를 통과하면 기본 추천 layer로 채택한다. 게이트 미통과 시에만 고정 λ(0.1/0.3)를 차선책으로 유지하되, 그 경우에도 HSI 상태가 매월 목표비중을 바꾸므로 배분 자체는 시변 적응 전략(1차 적응)임을 함께 서술한다."));

d1.push(H1("부록 A. 재현 실행 순서와 산출물 경로"));
d1.push(...BUL([
  "실행 순서: 24_factor_loading_diagnostic → 28_lambda_response_curve → 29_asymmetric_lambda_grid → 30_dynamic_lambda_rule_v1 → validation(OOS·walk-forward·leakage).",
  "저장 경로 규약: 원천/가공 = data/processed, 표 = output/tables (파일명 접두 main_final_*), 그림 = output/figures, 보고 md = docs/ 또는 reports/.",
  "산출물 접두 규칙: 최종 보고에 쓰는 파일만 main_final_* 사용, 중간·검토 파일은 flex_/sample_ 등으로 구분(발표 본문 사용 금지).",
]));

// =====================================================================
// DOCUMENT 2 — 결과보고서 구성틀
// =====================================================================
const d2 = [];
d2.push(...cover(
  "HSI RoboAdvisor · 비대칭 Lambda 결과보고서 구성틀",
  "독자가 실험 과정을 감사(audit)할 수 있는 결과보고서 스켈레톤 (v2)",
  "AIQuant 2차 프로젝트 · 후속 실험 · 팀 공유/제출용 · 2026-07"
));

d2.push(H1("0. 이 구성틀의 사용법"));
d2.push(P("본 문서는 비대칭·조건부 λ 실험의 결과보고서를 채우기 위한 틀이다. 각 섹션에는 (a) 목적, (b) 넣을 내용, (c) 표·그림 자리(placeholder), (d) 작성 시 주의를 함께 적었다. 핵심 목표는 “읽는 사람이 계획 → 데이터 → 실험 → 후보 → 검증 → 결론의 흐름을 되짚으며 과적합·데이터 누수가 없었는지 확인할 수 있게” 만드는 것이다."));
d2.push(NOTE("작성 원칙: 과장된 완료 표현을 피하고, 검증 가능한 설계와 산출물 중심으로 쓴다. 개선되지 않은 결과도 그대로 기록한다."));

d2.push(H1("1. 요약 (Executive Summary)"));
d2.push(P("목적: 무엇을·왜·어떤 결론인지 한 문단으로.", { bold: true }));
d2.push(...BUL([
  "넣을 내용: 연구 질문 1~2줄, 최종 판단(비대칭/조건부 λ를 후속 후보로 둘지 or 고정 λ 유지), 근거 지표 한 줄.",
  "표 자리: [요약 표 — 실험 24/28/29/30별 목적·핵심결과·역할].",
  "주의: “최적 전략을 찾았다”가 아니라 “검증 가능한 후보를 선별/검토했다”로 표현.",
]));

d2.push(H1("2. 배경과 연구 질문"));
d2.push(...BUL([
  "넣을 내용: 고정 λ=0.1/0.3의 위치(sensitivity 결과이지 optimizer 단일해 아님), 실험 15의 동적 λ 후속 제안, 비대칭 λ 동기.",
  "연구 질문 RQ1~RQ4(비대칭 개선 여부, 방어형 방향 가설, 조건부 λ 추가효과, OOS 유지 여부).",
  "주의: HSI는 예측기가 아니라 시장상태 해석 지표라는 정의를 재확인.",
]));

d2.push(H1("3. 데이터와 실험 설정"));
d2.push(P("목적: 재현 가능성 확보 — 무엇을 고정했는지 명시.", { bold: true }));
d2.push(...BUL([
  "넣을 내용: 유니버스 3종, 기간(2012-03~2026-06), 월간 리밸런싱, 월말 신호→t+1 수익률, 단위(decimal→%), 비교군 4층, 거래비용 가정.",
  "표 자리: [고정 요소 표], [사전 등록 grid 표(E28/E29/E30 범위와 셀 수)].",
  "주의: 성과 기준선 수치를 한 convention으로 통일(실험 10/20~23 계열 사용, 16/17 재계산 반영).",
]));

d2.push(H1("4. 입력·출력·산출물 구조표"));
d2.push(...BUL([
  "넣을 내용: 입력물 분류(A 가격/수익률 ~ F 팩터), 출력물/산출물 분류(중간·최종), 각 파일의 용도와 최종 사용 여부.",
  "표 자리: [입력물 분류표], [출력물·산출물 분류표].",
  "주의: rolling/PIT 처리 대상 컬럼을 표에 명시(누수 방지 근거).",
]));

d2.push(H1("5. 방법론"));
d2.push(...BUL([
  "5.1 대칭 λ 복습: w_t = w_{t-1} + λ·(w*_t − w_{t-1}), λ family 결과 요약.",
  "5.2 비대칭 λ 정의: 방향 판정(Δw*_069500 부호) → λ_up/λ_down, 대각선=대칭.",
  "5.3 조건부 λ 규칙 v1: 고위험→0.1, 안정완화→0.5, 그 외 0.3(threshold는 IS 결정).",
  "5.4 팩터로딩 진단(E24): 회귀식과 36개월 rolling.",
  "주의: 각 수식과 규칙의 threshold 출처(IS 구간)를 반드시 기재.",
]));

d2.push(H1("6. 실험 결과"));
d2.push(H2("6.1 E24 — 팩터로딩 진단"));
d2.push(...BUL([
  "그림 자리: [factor_loading_heatmap.png], [rolling_factor_exposure_lambda.png].",
  "표 자리: [전략별 β(Market/Bond/Momentum/Volatility/MacroRisk)·유의성].",
  "해석: λ 후보가 baseline 대비 시장·변동성 노출이 낮은지, 그 방어가 어느 방향 속도에서 오는지.",
]));
d2.push(H2("6.2 E28 — 단일 λ 반응곡선"));
d2.push(...BUL([
  "그림 자리: [λ vs CAGR/Turnover 곡선], [λ vs MDD].",
  "해석: 0.1/0.3 위치, 안정 구간, ‘빠른 반영이 항상 좋지는 않음’ 재확인.",
]));
d2.push(H2("6.3 E29 — 비대칭 λ_up/λ_down grid"));
d2.push(...BUL([
  "그림 자리: [λ_up×λ_down heatmap — Calmar], [heatmap — MDD], [heatmap — Turnover].",
  "표 자리: [상위 조합과 대칭 λ 대비 trade-off].",
  "해석: λ_down>λ_up 영역이 실제로 유리한지, 고립된 최고점 여부.",
]));
d2.push(H2("6.4 E30 — 조건부 동적 λ"));
d2.push(...BUL([
  "표 자리: [Dynamic λ v1 vs 고정 λ=0.1/0.3 vs BM 성과 비교], [월별 λ_t 경로 예시].",
  "해석: 조건부 λ가 비대칭 대비 추가 개선을 주는지, Turnover·비용 대가.",
]));

d2.push(H1("7. 후보 선별"));
d2.push(...BUL([
  "넣을 내용: 4차 필터 통과 과정, 채택/보류/제외 분류와 근거.",
  "표 자리: [candidate shortlist — CAGR·MDD·Sharpe·Calmar·Turnover·20bp drag·판정·사유].",
  "주의: 채택 근거를 ‘대칭 λ 대비 trade-off 개선 + OOS 유지’로 명시.",
]));

d2.push(H1("8. 검증 및 과적합·데이터 누수 방어 (Audit Trail)"));
d2.push(P("목적: 이 보고서의 신뢰성 핵심 — 독자가 결론을 그대로 감사할 수 있는 증거 구간.", { bold: true }));
d2.push(H2("8.1 Full-grid vs 필터 후"));
d2.push(...BUL(["표 자리: [필터 전 전체 grid 성과] → [필터 후 후보]. 숨김 없이 전량 먼저 제시."]));
d2.push(H2("8.2 Turnover 상한 · 거래비용 민감도"));
d2.push(...BUL(["표 자리: [0/5/10/20bp CAGR drag], [avg/max Turnover]. 비용 증가에도 후보가 버티는지."]));
d2.push(H2("8.3 Robustness"));
d2.push(...BUL(["표/그림 자리: [기간분할(2012–15/16–19/20–22/23–26) 성과], [HSI 상태별], [tail-month 방어]. 특정 구간 의존 여부."]));
d2.push(H2("8.4 In-sample / Out-of-sample"));
d2.push(...BUL(["표 자리: [IS 성과] vs [OOS 성과] 나란히. 순위 역전·과적합 신호 명시."]));
d2.push(H2("8.5 Walk-forward"));
d2.push(...BUL(["그림/표 자리: [walk-forward OOS-like 성과곡선], [창별 평가 성과]."]));
d2.push(H2("8.6 데이터 누수 audit 체크표"));
d2.push(table(
  ["항목", "확인", "결과"],
  [
    ["시점 정합(t 신호→t+1 수익)", "월말 관측만 사용", "☐ 통과 / ☐ 조치"],
    ["rolling 계산", "전구간 분위수·미래값 미사용", "☐ 통과 / ☐ 조치"],
    ["팩터 PIT/lag", "발표 시차·전월 lag 적용", "☐ 통과 / ☐ 조치"],
    ["grid·threshold 사전고정", "결과 후 변경 없음", "☐ 통과 / ☐ 조치"],
    ["OOS 격리", "선정 과정 미사용", "☐ 통과 / ☐ 조치"],
  ],
  [3.2, 3.8, 2]
));

d2.push(H1("9. 결론과 한계"));
d2.push(...BUL([
  "넣을 내용: 사전등록 비열등 판정 결과를 명확히(채택된 시변 layer 또는 fallback 사유). fallback 시에도 배분은 HSI 상태 기반 시변 전략임을 함께 서술하고, ‘동적 층의 증분이 제한적’으로 기록.",
  "한계: 표본 기간·자산 3종·OOS 회복장 편향·거래비용 단순화·규칙 threshold의 임의성.",
  "주의: 단일 우승 전략 주장 금지. 투자 목적별 후보(보수형/균형형) 구분 유지.",
]));

d2.push(H1("10. 후속 과제"));
d2.push(...BUL([
  "θ × λ 결합 제한 Grid Search(현재 θ·λ 분리 실험).",
  "조건×방향 결합 λ(v2), 상태-의존 λ 확장.",
  "팩터 후속 후보(장단기 금리차·주식-채권 상관 레짐·VKOSPI·환율·신용스프레드·외국인 순매수) 도입 검토.",
  "유니버스 확장(3종 → 자산군/해외)과 conflict 상태 표본 부족 재검토.",
]));

d2.push(H1("부록 A. 재현 실행 순서와 산출물 목록"));
d2.push(...BUL([
  "실행: 24 → 28 → 29 → 30 → 검증(OOS·walk-forward·leakage).",
  "산출물: factor_loading_*, lambda_response_*, asymmetric_lambda_grid, dynamic_lambda_comparison, candidate_selection_table, validation_audit_table.",
]));
d2.push(H1("부록 B. 용어"));
d2.push(...BUL([
  "λ / λ_up / λ_down / 조건부 λ, In-sample / Out-of-sample / Walk-forward, Robustness, 데이터 누수, 팩터로딩 — (본문 정의 참조).",
]));
d2.push(H1("부록 C. 발표용 핵심 문장과 피해야 할 표현"));
d2.push(table(
  ["피해야 할 표현", "대신 쓸 표현"],
  [
    ["비대칭 λ가 최종 우승 모델이다", "비대칭 λ는 대칭 λ와 동일 기준·OOS에서 비교한 후속 후보다"],
    ["동적 λ가 성과를 개선했다", "동적 λ는 (개선/제한적)이었고, trade-off와 OOS 유지로 판단했다"],
    ["HSI가 미래 수익률을 예측했다", "HSI가 시장상태를 해석했고, λ는 반영 속도를 조절했다"],
    ["Grid Search로 최고 CAGR을 찾았다", "다지표·인접 안정성·OOS로 후보를 선별했다(CAGR 1등 아님)"],
  ],
  [4.5, 4.5]
));

// ---------- write ----------
function build(children, title) {
  return new Document({
    creator: "AIQuant HSI RA Project",
    title,
    styles: baseStyles,
    numbering: numberingConfig,
    sections: [{ properties: { page: pageA4 }, children }],
  });
}
(async () => {
  const outDir = "/mnt/user-data/outputs";
  fs.mkdirSync(outDir, { recursive: true });
  const doc1 = build(d1, "HSI RA 비대칭 Lambda 상세 수행 문서 v2");
  const doc2 = build(d2, "HSI RA 비대칭 Lambda 결과보고서 구성틀 v2");
  fs.writeFileSync(`${outDir}/HSI_RA_비대칭람다_상세수행문서_v2.docx`, await Packer.toBuffer(doc1));
  fs.writeFileSync(`${outDir}/HSI_RA_비대칭람다_결과보고서_구성틀_v2.docx`, await Packer.toBuffer(doc2));
  console.log("WROTE both docx files to", outDir);
})();
