import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codexpet.quota import Window, parse_snapshot, reset_text


class QuotaTests(unittest.TestCase):
    def test_prefers_codex_bucket_over_legacy_and_other_models(self):
        data = {'rateLimits': {'primary': {'usedPercent': 99}}, 'rateLimitsByLimitId': {
            'other': {'primary': {'usedPercent': 2}},
            'codex': {'primary': {'usedPercent': 34, 'windowDurationMins': 300, 'resetsAt': 1000}, 'secondary': None}}}
        snapshot = parse_snapshot(data, now=100)
        self.assertEqual(snapshot.primary.remaining, 66)
        self.assertEqual(snapshot.primary.label, '5 小时额度')
        self.assertIsNone(snapshot.secondary)

    def test_does_not_substitute_other_bucket(self):
        with self.assertRaises(ValueError):
            parse_snapshot({'rateLimitsByLimitId': {'other': {'primary': {'usedPercent': 3}}}, 'rateLimits': {'primary': {'usedPercent': 5}}})

    def test_missing_is_not_zero(self):
        snapshot = parse_snapshot({'rateLimits': {'primary': {'usedPercent': 5}, 'secondary': {'usedPercent': None}}})
        self.assertIsNone(snapshot.secondary.remaining)
        for value in (None, True, '20', float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_snapshot({'rateLimits': {'primary': {'usedPercent': value}}})

    def test_clamps_percentages(self):
        self.assertEqual(Window(120, 300, None).remaining, 0)
        self.assertEqual(Window(-3, 300, None).remaining, 100)
        self.assertEqual(Window(100, 300, None).remaining, 0)

    def test_dynamic_windows(self):
        self.assertEqual(Window(1, 60, None).label, '1 小时额度')
        self.assertEqual(Window(1, 10080, None).label, '每周额度')
        self.assertEqual(Window(1, 15, None).label, '15 分钟额度')

    def test_reset_does_not_fabricate_restored_balance(self):
        snap = parse_snapshot({'rateLimits': {'primary': {'usedPercent': 100, 'resetsAt': 200}}}, now=100)
        self.assertFalse(snap.stale(199))
        self.assertTrue(snap.stale(200))
        self.assertEqual(snap.primary.remaining, 0)
        self.assertEqual(reset_text(snap.primary, 201), '已到重置时间，等待刷新')
        self.assertEqual(reset_text(Window(1, 300, 3700), 100), '1 小时 0 分钟后重置')
        self.assertEqual(reset_text(None), '重置时间暂不可用')

    def test_age_marks_stale(self):
        snap = parse_snapshot({'rateLimits': {'primary': {'usedPercent': 10}}}, now=100)
        self.assertFalse(snap.stale(400))
        self.assertTrue(snap.stale(401))


if __name__ == '__main__':
    unittest.main()
