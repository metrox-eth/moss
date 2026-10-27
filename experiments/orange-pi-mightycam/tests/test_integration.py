import json
import math
import time
import unittest
import urllib.request
from unittest.mock import patch

from moss_mighty.core import BenchState, Receiver, image_pixels, serve, validate_pose
from moss_mighty.module import MightyBench, blueprint

POSE = {'position_m':[1.,2.,3.], 'orientation_xyzw':[0.,0.,0.,1.],
        'confidence':.9,'timestamp_ns':1234567,'is_public':True,'packet_type':'POSE'}

class Tests(unittest.TestCase):
    def test_cpu_usage_counts_iowait_as_idle_and_ignores_guest_duplicates(self):
        from moss_mighty.core import cpu_percent
        self.assertEqual(cpu_percent([0]*10,[20,0,10,50,20,0,0,0,20,0]),30.0)
        self.assertIsNone(cpu_percent([1]*10,[1]*10))
        self.assertIsNone(cpu_percent([100]*10,[1]*10))

    def test_public_pose(self):
        p=validate_pose(POSE)
        self.assertEqual(p['sensor_timestamp_ns'],1234567)
        self.assertEqual(p['child_frame_id'],'mighty_imu')
        self.assertEqual(p['position_m'],[1,2,3])

    def test_reject_internal(self):
        with self.assertRaises(ValueError):validate_pose({**POSE,'is_public':False})

    def test_reject_bad_values(self):
        for data in [{'position_m':[math.nan,2,3]},{'orientation_xyzw':[0,0,0,0]},
                     {'position_m':[1,2]},{'confidence':math.nan}]:
            with self.assertRaises(ValueError):validate_pose({**POSE,**data})

    def test_stale_not_tracking(self):
        state=BenchState();state.accept_pose(POSE)
        self.assertTrue(state.snapshot()['tracking'])
        state.pose_monotonic-=2
        self.assertFalse(state.snapshot()['tracking'])

    def test_low_confidence_not_tracking(self):
        state=BenchState();state.accept_pose({**POSE,'confidence':.3})
        self.assertFalse(state.snapshot()['tracking'])
        self.assertEqual(len(state.trajectory),0)

    def test_degraded_categorical_state_overrides_confidence(self):
        for status in (0,1,3,4,5,6):
            state=BenchState();got=[]
            r=Receiver(state,'http://127.0.0.1:1',on_pose=got.append)
            r._vio_state({'state':status})
            r._pose({**POSE,'confidence':1.0})
            self.assertFalse(state.snapshot()['tracking'])
            self.assertEqual(list(state.trajectory),[])
            self.assertEqual(got,[])

    def test_npu_results_and_timing(self):
        from moss_mighty.npu import parse_result
        boxes,elapsed=parse_result('vip_run_network: 25.90 ms.\n16: 87%, [ 134, 216, 308, 552], dog\n')
        self.assertEqual(elapsed,25.9)
        self.assertEqual(boxes,[{'label':'dog','class_id':16,'confidence':.87,
            'xyxy':[134,216,308,552],'track_id':None}])
        self.assertEqual(parse_result('load failed'),([],None))

    def test_reset_drops_trajectory(self):
        state=BenchState();state.accept_pose(POSE);state.reset()
        self.assertIsNone(state.snapshot()['pose'])
        self.assertEqual(list(state.trajectory),[])

    def test_image_and_dropped_frame(self):
        import mighty_protocol as mp
        event={'kind':'raw','width':2,'height':2,'format':mp.RAW_FORMAT['GRAY8'],
               'data':bytes([0,127,128,255])}
        self.assertEqual(image_pixels(event).size,(2,2))
        self.assertIsNone(image_pixels({**event,'dropped':True}))

    def test_receiver_publishes_only_full_pose(self):
        got=[];r=Receiver(BenchState(),'http://127.0.0.1:1',on_pose=got.append)
        r._pose({**POSE,'confidence':.3});self.assertEqual(len(got),0)
        r._pose(POSE);self.assertEqual(len(got),1)
        r._pose({**POSE,'position_m':[math.inf,0,0]});self.assertEqual(len(got),1)

    def test_real_dimos_message_roundtrip(self):
        from dimos.msgs.geometry_msgs.PoseStamped import PoseStamped
        from dimos.msgs.sensor_msgs.Image import Image
        from PIL import Image as PillowImage
        m=MightyBench();got=[]
        with patch.object(m.mighty_pose,'publish',got.append):
            m._publish_pose(validate_pose(POSE))
        decoded=PoseStamped.lcm_decode(got[0].lcm_encode())
        self.assertAlmostEqual(decoded.x,1)
        self.assertEqual(decoded.frame_id,'mighty_odom')
        got=[]
        with patch.object(m.mighty_image,'publish',got.append):
            m._publish_image(PillowImage.new('RGB',(8,6)),time.time())
        self.assertEqual(Image.lcm_decode(got[0].lcm_encode()).frame_id,'mighty_camera')
        m.stop()

    def test_http_status(self):
        state=BenchState();server=serve(state,0)
        try:
            url=f'http://127.0.0.1:{server.server_port}'
            data=json.load(urllib.request.urlopen(url+'/status',timeout=3))
            self.assertFalse(data['tracking'])
            self.assertIn('MightyCam',urllib.request.urlopen(url,timeout=3).read().decode())
        finally:server.shutdown();server.server_close()

    def test_startup_nonfinite_diagnostics_keep_http_status_working(self):
        state=BenchState();receiver=Receiver(state,'http://127.0.0.1:1')
        receiver._vio_state({'state':'initializing','score':math.nan,
                             'error':math.inf,'other':-math.inf,'features':12})
        server=serve(state,0)
        try:
            data=json.load(urllib.request.urlopen(
                f'http://127.0.0.1:{server.server_port}/status',timeout=3))
            self.assertIsNone(data['vio_state']['score'])
            self.assertIsNone(data['vio_state']['error'])
            self.assertIsNone(data['vio_state']['other'])
            self.assertEqual(data['vio_state']['features'],12)
            self.assertEqual(data['vio_state']['state'],'initializing')
            self.assertFalse(data['tracking'])
            json.dumps(data,allow_nan=False)
        finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main(verbosity=2)
