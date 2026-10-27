"""Portable checks for data validity; no board, SDK or actuator required."""
import math
import unittest
from unittest.mock import patch

from moss_mighty.core import BenchState, CpuUsage, cpu_percent, validate_pose
from moss_mighty.npu import parse_result

POSE = {'position_m':[1.,2.,3.], 'orientation_xyzw':[0.,0.,0.,1.],
        'confidence':.9, 'timestamp_ns':123, 'is_public':True, 'packet_type':'POSE'}


class CoreTests(unittest.TestCase):
    def test_invalid_or_internal_pose_is_rejected(self):
        for changes in ({'position_m':[math.nan,0,0]}, {'confidence':math.inf},
                        {'orientation_xyzw':[0,0,0,0]}, {'is_public':False}):
            with self.assertRaises(ValueError):
                validate_pose({**POSE, **changes})

    def test_degraded_pose_never_extends_path(self):
        for code in (0,1,3,4,5,6):
            state=BenchState();state.vio_state={'state':code}
            state.accept_pose(POSE)
            self.assertFalse(state.snapshot()['tracking'])
            self.assertEqual(list(state.trajectory),[])

    def test_low_confidence_pose_never_extends_path(self):
        state=BenchState();state.accept_pose({**POSE,'confidence':.25})
        self.assertFalse(state.snapshot()['tracking'])
        self.assertEqual(list(state.trajectory),[])

    def test_stale_pose_is_not_live(self):
        state=BenchState();state.accept_pose(POSE)
        self.assertTrue(state.snapshot()['tracking'])
        state.pose_monotonic-=2
        self.assertFalse(state.snapshot()['tracking'])

    def test_reset_clears_state_and_trace(self):
        state=BenchState();state.accept_pose(POSE);state.reset()
        self.assertIsNone(state.pose)
        self.assertEqual(list(state.trajectory),[])
        self.assertEqual(state.reset_count,1)

    def test_cpu_iowait_is_idle_guest_is_not_double_counted(self):
        self.assertEqual(cpu_percent([0]*10,[20,0,10,50,20,0,0,0,20,0]),30.0)
        self.assertIsNone(cpu_percent([1]*10,[1]*10))
        self.assertIsNone(cpu_percent([100]*10,[1]*10))

    def test_cpu_samples_are_shared_between_browser_clients(self):
        sampler=CpuUsage()
        with patch('moss_mighty.core.Path.read_text', side_effect=[
            'cpu 0 0 0 0 0 0 0 0\ncpu0 0 0 0 0 0 0 0 0\ncpu1 0 0 0 0 0 0 0 0',
            'cpu 0 0 0 0 0 0 0 0\ncpu0 20 0 10 50 20 0 0 0\ncpu1 50 0 0 50 0 0 0 0'
        ]) as reader, patch('moss_mighty.core.time.monotonic',side_effect=[10.,10.3,11.]):
            first=sampler.sample();cached=sampler.sample();last=sampler.sample()
        self.assertEqual(reader.call_count,2)
        self.assertIs(first,cached)
        self.assertIsNone(first['average_percent'])
        self.assertEqual(last['cores'],[{'id':0,'usage_percent':30.0},{'id':1,'usage_percent':50.0}])
        self.assertEqual(last['average_percent'],40.0)

    def test_npu_boxes_and_network_timing(self):
        boxes,timing=parse_result('vip_run_network: 27.03 ms.\n16: 87%, [ 134, 216, 308, 552], dog\n')
        self.assertEqual(timing,27.03)
        self.assertEqual(boxes[0]['xyxy'],[134,216,308,552])
        self.assertEqual(boxes[0]['confidence'],.87)
        self.assertEqual(parse_result('load failed'),([],None))


if __name__ == '__main__':
    unittest.main()
