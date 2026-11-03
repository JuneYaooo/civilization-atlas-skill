import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT / 'knowledge-base' / 'scripts' / 'query.py'


def run(*args):
    out = subprocess.run([sys.executable, str(QUERY), *args], capture_output=True, text=True, check=True)
    return out.stdout


class SeriesTest(unittest.TestCase):
    def test_indicators_lists_mirror_vintage(self):
        rows = json.loads(run('indicators'))
        tfr = [r for r in rows if r['indicator'] == 'SP.DYN.TFRT.IN']
        self.assertTrue(tfr)
        self.assertIn('not current', tfr[0]['vintage'])

    def test_series_values_and_locators(self):
        data = json.loads(run('series', '--indicator', 'SP.POP.65UP.TO.ZS', '--entity', 'JPN,Korea, Rep.'.split(',')[0],
                              '--years', '1985,1995', '--nearest', '10.12', '--format', 'json'))
        japan = data['series'][0]
        self.assertEqual(japan['entity_id'], 'wb:JPN')
        values = {r['year']: r['value'] for r in japan['values']}
        self.assertAlmostEqual(values[1985], 10.111, places=2)
        self.assertEqual(japan['nearest']['year'], 1985)
        self.assertTrue(all(r['locator'] for r in japan['values']))

    def test_series_resolves_names_and_rejects_unknown(self):
        data = json.loads(run('series', '--indicator', 'FS.AST.PRVT.GD.ZS', '--entity', 'Thailand', '--years', '1996', '--format', 'json'))
        self.assertAlmostEqual(data['series'][0]['values'][0]['value'], 146.312, places=2)
        bad = subprocess.run([sys.executable, str(QUERY), 'series', '--indicator', 'NOPE', '--entity', 'JPN'], capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)


if __name__ == '__main__':
    unittest.main()
