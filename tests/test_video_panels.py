"""T13 (lab side) + T14: the text the video shows comes from evidence/ or a pinned file, and fits a phone.

video/panel-sources.json: {"<panel file in video/>": {"sources": ["<lab-relative file>", ...], "max_cells": 60}}
Every non-empty line of a panel must appear verbatim (as a substring) in one of its sources. The primer-side check
(`pr-plan --check`, T13b) runs at the script stage in mcp-canvas.
"""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8', errors='replace') as f:
        return f.read()


class T14PanelsFromEvidence(unittest.TestCase):
    def setUp(self):
        self.sources = json.loads(read('video/panel-sources.json'))

    def test_every_panel_line_is_in_its_sources(self):
        self.assertGreaterEqual(len(self.sources), 6)
        for panel, spec in self.sources.items():
            src = '\n'.join(read(s) for s in spec['sources'])
            for line in read(os.path.join('video', panel)).splitlines():
                if line.strip():
                    self.assertIn(line.strip(), src, f'{panel}: {line!r}')

    def test_rows_fit(self):
        for panel, spec in self.sources.items():
            for line in read(os.path.join('video', panel)).splitlines():
                self.assertLessEqual(len(line), spec.get('max_cells', 60), f'{panel}: {line!r}')


class T13ComposeCards(unittest.TestCase):
    def test_bug_and_fix_differ_in_one_row_same_column(self):
        a = read('compose.bug.yaml').splitlines()
        b = read('compose.fix.yaml').splitlines()
        self.assertEqual(len(a), len(b))
        diff = [(x, y) for x, y in zip(a, b) if x != y]
        self.assertEqual(len(diff), 1, diff)
        x, y = diff[0]
        col = next(i for i, (c1, c2) in enumerate(zip(x, y)) if c1 != c2)
        self.assertEqual(x[:col], y[:col])
        self.assertIn('JAVA_TOOL_OPTIONS', x)
        for line in a + b:
            self.assertLessEqual(len(line), 60)


if __name__ == '__main__':
    unittest.main()
