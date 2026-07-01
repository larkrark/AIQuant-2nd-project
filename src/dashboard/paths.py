from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

HSI_CANDIDATE_DATA_DIR = ROOT / "data" / "processed" / "hsi_candidates"
HSI_CANDIDATE_OUTPUT_DIR = ROOT / "output" / "streamlit" / "hsi_candidates"

MIDTERM_VERSION = "20260630_state5_midterm"
MIDTERM_DIR = ROOT / "output" / "presentation" / MIDTERM_VERSION
MIDTERM_TABLE_DIR = MIDTERM_DIR / "tables"
MIDTERM_FIGURE_DIR = MIDTERM_DIR / "figures"
LEGACY_TABLE_DIR = ROOT / "output" / "tables"
LEGACY_FIGURE_DIR = ROOT / "output" / "figures"

