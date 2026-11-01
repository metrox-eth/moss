#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$TASK_ROOT/fw_build"
SDK_FLAGS=()
if [[ "$(uname)" == Darwin ]]; then
  TASK_SDK="$(xcrun --show-sdk-path)"
  # Some Apple CLT installations retain libc++ headers only inside a versioned SDK.
  if [[ ! -f "$TASK_SDK/usr/include/c++/v1/cassert" ]]; then
    for candidate in /Library/Developer/CommandLineTools/SDKs/MacOSX*.sdk; do
      if [[ -f "$candidate/usr/include/c++/v1/cassert" ]]; then TASK_SDK="$candidate"; fi
    done
  fi
  SDK_FLAGS=(-isysroot "$TASK_SDK" -isystem "$TASK_SDK/usr/include/c++/v1")
fi
for suite in core_test servo_bus_test legacy_control_test; do
  c++ -std=c++17 -Wall -Wextra -Werror "${SDK_FLAGS[@]}" -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I "$TASK_ROOT/src/MOSS_CORE_V07" -I "$TASK_ROOT/tests/stubs" \
    "$TASK_ROOT/tests/$suite.cpp" -o "$TASK_ROOT/fw_build/$suite"
  "$TASK_ROOT/fw_build/$suite"
done
python3 "$TASK_ROOT/tests/console_test.py"
python3 "$TASK_ROOT/tools/validate_contract.py"
python3 "$TASK_ROOT/tests/contract_test.py"
