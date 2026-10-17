import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codexpet.appearance import PAT_DURATION, pat_transform


class AppearanceTests(unittest.TestCase):
    def test_chibi_compresses_downward_and_expands_sideways_without_rotation(self):
        samples = [pat_transform('chibi', PAT_DURATION * i / 120) for i in range(121)]
        self.assertTrue(all(angle == 0 and 0.8 <= height <= 1 and 1 <= width <= 1.25
                            for width, height, angle in samples))
        self.assertLess(samples[20][1], 0.85)
        for width, height, _ in samples:
            self.assertAlmostEqual(width * height, 1)
        for phase in (0, 1 / 3, 2 / 3, 1):
            self.assertAlmostEqual(pat_transform('chibi', PAT_DURATION * phase)[1], 1)
        self.assertGreater(samples[100][1], samples[20][1])

    def test_dragon_sways_and_both_return_to_rest(self):
        self.assertNotEqual(pat_transform('dragon', 0.15)[2], 0)
        for appearance in ('dragon', 'chibi'):
            for age in (-1, PAT_DURATION, 5):
                self.assertEqual(pat_transform(appearance, age), (1, 1, 0))
