import sys
from pathlib import Path
import unittest
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codexpet.quota import Window, parse_snapshot, reset_text


class QuotaTests(unittest.TestCase):
    def extras(self, credits=None, resets=None):
        return parse_snapshot({'rateLimitsByLimitId': {'codex': {
            'primary': {'usedPercent': 100}, 'credits': credits}}, 'rateLimitResetCredits': resets})

    def test_balance_and_authoritative_reset_count(self):
        snap = self.extras({'balance': '886.3598500000', 'hasCredits': True},
                           {'availableCount': 3, 'credits': [{'id': 'only-one-detail'}]})
        self.assertEqual(snap.reset_credits, 3)
        self.assertEqual(snap.reset_credits_text, '3 张')
        self.assertEqual(snap.credit_balance, Decimal('886.3598500000'))
        self.assertEqual(snap.credit_balance_text, '886.36')

    def test_extra_values_distinguish_zero_unknown_and_unlimited(self):
        unknown = self.extras({'hasCredits': False}, {'credits': []})
        self.assertEqual(unknown.reset_credits_text, '未提供')
        self.assertEqual(unknown.credit_balance_text, '未提供')
        zero = self.extras({'balance': '0'}, {'availableCount': 0})
        self.assertEqual(zero.reset_credits_text, '0 张')
        self.assertEqual(zero.credit_balance_text, '0.00')
        self.assertEqual(self.extras({'unlimited': True}).credit_balance_text, '不限量')
        self.assertEqual(self.extras({'unlimited': 'true'}).credit_balance_text, '未提供')

    def test_invalid_extra_values_do_not_break_valid_quota(self):
        for value in (None, True, -1, 'NaN', 'Infinity', '-0.1', {}, [], 'bad'):
            with self.subTest(value=value):
                snap = self.extras({'balance': value}, {'availableCount': value})
                self.assertIsNone(snap.credit_balance)
                self.assertIsNone(snap.reset_credits)
                self.assertEqual(snap.primary.remaining, 0)
        for count in ('2', 2.5):
            self.assertIsNone(self.extras(resets={'availableCount': count}).reset_credits)

    def test_extra_values_do_not_leak_from_other_bucket_or_previous_snapshot(self):
        snap = parse_snapshot({'rateLimits': {'credits': {'balance': '99'}},
                               'rateLimitsByLimitId': {'codex': {'primary': {'usedPercent': 0}}}})
        self.assertIsNone(snap.credit_balance)
        self.assertEqual(self.extras({'balance': '10000000'}).credit_balance_text, '1.00E+7')

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
