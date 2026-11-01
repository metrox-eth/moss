# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('console',Path(__file__).resolve().parents[1]/'tools/bench_console.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.drive_request('drive -100 100 5000'.split())==('drive -100 100',5.0)
assert module.drive_request('drive 0 0 1'.split())==('drive 0 0',.001)
for bad in ['drive 1 1','drive 1 1 5001','drive -101 0 1','drive 0 101 1','drive 1 1 0','drive 1.1 2 100','drive 1 1 100 extra']:
    try:module.drive_request(bad.split())
    except ValueError:pass
    else:raise AssertionError(bad)
print('PASS console bounded drive validation; no ports opened')
