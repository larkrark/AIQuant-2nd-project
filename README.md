# AIQuant-2nd-project

AIQuant 2차 프로젝트 작업 저장소입니다. 현재 흐름은 한국 상장 ETF 가격 데이터를 기반으로 HSI(Hourglass Signal Index) 시장 상태 지표를 생성하고, 이를 market timing 보조 신호로 활용할 수 있는지 검토하는 방향입니다.

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
