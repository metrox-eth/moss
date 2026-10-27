"""SDK-facing bench state. The sensor's IMU frame is not the rover base frame."""
import io
import json
import math
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .paths import RUNTIME



def cpu_percent(before, after):
    """Linux counters: guest time is already included in user/nice."""
    delta = [b-a for a,b in zip(before[:8], after[:8])]
    if len(delta) < 5 or any(d < 0 for d in delta) or sum(delta) <= 0:
        return None
    idle = delta[3] + delta[4]  # idle + iowait
    return round(max(0, min(100, 100*(sum(delta)-idle)/sum(delta))), 1)


class CpuUsage:
    def __init__(self):
        self.lock = threading.Lock()
        self.previous = {}
        self.last = None
        self.result = {'cores': [], 'average_percent': None, 'interval_s': None}

    def sample(self):
        with self.lock:
            now = time.monotonic()
            # Share a sampling interval across all browser clients.
            if self.last is not None and now-self.last < .8:
                return self.result
            try:
                rows = [line.split() for line in Path('/proc/stat').read_text().splitlines()]
                current = {r[0]: list(map(int,r[1:])) for r in rows
                           if r and r[0].startswith('cpu') and r[0][3:].isdigit()}
            except (OSError, ValueError):
                return {'cores': [], 'average_percent': None, 'interval_s': None}
            cores = [{'id': int(name[3:]), 'usage_percent': cpu_percent(self.previous[name],values)
                      if name in self.previous else None}
                     for name,values in sorted(current.items(), key=lambda p:int(p[0][3:]))]
            valid = [c['usage_percent'] for c in cores if c['usage_percent'] is not None]
            self.result = {'cores':cores, 'average_percent':round(sum(valid)/len(valid),1) if valid else None,
                           'interval_s':round(now-self.last,2) if self.last is not None else None}
            self.previous, self.last = current, now
            return self.result


CPU_USAGE = CpuUsage()


def resources():
    """Whole-board available RAM includes reclaimable cache, as Linux free does."""
    result = {'memory': None, 'temperature_c': None, 'services': {}, 'cpu': CPU_USAGE.sample(),
              'profile': os.environ.get('MOSS_MIGHTY_PROFILE', 'mighty'),
              'hardware': {'name': 'Orange Pi Zero 3W', 'soc': 'Allwinner A733',
                           'cores': os.cpu_count(), 'ram_nominal_gb': 6,
                           'npu_driver_present': Path('/dev/vipcore').exists()}}
    try:
        mem = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
        result['memory'] = {'total_mib': round(mem['MemTotal']/1024, 1),
            'used_mib': round((mem['MemTotal']-mem['MemAvailable'])/1024, 1),
            'available_mib': round(mem['MemAvailable']/1024, 1),
            'swap_used_mib': round((mem['SwapTotal']-mem['SwapFree'])/1024, 1)}
    except (OSError, KeyError, ValueError):
        pass
    temps=[]
    for f in Path('/sys/class/thermal').glob('thermal_zone*/temp'):
        try: temps.append(float(f.read_text())/1000)
        except (OSError, ValueError): pass
    if temps: result['temperature_c']=round(max(temps), 1)
    for name in ['moss-mighty', 'moss-vision', 'moss-full-bench']:
        group=Path('/sys/fs/cgroup/system.slice')/(name+'.service')
        try:
            result['services'][name]={'running':int((group/'pids.current').read_text())>0,
                'memory_mib':round(int((group/'memory.current').read_text())/(1024**2), 1)}
        except (OSError, ValueError): result['services'][name]={'running':False,'memory_mib':0}
    return result


def vision_status():
    try:
        result=json.loads((RUNTIME/'vision.json').read_text())
        result['age_s']=max(0, time.time()-result.get('source_timestamp',result.get('updated_at',0)))
        result['active']=result['age_s']<3 and not result.get('error')
        return result
    except (OSError, ValueError, TypeError):
        return {'active':False,'error':'Detection not running','detections':[]}


def validate_pose(pose):
    if not pose.get("is_public", True) or pose.get("packet_type", "POSE") != "POSE":
        raise ValueError("Non-public pose")
    xyz = [float(x) for x in pose["position_m"]]
    q = [float(x) for x in pose["orientation_xyzw"]]
    confidence = float(pose.get("confidence", 0))
    if len(xyz) != 3 or len(q) != 4 or not all(map(math.isfinite, xyz + q + [confidence])):
        raise ValueError("Invalid pose values")
    norm = math.sqrt(sum(x*x for x in q))
    if not 0.9 <= norm <= 1.1:
        raise ValueError("Invalid quaternion")
    return {"position_m": xyz, "orientation_xyzw": [x/norm for x in q],
            "confidence": max(0, min(1, confidence)),
            "sensor_timestamp_ns": int(pose.get("timestamp_ns", 0)),
            "frame_id": "mighty_odom", "child_frame_id": "mighty_imu",
            "received_at": time.time()}


class BenchState:
    def __init__(self):
        self.lock = threading.RLock()
        self.pose = None
        self.pose_monotonic = None
        self.jpeg = None
        self.image_monotonic = None
        self.poses = 0
        self.images = 0
        self.error = "Waiting for MightyCam USB"
        self.vio_state = {}
        self.trajectory = deque(maxlen=1200)
        self.last_point = 0
        self.reset_count = 0
        self.features = []
        self.features_monotonic = None
        self.distance_m = 0.0
        self.started_at = time.time()

    def accept_pose(self, raw):
        pose = validate_pose(raw)
        with self.lock:
            self.pose = pose
            self.pose_monotonic = time.monotonic()
            self.poses += 1
            self.error = ""
            if pose["confidence"] >= .5 and self.vio_state.get('state',2)==2 and self.pose_monotonic - self.last_point >= .2:
                if self.trajectory:
                    d=math.dist(self.trajectory[-1],pose['position_m'])
                    if .02 < d < 1.0:self.distance_m+=d
                self.trajectory.append(pose["position_m"])
                self.last_point = self.pose_monotonic
        return pose

    def reset(self):
        with self.lock:
            self.pose = None
            self.pose_monotonic = None
            self.trajectory.clear()
            self.distance_m = 0.0
            self.started_at = time.time()
            self.reset_count += 1

    def snapshot(self):
        with self.lock:
            age = None if self.pose_monotonic is None else time.monotonic()-self.pose_monotonic
            image_age = None if self.image_monotonic is None else time.monotonic()-self.image_monotonic
            good = age is not None and age < 1 and self.pose["confidence"] >= .5 and self.vio_state.get('state',2)==2
            return {"mode": "tabletop — camera only", "pose": self.pose,
                    "pose_age_s": age, "image_age_s": image_age,
                    "tracking": good, "poses_received": self.poses,
                    "images_received": self.images, "error": self.error,
                    "vio_state": self.vio_state, "resets": self.reset_count,
                    "trajectory": list(self.trajectory), 'distance_m': self.distance_m,
                    'started_at': self.started_at,
                    'features': self.features if self.features_monotonic and time.monotonic()-self.features_monotonic<1 else []}


def image_pixels(event):
    from mighty_sdk import image_to_raw
    from PIL import Image
    import mighty_protocol as mp
    raw = image_to_raw(event)
    if raw is None:
        return None
    modes = {mp.RAW_FORMAT["GRAY8"]: "L", mp.RAW_FORMAT["RGB24"]: "RGB",
             mp.RAW_FORMAT["RGBA32"]: "RGBA"}
    mode = modes.get(raw["format"])
    if mode is None:
        raise ValueError("Unsupported Mighty image format")
    width, height = int(raw["width"]), int(raw["height"])
    if not (0 < width <= 4096 and 0 < height <= 4096):
        raise ValueError("Invalid image dimensions")
    return Image.frombytes(mode, (width, height), bytes(raw["data"])).convert("RGB")


class Receiver:
    def __init__(self, state, url, on_pose=None, on_image=None):
        from mighty_sdk import MightyClient, MightyWebDevice
        self.state, self.on_pose, self.on_image = state, on_pose, on_image
        self.stop_event = threading.Event()
        self.latest_image = None
        self.image_lock = threading.Lock()
        self.client = MightyClient(MightyWebDevice(base_url=url, read_chunk_size=4096),
                                  auto_reconnect=True, reconnect_delay_s=2)
        self.client.on_pose(self._pose)
        self.client.on_image(self._queue_image)
        self.client.on_error(self._error)
        self.client.on_reset(lambda _: state.reset())
        self.client.on_vio_state(self._vio_state)
        self.client.on_viz(self._viz)

    def _viz(self, event):
        if event.get('subtype') != 'features': return
        with self.state.lock:
            self.state.features = [{k:f[k] for k in ('x','y','status','id') if k in f}
                                   for f in event.get('features',[])[:1000]]
            self.state.features_monotonic = time.monotonic()

    def _pose(self, raw):
        try:
            p = self.state.accept_pose(raw)
            if p["confidence"] >= .5 and self.state.vio_state.get('state',2)==2 and self.on_pose:
                self.on_pose(p)
        except Exception as e:
            self._error({"message": str(e)})

    def _error(self, event):
        with self.state.lock:
            self.state.error = str(event.get("message", event))[:400]

    def _vio_state(self, event):
        with self.state.lock:
            # Unavailable firmware diagnostics may be NaN/Inf during startup.
            # Keep them explicitly unknown rather than breaking JSON/status.
            self.state.vio_state = {k: (None if isinstance(v, float) and not math.isfinite(v) else v)
                                    for k,v in event.items()
                                    if isinstance(v, (str, int, float, bool, type(None)))}

    def _queue_image(self, event):
        if not event.get("dropped"):
            with self.image_lock:
                self.latest_image = event

    def _images(self):
        while not self.stop_event.wait(.2):
            with self.image_lock:
                event, self.latest_image = self.latest_image, None
            if event is None:
                continue
            try:
                pixels = image_pixels(event)
                if pixels is None:
                    continue
                pixels.thumbnail((640, 480))
                output = io.BytesIO()
                pixels.save(output, "JPEG", quality=75)
                with self.state.lock:
                    self.state.jpeg = output.getvalue()
                    self.state.image_monotonic = time.monotonic()
                    self.state.images += 1
                if self.on_image:
                    self.on_image(pixels, time.time())
            except Exception as e:
                self._error({"message": "Image: " + str(e)})

    def _start_vio(self):
        # Retry only until a start succeeds. Never reset a healthy VIO stream.
        while not self.stop_event.is_set():
            result = self.client.start_vio()
            if result.get("ok"):
                return
            self._error(result)
            self.stop_event.wait(5)

    def start(self):
        self.client.connect()
        self.threads = [threading.Thread(target=f, daemon=True)
                        for f in (self._images, self._start_vio)]
        for thread in self.threads:
            thread.start()

    def stop(self):
        self.stop_event.set()
        self.client.disconnect()
        for thread in getattr(self, "threads", []):
            thread.join(timeout=4)


def serve(state, port):
    page = Path(__file__).with_name("dashboard.html").read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/":
                body, kind = page, "text/html; charset=utf-8"
            elif path.startswith('/static/'):
                base=Path(__file__).with_name('cockpit').resolve()
                target=(base/path[len('/static/'):]).resolve()
                if base not in target.parents or not target.is_file():
                    self.send_error(404)
                    return
                body=target.read_bytes()
                kind={'.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml',
                      '.ttf':'font/ttf'}.get(target.suffix,'application/octet-stream')
            elif path == "/status":
                body = json.dumps(state.snapshot(), allow_nan=False).encode()
                kind = "application/json"
            elif path == "/resources":
                body, kind = json.dumps(resources(), allow_nan=False).encode(), 'application/json'
            elif path == "/detections":
                body, kind = json.dumps(vision_status(), allow_nan=False).encode(), 'application/json'
            elif path == "/vision.jpg":
                try: body = (RUNTIME/'vision.jpg').read_bytes()
                except OSError:
                    self.send_error(503, 'Waiting for detector')
                    return
                kind = 'image/jpeg'
            elif path == "/image.jpg":
                with state.lock:
                    body = state.jpeg
                kind = "image/jpeg"
                if body is None:
                    self.send_error(503, "Waiting for camera")
                    return
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
