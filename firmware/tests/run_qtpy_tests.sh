#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd "$(dirname "$0")/.." && pwd)"
task_build="$(mktemp -d)"
trap 'rm -rf "$task_build"' EXIT
task_cxx="${CXX:-c++}"
task_flags=(-std=c++17 -Wall -Wextra -Werror)
if [[ "$(uname -s)" == Darwin ]]; then
  task_sdk="$(xcrun --show-sdk-path)"
  task_flags+=(-isystem "$task_sdk/usr/include/c++/v1")
fi
for task_case in control_v04_test stop_loop_test; do
  "$task_cxx" "${task_flags[@]}" "$task_root/tests/$task_case.cpp" -o "$task_build/$task_case"
  "$task_build/$task_case"
done
for task_driver in mdd3a mdd10a; do
  task_driver_flags=("${task_flags[@]}")
  if [[ "$task_driver" == mdd10a ]]; then task_driver_flags+=(-DMOSS_DRIVER_MDD10A); fi
  "$task_cxx" "${task_driver_flags[@]}" -I "$task_root/tests/qtpy_stubs" \
    "$task_root/tests/qtpy_stop_integration_test.cpp" -o "$task_build/integration_$task_driver"
  "$task_build/integration_$task_driver"
done
