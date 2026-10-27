import json
import os
import threading
import numpy as np
from dimos.core.core import rpc
from dimos.core.module import Module
from dimos.core.stream import Out
from dimos.core.transport import LCMTransport, JpegLcmTransport
from dimos.core.coordination.blueprints import autoconnect
from dimos.msgs.geometry_msgs.PoseStamped import PoseStamped
from dimos.msgs.sensor_msgs.Image import Image, ImageFormat
from dimos.msgs.std_msgs.String import String
from .core import BenchState, Receiver, serve


class MightyBench(Module):
    dedicated_worker = True
    mighty_pose: Out[PoseStamped]
    mighty_image: Out[Image]
    mighty_status: Out[String]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bench = BenchState()
        self.end_status = threading.Event()

    @rpc
    def start(self):
        super().start()
        self.server = serve(self.bench, int(os.environ.get("MOSS_MIGHTY_WEB_PORT", "8905")))
        self.receiver = Receiver(self.bench, os.environ.get("MOSS_MIGHTY_URL", "http://192.168.7.1"),
                                 on_pose=self._publish_pose, on_image=self._publish_image)
        self.receiver.start()
        self.status_thread = threading.Thread(target=self._status_worker, daemon=True)
        self.status_thread.start()

    def _publish_pose(self, p):
        # Host receipt time is intentional. Raw sensor ns are exposed in status;
        # no uncalibrated device clock is presented as Unix time.
        self.mighty_pose.publish(PoseStamped(ts=p["received_at"], frame_id="mighty_odom",
                                            position=p["position_m"], orientation=p["orientation_xyzw"]))

    def _publish_image(self, pixels, timestamp):
        self.mighty_image.publish(Image.from_numpy(np.asarray(pixels), format=ImageFormat.RGB,
                                                   frame_id="mighty_camera", ts=timestamp))

    def _status_worker(self):
        while not self.end_status.wait(1):
            status = self.bench.snapshot()
            status.pop("trajectory", None)
            self.mighty_status.publish(String(json.dumps(status, allow_nan=False)))

    @rpc
    def stop(self):
        self.end_status.set()
        if hasattr(self, "receiver"):
            self.receiver.stop()
        if hasattr(self, "server"):
            self.server.shutdown()
            self.server.server_close()
        if hasattr(self, "status_thread"):
            self.status_thread.join(timeout=2)
        super().stop()


blueprint = autoconnect(MightyBench.blueprint()).transports({
    ("mighty_pose", PoseStamped): LCMTransport("/moss/mighty/pose", PoseStamped),
    ("mighty_image", Image): JpegLcmTransport("/moss/mighty/image", Image),
    ("mighty_status", String): LCMTransport("/moss/mighty/status", String),
})
