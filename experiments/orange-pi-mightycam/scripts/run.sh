#!/usr/bin/env bash
set -euo pipefail
experiment_dir="$(cd "$(dirname "$0")/.." && pwd)"
repo_dir="$(cd "$experiment_dir/../.." && pwd)"
profile="${1:-demo}"
case "$profile" in mighty|demo|full-bench) ;; *) echo 'Usage: run.sh [mighty|demo|full-bench]' >&2; exit 2;; esac
export MOSS_MIGHTY_DATA_DIR="${MOSS_MIGHTY_DATA_DIR:-$experiment_dir/runtime}"
export MOSS_MIGHTY_PROFILE="$profile"
export MOSS_MIGHTY_URL="${MOSS_MIGHTY_URL:-http://192.168.7.1}"
export MOSS_YOLO_BACKEND="${MOSS_YOLO_BACKEND:-npu}"
export MOSS_YOLO_FPS="${MOSS_YOLO_FPS:-3}"
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 NUMBA_NUM_THREADS=2
export YOLO_AUTOINSTALL=false
export YOLO_CONFIG_DIR="$MOSS_MIGHTY_DATA_DIR/yolo-config"
export PATH="/usr/sbin:/sbin:$PATH"
mkdir -p "$MOSS_MIGHTY_DATA_DIR"
cd "$repo_dir"
exec "${MOSS_DIMOS:-$repo_dir/.venv/bin/dimos}" run "moss-mighty.$profile"
