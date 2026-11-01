# SPDX-License-Identifier: Apache-2.0
"""Find authoritative electrical data in either the repository or a private review checkout."""
import os
from pathlib import Path

def electrical_path(root,explicit=None):
    chosen=explicit or os.environ.get('MOSS_ELECTRICAL')
    if chosen:
        candidates=[Path(chosen).expanduser()]
    else:
        candidates=[base/'hardware/electronics/moss-core-v0.7/electrical' for base in (root,*root.parents)]
        candidates.append(root.parent/'design/electrical')
    for candidate in candidates:
        if all((candidate/name).is_file() for name in ('circuit.json','MCU_PIN_MAP.json')):
            return candidate
    raise FileNotFoundError('Electrical contract not found: pass --electrical DIRECTORY or set MOSS_ELECTRICAL')
