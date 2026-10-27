#!/usr/bin/env bash
set -euo pipefail
experiment_dir="$(cd "$(dirname "$0")/.." && pwd)"
data_dir="${MOSS_MIGHTY_DATA_DIR:-$experiment_dir/runtime}"
sdk_dir="${MOSS_NPU_SDK:-$data_dir/npu-sdk}"
[[ "$(uname -s)" == Linux ]] || { echo 'Build on the Linux A733 board.' >&2; exit 1; }
case "$(uname -m)" in aarch64|arm64) ;; *) echo 'Build on the A733 ARM64 board.' >&2; exit 1;; esac
make -C "$sdk_dir/examples/yolov5" AI_SDK_PLATFORM=a733 STAGING_DIR=/ \
  CFLAGS='-O2 -DNPU_SW_VERSION=2' yolov5
echo "Built: $sdk_dir/examples/yolov5/yolov5"
