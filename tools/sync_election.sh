#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Facade
SRC_FACADE="$ROOT_DIR/backend/election.py"
DST_FACADE="$ROOT_DIR/frontend/backend/election.py"

# Model packages
SRC_MODELS_DIR="$ROOT_DIR/backend/election_models"
DST_MODELS_DIR="$ROOT_DIR/frontend/backend/election_models"


set -euo pipefail

if [[ ! -f "$SRC_FACADE" ]]; then
  echo "Source not found: $SRC_FACADE" >&2; exit 1
fi
cp -f "$SRC_FACADE" "$DST_FACADE"
echo "Synced: $SRC_FACADE -> $DST_FACADE"

if [[ -d "$SRC_MODELS_DIR" ]]; then
  mkdir -p "$DST_MODELS_DIR"
  cp -rf "$SRC_MODELS_DIR/"* "$DST_MODELS_DIR/"
  echo "Synced: $SRC_MODELS_DIR -> $DST_MODELS_DIR"
fi

:
