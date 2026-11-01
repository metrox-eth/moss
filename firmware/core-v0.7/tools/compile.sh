#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_CLI="${ARDUINO_CLI:-arduino-cli}"
TASK_CONFIG=()
if ! command -v "$TASK_CLI" >/dev/null 2>&1; then
  TASK_CLI='/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli'
fi
if [[ -n "${ARDUINO_CONFIG:-}" ]]; then TASK_CONFIG=(--config-file "$ARDUINO_CONFIG");
elif [[ -f "${HOME}/.arduinoIDE/arduino-cli.yaml" ]]; then TASK_CONFIG=(--config-file "${HOME}/.arduinoIDE/arduino-cli.yaml");
fi
"$TASK_CLI" "${TASK_CONFIG[@]}" compile --warnings all \
  --fqbn 'esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=8M,PSRAM=disabled,PartitionScheme=default_8MB' \
  --build-path "$TASK_ROOT/fw_build/esp32s3" "$TASK_ROOT/src/MOSS_CORE_V07"
