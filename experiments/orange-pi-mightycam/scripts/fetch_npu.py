#!/usr/bin/env python3
"""Fetch the pinned vendor example into ignored runtime storage; verify every file."""
import argparse
import hashlib
import json
import os
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    default = Path(os.environ.get('MOSS_MIGHTY_DATA_DIR', str(HERE.parent/'runtime')))/'npu-sdk'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=default)
    args = parser.parse_args()
    manifest = json.loads((HERE/'npu-files.json').read_text())
    destination = args.destination.expanduser().resolve()
    upstream = manifest['repository'].removeprefix('https://github.com/')
    for name, checksum in manifest['sha256'].items():
        target = (destination/name).resolve()
        if destination not in target.parents:
            raise ValueError('Invalid manifest path')
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == checksum:
            continue
        url = f"https://raw.githubusercontent.com/{upstream}/{manifest['revision']}/{name}"
        with urllib.request.urlopen(url, timeout=45) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != checksum:
            raise ValueError(f'Checksum mismatch: {name}')
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix+'.download')
        temporary.write_bytes(data)
        temporary.replace(target)
        print(name, flush=True)
    # The sample does not use highgui. Keep the build headless.
    for name in ('yolov5_pre_process.cpp', 'yolov5_post_process.cpp'):
        path = destination/'examples/yolov5'/name
        text = path.read_text().replace('#include <opencv2/highgui/highgui.hpp>',
                                        '#include <opencv2/imgcodecs.hpp>')
        # vector's end is exclusive; preserve the last output element too.
        for i in range(3):
            text = text.replace(f'&output[{i}][size{i}-1]', f'output[{i}] + size{i}')
        path.write_text(text)
    print(f'Ready: {destination}')


if __name__ == '__main__':
    main()
