"""User-owned data locations for this experimental profile."""
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get('MOSS_MIGHTY_DATA_DIR',
                              str(Path.home()/'.local/share/moss-mighty'))).expanduser()
RUNTIME = Path(os.environ.get('MOSS_VISION_RUNTIME', str(DATA_DIR/'runtime'))).expanduser()
NPU_SDK = Path(os.environ.get('MOSS_NPU_SDK', str(DATA_DIR/'npu-sdk'))).expanduser()
MODELS_DIR = DATA_DIR/'models'
STATE_DIR = Path(os.environ.get('MOSS_STATE_DIR', str(DATA_DIR/'bench-state'))).expanduser()
