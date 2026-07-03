#!/usr/bin/env bash
# src/ 스냅샷 백업 스크립트 (git과 무관한 안전장치)
#
# 사용법:
#   bash backup_src.sh
# 결과:
#   _backups/src_<날짜시간>/ 에 src/ 전체 복사 (__pycache__, .pytest_cache 제외)
#
# 위험한 작업(merge/reset/대규모 리팩터링) 전에 실행해 두면
# git 상태와 무관하게 언제든 복구할 수 있다.

set -euo pipefail
cd "$(dirname "$0")"

TS="$(date +%Y%m%d_%H%M%S)"
DEST="_backups/src_${TS}"
mkdir -p "$DEST"

if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude='__pycache__' --exclude='.pytest_cache' src/ "$DEST/"
else
  cp -r src/* "$DEST/"
  find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
fi

echo "백업 완료: $DEST"
find "$DEST" -name '*.py' | wc -l | xargs echo "백업된 .py 개수:"
