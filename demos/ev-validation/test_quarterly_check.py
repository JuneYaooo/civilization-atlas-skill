import copy
import json
from pathlib import Path
import unittest

from quarterly_check import run, share_rise


class ResolutionTests(unittest.TestCase):
    def test_exact_tie_is_no(self):
        self.assertEqual(share_rise(1, 3, 2, 6), 0)

    def test_rounded_tie_can_be_increase(self):
        self.assertEqual(round(100*1000/10000, 1), round(100*1001/10000, 1))
        self.assertEqual(share_rise(1000, 10000, 1001, 10000), 1)

    def test_falling_volume_can_have_rising_share(self):
        self.assertEqual(share_rise(28623, 32156, 26617, 27175), 1)

    def test_invalid_counts_are_not_negative_outcomes(self):
        for values in [(None, 10, 1, 10), (True, 10, 1, 10),
                       (1.0, 10, 1, 10), (-1, 10, 1, 10),
                       (11, 10, 1, 10), (0, 0, 1, 10)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                share_rise(*values)

    def test_monthly_average_reverses_direction(self):
        # Synthetic counterexample: unweighted month means rise, aggregate falls.
        old = [(90, 100), (1, 10)]
        new = [(8, 10), (30, 100)]
        self.assertGreater(sum(b/t for b,t in new), sum(b/t for b,t in old))
        self.assertEqual(share_rise(sum(b for b,t in old), sum(t for b,t in old),
                                    sum(b for b,t in new), sum(t for b,t in new)), 0)

    def test_scope_time_and_duplicates_rejected(self):
        data = json.loads(Path(__file__).with_name('quarterly-input.json').read_text())
        for key, value in [('scope', 'vehicle_stock'), ('period', 'March'),
                           ('mode', 'future_settlement')]:
            changed = dict(data, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                run(changed)
        changed = copy.deepcopy(data)
        changed['rows'][0]['new_year'] = 2027
        with self.assertRaises(ValueError):
            run(changed)
        changed = copy.deepcopy(data)
        changed['rows'].append(changed['rows'][0])
        with self.assertRaises(ValueError):
            run(changed)

    def test_frozen_output_reproducible(self):
        p = Path(__file__).parent
        self.assertEqual(run(json.loads((p/'quarterly-input.json').read_text())),
                         json.loads((p/'quarterly-results.json').read_text()))


if __name__ == '__main__':
    unittest.main()
