import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codexpet.appearance import PAT_DURATION, pat_transform


class AppearanceTests(unittest.TestCase):
    def test_chibi_bounces_without_sway_or_sinking_below_floor(self):
        samples = [pat_transform('chibi', PAT_DURATION * i / 120) for i in range(121)]
        self.assertTrue(all(angle == 0 and -15 <= offset <= 0 for offset, angle in samples))
        self.assertLess(samples[20][0], -10)
        for phase in (0, 1 / 3, 2 / 3, 1):
            self.assertAlmostEqual(pat_transform('chibi', PAT_DURATION * phase)[0], 0)
        self.assertGreater(samples[100][0], samples[20][0])

    def test_dragon_sways_and_both_return_to_rest(self):
        self.assertNotEqual(pat_transform('dragon', 0.15)[1], 0)
        for appearance in ('dragon', 'chibi'):
            for age in (-1, PAT_DURATION, 5):
                self.assertEqual(pat_transform(appearance, age), (0, 0))
