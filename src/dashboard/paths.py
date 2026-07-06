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

# hsi_report_artifacts 해체 후 root 구조로 통합 (2026-07-06 정리)
# manifest의 repo_path가 ROOT 기준 상대경로이므로 ARTIFACTS_DIR = ROOT
ARTIFACTS_DIR = ROOT
ARTIFACT_REPORT_DIR = ROOT / "docs" / "reports"
ARTIFACT_NOTE_DIR = ROOT / "docs" / "experiment_notes"
ARTIFACT_TABLE_DIR = ROOT / "output" / "tables"
ARTIFACT_FIGURE_DIR = ROOT / "output" / "figures"
ARTIFACT_META_DIR = ROOT / "output" / "streamlit" / "artifacts_meta"
