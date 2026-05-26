#!/usr/bin/env bash
# Build a distributable Google Image Search.alfredworkflow file.
#
# Usage:
#   ./scripts/package.sh           # writes dist/Google Image Search.alfredworkflow
#   ./scripts/package.sh out.zip   # writes to the given path
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="${ROOT}/dist"
OUT="${1:-${DIST_DIR}/Google Image Search.alfredworkflow}"

if [[ ! -f "${ROOT}/info.plist" ]]; then
  echo "error: info.plist not found in ${ROOT}" >&2
  exit 1
fi

/usr/bin/plutil -lint "${ROOT}/info.plist" >/dev/null

mkdir -p "$(dirname "${OUT}")"
rm -f "${OUT}"

cd "${ROOT}"

INCLUDES=(info.plist README.md icons workflow)
for path in "${INCLUDES[@]}"; do
  if [[ ! -e "${path}" ]]; then
    echo "error: missing required path: ${path}" >&2
    exit 1
  fi
done

# Strip bytecode and editor cruft before packaging.
find workflow tests -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true

/usr/bin/zip -r -q -X "${OUT}" \
  "${INCLUDES[@]}" \
  -x "*/__pycache__/*" "*.pyc" ".DS_Store"

SIZE_BYTES="$(/usr/bin/stat -f%z "${OUT}")"
printf 'built %s (%d bytes)\n' "${OUT}" "${SIZE_BYTES}"
