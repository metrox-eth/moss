#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $0 FIRMWARE_HEADER_DIRECTORY OUTPUT_DIRECTORY [PROBE_CPP]" >&2
  exit 2
fi
TASK_SOURCE="$(cd "$1" && pwd)"
mkdir -p "$2"
TASK_OUTPUT="$(cd "$2" && pwd)"
TASK_TEST="${3:-$(cd "$(dirname "$0")" && pwd)/independent_state_probe.cpp}"
TASK_BINARY="$(basename "$TASK_TEST" .cpp)"
TASK_FLAGS=()
if [[ "$(uname)" == Darwin ]]; then
  TASK_SDK="$(xcrun --show-sdk-path)"
  if [[ ! -f "$TASK_SDK/usr/include/c++/v1/cassert" ]]; then
    for candidate in /Library/Developer/CommandLineTools/SDKs/MacOSX*.sdk; do
      if [[ -f "$candidate/usr/include/c++/v1/cassert" ]]; then TASK_SDK="$candidate"; fi
    done
  fi
  TASK_FLAGS=(-isysroot "$TASK_SDK" -isystem "$TASK_SDK/usr/include/c++/v1")
fi
c++ -std=c++17 -Wall -Wextra -Werror "${TASK_FLAGS[@]}" \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -I "$TASK_SOURCE" "$TASK_TEST" -o "$TASK_OUTPUT/$TASK_BINARY" \
  >"$TASK_OUTPUT/compile.log" 2>&1
"$TASK_OUTPUT/$TASK_BINARY" >"$TASK_OUTPUT/test.log" 2>&1
cat "$TASK_OUTPUT/test.log"
