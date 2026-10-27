"""A733 VIPLite backend; model and runtime stay on the Orange Pi.

Uses the vendor SDK's YOLOv5 preprocessing, inference and postprocessing.
The subprocess is bounded and consumes only the latest camera frame.
"""
import os
import re
import subprocess
import time
from pathlib import Path

DETECTION = re.compile(r'^\s*(\d+):\s*(\d+)%,\s*\[\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\],\s*(.+)$', re.M)
NETWORK_MS = re.compile(r'vip_run_network:\s*([\d.]+) ms')


def parse_result(output):
    boxes = []
    for item in DETECTION.finditer(output):
        cls, confidence, x1, y1, x2, y2, label = item.groups()
        boxes.append({'label': label.strip(), 'class_id': int(cls),
                      'confidence': int(confidence)/100,
                      'xyxy': list(map(int, (x1, y1, x2, y2))), 'track_id': None})
    timing = NETWORK_MS.search(output)
    return boxes, float(timing.group(1)) if timing else None


class NpuDetector:
    def __init__(self, runtime):
        from .paths import NPU_SDK
        self.sdk = NPU_SDK
        self.binary = self.sdk/'examples/yolov5/yolov5'
        self.model = self.sdk/'examples/yolov5/model/v3/yolov5.nb'
        self.work = Path(runtime)/'npu'
        self.work.mkdir(parents=True, exist_ok=True)
        if not self.binary.is_file() or not self.model.is_file():
            raise RuntimeError('Compiled A733 YOLOv5 backend or model is missing')
        self.env = dict(os.environ)
        self.env['LD_LIBRARY_PATH'] = str(self.sdk/'viplite-tina/lib/aarch64-none-linux-gnu/v2.0')

    def predict(self, image):
        import cv2
        before = time.monotonic()
        source = self.work/'input.jpg'
        if not cv2.imwrite(str(source), image, [cv2.IMWRITE_JPEG_QUALITY, 92]):
            raise RuntimeError('Cannot prepare NPU input')
        result = subprocess.run([str(self.binary), str(self.model), str(source)],
                                cwd=self.work, env=self.env, capture_output=True,
                                text=True, timeout=4, check=False)
        output = result.stdout+'\n'+result.stderr
        if result.returncode:
            raise RuntimeError(f'NPU inference exited {result.returncode}: {output[-400:]}')
        boxes, npu_ms = parse_result(output)
        if npu_ms is None or 'detection num:' not in output:
            raise RuntimeError('NPU did not return a completed inference')
        annotated = image.copy()
        for b in boxes:
            x1,y1,x2,y2 = b['xyxy']
            cv2.rectangle(annotated, (x1,y1), (x2,y2), (199,248,108), 2)
            cv2.putText(annotated, f"{b['label']} {b['confidence']:.0%}",
                        (x1,max(18,y1-6)), cv2.FONT_HERSHEY_SIMPLEX, .5, (199,248,108), 1, cv2.LINE_AA)
        return annotated, boxes, npu_ms, (time.monotonic()-before)*1000

    def stop(self):
        pass
