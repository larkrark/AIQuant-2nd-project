# AIQuant-2nd-project

AIQuant 2차 프로젝트 작업 저장소입니다. 현재 흐름은 한국 상장 ETF 가격 데이터를 기반으로 HSI(Hourglass Signal Index) 시장 상태 지표를 생성하고, 이를 market timing 보조 신호로 활용할 수 있는지 검토하는 방향입니다.

## 🔧 최근 대규모 업데이트 (2026-07-06): 구조 리팩터링 · RA 확장 · 작업환경 주의

> 다른 조원 및 후속 에이전트를 위한 요약. 상세는 `docs/` 관련 문서 참조.

### 1) src/ 구조 재편
```
src/
├── common/     공통 모듈 (paths·config·io_utils·viz·metrics·backtest)
├── pipeline/   새 파이프라인 (리포트 00~17·20~23 반영)
├── dashboard/  Streamlit 대시보드
├── legacy/     과거 00~30 + portfolio_optimizer (복구용 보존)
└── tests/      pytest
```
- 옛 번호 스크립트(main_v2/flex/v3 계열)는 `src/legacy/`로 이동(경로 깊이만 보정). 구조 설명: `src/STRUCTURE.md`.
- 최상위 `20~23_*` 스크립트는 조원 최종 리포트/선별 원본(참조용), 로직은 `pipeline/`으로 이식됨.

### 2) 새 파이프라인 (`src/pipeline`) — 단계 지도: `cd src && python3 -m pipeline.run`
- 구현: `stage_d_lambda`(λ 부분조정), `stage_g_benchmark`(Fixed 70/20/10), `stage_selection`(비용·Turnover 선별), `stage_factor`(팩터 로딩), `stage_attribution`(성과 기여도).
- 스텁(데이터 인제스트 후 구현): `stage_a_data`, `stage_b_hsi`, `stage_c_diagnostics`, `stage_e_macro`, `stage_f_robustness`.

### 3) RA(로보어드바이저) 확장 — 신규
- `stage_factor.py`: 팩터 로딩 회귀(β·t-stat·R²·VIF·36개월 rolling), expanding z-score·시차로 룩어헤드 차단.
- `stage_attribution.py`: EW 대비 초과수익 = SAA + 타이밍 + λ smoothing + 비용 (가법 항등식 분해).
- 대시보드 "팩터·기여도" 페이지 추가: `streamlit run streamlit_app.py`.

### 4) 테스트
```
cd src && python3 -m pytest tests/ -q     # 30 passing
```
모든 신규 로직은 numpy/pandas 합성 데이터로 검증됨(외부 데이터 불필요).

### 5) 실행에 필요한 미보유 데이터 (0단계 = 데이터 인제스트)
- `data/processed/main_final_*_backtest_timeseries.csv` (조원 20_select 등 최종 스크립트 입력)
- `data/factors/monthly_factors.csv` (팩터 원자료 — ECOS 무료: 회사채/국고 수익률·금리, KRX: VKOSPI·거래대금)
→ 이 데이터가 채워지면 `stage_selection`/`stage_factor`/`stage_attribution`이 실제 값으로 실행됨.

### 6) ⚠️ 작업환경 주의 (에이전트 필독)
- 일부 편집이 **샌드박스 마운트**를 통해 이뤄졌고, 그 환경에서 **(a) git 커밋 불가, (b) 파일 저장 시 간헐적 손상**(트레일링 널바이트·유령 코드 조각 주입)이 발생함.
- 따라서 편집 후 **반드시 `python -m py_compile` + `pytest`로 검증**하고, 파일이 손상돼 보이면 **`_backups/src_<타임스탬프>/` 스냅샷에서 복구**할 것.
- **커밋은 반드시 PC 네이티브 git에서** 수행(샌드박스 불가). 관련: `docs/git_복구_및_커밋_안전장치_2026-07-03.md`.
- 위험 작업 전 스냅샷: `bash backup_src.sh`.

### 7) 관련 문서
- `docs/RA_확장성_검토_2026-07-03.md` — RA 요구사항 충족도·갭
- `docs/meetings/HSI_RA_팩터후보_통합표_2026-07-03.md` — 팩터 후보(기본+추가, 팀검토 반영)
- `docs/팩터_파이프라인_시각화_반영_설계_2026-07-03.md` — 팩터 반영 설계
- `docs/src_common_리팩터링_요약_2026-07-02.md`, `docs/src_파이프라인_코드분석_개선방향_2026-07-02.md`


## 최근 업데이트

- `practice/` 실습 폴더를 추가했습니다.
- `practice/hsi_indicator_generation_practice.ipynb`에 HSI 지표 생성 흐름을 노트북 형태로 정리했습니다.
- 노트북 흐름은 ETF 가격 데이터 점검, 일별 사건 등급 분류, 월별 사건 카운트, 가격 기반 HSI 입력 지표 생성, HSI 상태 라벨 생성, 사건 구간별 상태 확인 순서입니다.
- 실습 노트북의 생성 결과는 `practice/output/`에 저장되며 Git에는 올리지 않습니다.
- 새 Python 가상환경은 `.venv/`를 사용합니다.
- 대용량 원천 데이터 폴더 `data/raw/AI퀀트분석데이터셋/`은 로컬 분석용으로 두고 Git에는 올리지 않습니다.
- PDF, DOCX, PPTX 문서는 GitHub 용량과 diff 관리를 위해 원본 대신 `docs/lightweight/`의 Markdown 추출본을 올립니다.

## 가상환경 사용

PowerShell 기준:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install -r requirements.txt
```

현재 `.venv`에는 HSI 실습 노트북 실행에 필요한 `pandas`, `numpy`, `ipykernel`이 설치되어 있습니다.

시각화 스크립트(`src/06_visualize_event_waves.py`, `src/09_visualize_hsi_event_annotations.py`, `src/10_visualize_hsi_hourglass_cone.py`)를 실행하려면 `matplotlib`이 필요합니다. 포트폴리오 GUI(`src/portfolio_optimizer.py`)를 실행하려면 `PyQt5`가 추가로 필요할 수 있습니다.

## HSI 원뿔형 시각화

이미지 참고자료의 모래시계/원뿔형 구조를 실제 HSI 입력 지표와 연결하기 위해 다음 스크립트를 추가했습니다.

```powershell
python src\10_visualize_hsi_hourglass_cone.py
```

특정 월이나 티커를 지정할 수도 있습니다.

```powershell
python src\10_visualize_hsi_hourglass_cone.py --month 2026-06 --ticker 229200
```

생성 파일 예시:

- `output/figures/fig16_hsi_hourglass_cone_2026-06_229200.png`
- `output/figures/fig16_hsi_hourglass_cone_2026-06_229200.svg`
- `output/tables/fig16_hsi_hourglass_cone_2026-06_229200_vectors.csv`

시각화 스크립트는 Windows의 `Malgun Gothic`을 우선 사용하고, 없으면 Nanum/Noto 계열 한글 폰트를 찾아 사용합니다.

## HSI 실습 노트북

실습 노트북:

```text
practice/hsi_indicator_generation_practice.ipynb
```

노트북은 원본 `output/` 폴더를 덮어쓰지 않고 다음 경로에 실습 결과를 생성합니다.

```text
practice/output/
```

주요 생성 파일:

- `korea_etf_price_clean_practice.csv`
- `daily_event_labels_practice.csv`
- `monthly_event_counts_practice.csv`
- `monthly_hsi_inputs_practice.csv`
- `monthly_hsi_state_labels_practice.csv`
- `monthly_hsi_state_summary_practice.csv`
- `event_period_state_check_practice.csv`

## 데이터 관리 기준

Git에 포함하는 자료:

- 프로젝트 실행에 필요한 소형 원천 데이터
- HSI 핵심 코드
- 문서 및 회의록
- 발표/공유용 요약 결과표와 그림
- 실습 노트북

Git에서 제외하는 자료:

- `.venv/`
- `practice/output/`
- `data/raw/AI퀀트분석데이터셋/`
- `docs/` 아래의 PDF, DOCX, PPTX 원본 문서
- 재생성 가능한 HSI 중간 CSV 파일

대용량 엑셀 원천 데이터는 로컬에 보관하고, 필요한 경우 전처리 결과만 별도 CSV로 추출해 사용합니다.

문서 원본은 로컬에 보관하고, GitHub에는 다음 폴더의 경량 Markdown 추출본을 사용합니다.

```text
docs/lightweight/
```

## Figure 관리 기준

본 프로젝트에는 초기 prototype 실험에서 생성된 그림과 최종 보고서용 그림이 함께 존재한다.  
최종 보고서와 발표에서는 `output/figures/report_final/` 폴더의 그림만 사용한다.

`output/figures/archive_prototype/` 폴더에는 00~36번 prototype 실험, main_v2 계열 실험, P/S wave 및 event pressure 계열 시각화가 보존되어 있다. 이 그림들은 프로젝트 아이디어 발전 과정을 보여주는 참고 자료이지만, 최종 성과 판단이나 발표용 근거로 사용하지 않는다.

특히 최종 프로젝트 기준은 `direction / intensity / conflict / HSI 5상태 / λ overlay` 구조이며, 과거 prototype 그림은 이 기준과 용어 또는 계산 흐름이 다를 수 있으므로 본문 결과와 혼용하지 않는다.
