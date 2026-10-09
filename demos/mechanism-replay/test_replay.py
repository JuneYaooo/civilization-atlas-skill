import copy
import json
import unittest
from pathlib import Path
from replay import input_status, resolve, run

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(Path(__file__).with_name('audit.json').read_text())

    def test_future_evidence_is_rejected(self):
        self.data['cases'][0]['inputs'].append('housing2021')
        with self.assertRaises(ValueError):
            run(self.data)

    def test_known_revision_excluded(self):
        self.assertEqual(input_status(self.data['sources']['copilot'], '2022-11-30'), 'reject_later_revision')

    def test_current_page_not_archive(self):
        self.assertEqual(input_status(self.data['sources']['reform'], '1998-07-31'), 'historical_version_unverified')

    def test_missing_is_not_zero(self):
        claim = copy.deepcopy(self.data['claims'][0])
        claim.update(base=None, end=None, reported_value=None)
        self.assertEqual(resolve(claim)['status'], 'unresolved')

    def test_growth_and_counterexample(self):
        rows = {r['id']: r for r in run(self.data)['results']}
        self.assertAlmostEqual(rows['R2']['value_percent'], 18.5005, places=4)
        self.assertEqual(rows['R3']['status'], 'contradicted')
        self.assertEqual(rows['R4']['status'], 'contradicted')
        self.assertEqual(rows['A2']['status'], 'contradicted')

    def test_cannot_claim_prospective_accuracy(self):
        self.data['accuracy_estimate_permitted'] = True
        with self.assertRaises(ValueError):
            run(self.data)

if __name__ == '__main__':
    unittest.main()
