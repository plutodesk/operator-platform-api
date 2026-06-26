# -*- encoding: utf-8 -*-
#
# @Date: 2026

import unittest

from operator_platform.libs.color_palette import PALETTE, assign_color


class ColorPaletteTest(unittest.TestCase):

    def test_assign_color_is_deterministic(self):
        self.assertEqual(assign_color('奇幻'), assign_color('奇幻'))
        self.assertEqual(assign_color('AI生成'), assign_color('AI生成'))

    def test_assign_color_in_palette(self):
        for name in ['奇幻', 'AI生成', '节日限定', '']:
            self.assertIn(assign_color(name), PALETTE)

    def test_different_names_can_differ(self):
        colors = {assign_color(name) for name in ['奇幻', 'AI生成', '节日限定']}
        self.assertGreaterEqual(len(colors), 2)


if __name__ == '__main__':
    unittest.main()
