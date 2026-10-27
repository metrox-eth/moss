"""Latest-frame YOLO worker on the real dimOS Mighty image stream."""
import json
import os
import threading
import time
from collections import deque
from pathlib import Path

from dimos.core.core import rpc
from dimos.core.module import Module
from dimos.core.stream import In, Out
from dimos.core.transport import LCMTransport, JpegLcmTransport
from dimos.core.coordination.blueprints import autoconnect
from dimos.msgs.sensor_msgs.Image import Image, ImageFormat
from dimos.msgs.std_msgs.String import String

from .paths import RUNTIME



def atomic_write(path,data):
    temporary=path.with_suffix(path.suffix+'.new')
    temporary.write_bytes(data)
    temporary.replace(path)


class MightyYolo(Module):
    dedicated_worker=True
    mighty_image: In[Image]
    detections: Out[String]
    annotated_image: Out[Image]

    @rpc
    def start(self):
        super().start()
        import cv2
        self.threads=int(os.environ.get('MOSS_YOLO_THREADS','2'))
        cv2.setNumThreads(1)
        self.size=int(os.environ.get('MOSS_YOLO_SIZE','320'))
        self.rate=float(os.environ.get('MOSS_YOLO_FPS','3'))
        self.backend=os.environ.get('MOSS_YOLO_BACKEND','npu')
        if self.backend=='npu':
            from .npu import NpuDetector
            self.detector=NpuDetector(RUNTIME)
            self.size=640
            self.model_name='YOLOv5 · COCO'
            self.backend_name='A733 NPU · VIPLite'
        else:
            import torch
            from dimos.perception.detection.detectors.yolo import Yolo2DDetector
            torch.set_num_threads(self.threads)
            from .paths import MODELS_DIR
            path=Path(os.environ.get('MOSS_YOLO_MODEL',str(MODELS_DIR/'yolo11n.pt')))
            self.detector=Yolo2DDetector(model_path=str(path.parent),model_name=path.name,device='cpu')
            self.model_name=path.name
            self.backend_name='PyTorch CPU'
        self.latest=None
        self.lock=threading.Lock()
        self.end=threading.Event()
        self.count=0
        self.timings=deque(maxlen=30)
        RUNTIME.mkdir(parents=True,exist_ok=True)
        self.subscription=self.mighty_image.subscribe(self.accept)
        self.worker=threading.Thread(target=self.infer,daemon=True)
        self.worker.start()

    def accept(self,image):
        # No accumulation: overwrite frames while the CPU is busy.
        with self.lock:self.latest=image

    def infer(self):
        import cv2
        import numpy as np
        while not self.end.is_set():
            start=time.monotonic()
            with self.lock:
                frame,self.latest=self.latest,None
            if frame is None:
                self.end.wait(.05)
                continue
            try:
                npu_ms=None
                if self.backend=='npu':
                    annotated,boxes,npu_ms,elapsed=self.detector.predict(frame.to_opencv())
                else:
                    import torch
                    results=self.detector.model.track(frame.to_opencv(),imgsz=self.size,
                        device='cpu',conf=.35,iou=.6,persist=True,tracker='bytetrack.yaml',verbose=False)
                    torch.set_num_threads(self.threads)
                    elapsed=(time.monotonic()-start)*1000
                    result=results[0]
                    boxes=[]
                    if result.boxes is not None:
                        ids=result.boxes.id
                        for i,b in enumerate(result.boxes):
                            cls=int(b.cls.item())
                            boxes.append({'label':result.names[cls],'confidence':float(b.conf.item()),
                                          'xyxy':b.xyxy[0].tolist(),'track_id':int(ids[i]) if ids is not None else None})
                    annotated=result.plot()
                self.timings.append(elapsed)
                self.count+=1
                now=time.time()
                info={'model':self.model_name,'backend':self.backend_name,'input_size':self.size,
                      'npu_network_ms':npu_ms,
                      'inference_ms':round(elapsed,1),'median_ms':round(float(np.median(self.timings)),1),
                      'frames_processed':self.count,'source_timestamp':float(frame.ts),
                      'updated_at':now,'detections':boxes,'error':'',
                      'note':'2D detections on a monochrome camera; no object depth or distance measured.'}
                _,jpg=cv2.imencode('.jpg',annotated,[cv2.IMWRITE_JPEG_QUALITY,80])
                atomic_write(RUNTIME/'vision.jpg',jpg.tobytes())
                data=json.dumps(info,allow_nan=False)
                atomic_write(RUNTIME/'vision.json',data.encode())
                self.detections.publish(String(data=data))
                self.annotated_image.publish(Image.from_numpy(cv2.cvtColor(annotated,cv2.COLOR_BGR2RGB),
                    format=ImageFormat.RGB,frame_id='mighty_camera',ts=frame.ts))
            except Exception as exc:
                atomic_write(RUNTIME/'vision.json',json.dumps({'updated_at':time.time(),
                    'error':str(exc),'model':self.model_name,'detections':[]}).encode())
            self.end.wait(max(.01,1/self.rate-(time.monotonic()-start)))

    @rpc
    def stop(self):
        if hasattr(self,'end'):
            self.end.set();self.worker.join(timeout=5)
            self.detector.stop()
        super().stop()


blueprint=autoconnect(MightyYolo.blueprint()).transports({
    ('mighty_image',Image):JpegLcmTransport('/moss/mighty/image',Image),
    ('detections',String):LCMTransport('/moss/mighty/detections',String),
    ('annotated_image',Image):JpegLcmTransport('/moss/mighty/annotated',Image),
})

from .module import blueprint as camera_blueprint
demo=autoconnect(camera_blueprint, blueprint)
