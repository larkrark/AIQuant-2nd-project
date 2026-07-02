"""
프로젝트 공통 경로 상수.

기존 스크립트들이 각자 `Path(__file__).resolve().parents[1]`로 계산하고
`PROJECT_DIR` / `ROOT_DIR` / `PROJECT_ROOT`로 제각각 부르던 경로를 한곳으로 통일한다.

이 파일 위치는 `src/common/paths.py`이므로 프로젝트 루트는 parents[2]다.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 데이터
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"

# 산출물
OUTPUT_DIR = PROJECT_ROOT / "output"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"

# 문서
DOCS_DIR = PROJECT_ROOT / "docs"
