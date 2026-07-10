# HSI RA · 비대칭/조건부 Lambda 후속 실험 코드 (E24/E28/E29/E30 + 검증)

근거 문서: `HSI_RA_비대칭람다_상세수행문서_v2` (v1의 [D-x] 미결 해소본을 기준으로 구현)

## 폴더 구조 (기존 Git 규약과 동일)

```
hsi_lambda/
├── data/processed/          # 입력 (Git에서 복사해 넣을 것)
│   ├── main_final_monthly_return_decimal.csv        # 필수
│   ├── main_final_baseline_rebalance_weights.csv    # 필수
│   └── factor_inputs_monthly.csv                    # E24·E30 macro용 (선택)
├── src/
│   ├── config.py                        # 사전등록 고정값 (결과 후 변경 금지)
│   ├── common.py                        # 로딩·백테스트 엔진·성과지표
│   ├── 00_smoke_test.py                 # 합성데이터 기계 검증 (T1~T6)
│   ├── 24_factor_loading_diagnostic.py  # E24 (팩터 파일 있을 때만)
│   ├── 28_lambda_response_curve.py      # E28 + 게이트 ① 재현 대조
│   ├── 29_asymmetric_lambda_grid.py     # E29 full-grid 16셀 (게이트 ②③)
│   ├── 30_dynamic_lambda_rule_v1.py     # E30 규칙 v1
│   └── 31_validation.py                 # 게이트 ④⑤⑥⑦ (IS/OOS·WF·audit)
├── output/tables/   # main_final_* = 최종 보고용, flex_* = 중간·검토용
├── output/figures/
└── reports/
```

## 실행 순서

```bash
cd src
python 00_smoke_test.py                  # 기계 검증 (데이터 없이 가능) — 전부 PASS 확인됨
# 데이터 배치 후:
python 28_lambda_response_curve.py       # 게이트 ① 대조 출력을 반드시 확인
python 29_asymmetric_lambda_grid.py
python 30_dynamic_lambda_rule_v1.py
python 31_validation.py
python 24_factor_loading_diagnostic.py   # factor_inputs_monthly.csv 확보 후
```

## 입력 스키마

`main_final_monthly_return_decimal.csv`: index=월말 Date, 열 `069500,114260,153130`, decimal 월수익률.
% 단위가 들어오면 로더가 에러로 차단한다.

`main_final_baseline_rebalance_weights.csv`: index=신호월(월말). 다음 둘 중 하나.
- `hsi_state` 열 (risk_relief / neutral_watch / conflict / risk_warning / accident_zone / insufficient_data) → config의 상태별 w*로 매핑
- `w_star_069500, w_star_114260, w_star_153130` 열 직접 제공 (`hsi_state`도 있으면 E30 상태지속 판정에 사용)

`factor_inputs_monthly.csv` (선택): 열 `Market, Bond, Momentum, Volatility, MacroRisk`
(+ E30용 `macro_risk_score`). PIT·전월 lag는 이 파일 생성 단계에서 처리할 것.

## 구현이 문서 대비 확정/보완한 사항 (팀 공유 필요)

1. **방향 판정 기호**: 문서의 "Δw*"는 실제로는 `Δ_t = w*_{069500,t} − w_{069500,t-1}`(직전 **실제**비중 기준)
   이며 코드도 그렇게 구현했다. Δ<0 → λ_down, Δ≥0 → λ_up. 문서 v3에서 기호를 Δ_t로 수정 권장.
2. **Turnover = Σ|Δw|/2**: 기존 표의 λ=1 최대 Turnover 70.00%(risk_relief→accident_zone 점프)를
   정확히 재현하는 규약임을 합성 테스트(T2)로 확인.
3. **w_0 = 첫 유효 신호월의 w***: E28의 λ=0 퇴화 방지. λ=0은 초기비중 고정 보유가 되므로
   반응곡선의 좌측 끝 참조점으로만 해석한다.
4. **Sharpe 규약 2종 병기**: `sharpe`(산술연환산, 기존 표 EW 0.832와 정합 추정) / `sharpe_geom`(CAGR/vol).
   게이트 ①에서 실데이터로 어느 쪽이 기존 표와 일치하는지 확정 후 보고서에 하나만 사용.
5. **insufficient_data = 직전 실제비중 유지**, 월중 비중 drift 미반영(문서 계산식 그대로) — 한계로 명시.
6. **E30 상태변수 창**: vol 12M rolling ann.(√12), z는 36M rolling, drawdown 12M, momentum 12-1.
   전부 config에 있고 **IS에서만 조정 가능**. macro_risk_score 미확보 시 해당 조건 자동 비활성+기록.
7. **게이트 ① 수치 드리프트**: E28이 convention A(6.51/8.66/9.09)와 B(6.59/8.69/9.15)를 모두 대조
   출력한다. 실데이터 실행 후 일치하는 convention으로 모든 표를 고정할 것(강의요건 보고서 §4.1).

## 남은 팀 결정 사항 (코드 실행을 막지 않음)

- [D-C3] E24 팩터 대용치 확정 (Market=KOSPI200 초과수익, Volatility=실현변동성 vs VKOSPI 등)
- [D-A2] SAA 앵커 언어화 (중립상태 50/35/15 권장) — 보고서 서술용
- 31_validation의 `CANDIDATES` 목록: E29 full-grid 결과를 본 뒤 인접 안정 영역 기준으로
  확정(추가·삭제 이력을 주석으로 기록 — 게이트 ⑦)

## v3 추가분 (팀 검수 반영)

- `config.ADOPTION_RULE`: 사전등록 **비열등 채택규칙**. RA의 시변 전략 의무를 반영해
  입증 부담을 뒤집음 — 시변 layer(비대칭·조건부 λ)가 OOS·10bp net 기준 4개 마진을
  만족하고 8게이트를 통과하면 **기본 추천 layer로 채택**, 고정 λ는 fallback.
  마진: Calmar ≥ 대칭최우수×0.9 / MDD 악화 ≤ 2%p / tail 악화 ≤ 0.3%p / TO ≤ 대칭0.3×1.5.
  (결과를 본 뒤 마진 변경 금지 — 변경 시 사유·일자 주석)
- `33_report_outputs.py`: **리밸런싱 일자별 포트폴리오 구성내역** CSV(전략별) +
  **IS/OOS/FULL 누적수익률·변동성·MDD·Sharpe 비교표와 차트**(전략 vs Fixed BM vs EW),
  drawdown 차트.
- `34_adoption_decision.py`: 채택규칙 자동 판정표(main_final_adoption_decision.csv).
- `build_docs_v3.js`: v2 docx의 "개선 제한적 → 고정 λ 유지" 문구 3곳(§1.7, §3.13,
  구성틀 §9)을 비열등 결정규칙 서술로 치환한 문서 생성기. `node build_docs_v3.js`로 재생성.

실행 순서(전체): 00 → 28 → 29 → 32 → 30 → 31 → 34 → 33 → (24는 팩터 확보 시)
