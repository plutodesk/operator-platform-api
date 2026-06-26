# test/test_material_meta.py
import unittest

from operator_platform.constants.material_meta import (
    LANGUAGES,
    SIZES,
    CHANNELS,
    DEFAULT_CHANNEL_USAGE,
)
from operator_platform.db.material import Material


class MaterialMetaTest(unittest.TestCase):

    def test_language_and_size_constants(self):
        self.assertIn('en', LANGUAGES)
        self.assertIn('9x16', SIZES)
        self.assertEqual(set(CHANNELS), {'google', 'facebook', 'unity'})

    def test_material_default_has_channel_usage(self):
        self.assertEqual(Material.default['channel_usage'], DEFAULT_CHANNEL_USAGE)
        self.assertEqual(Material.default['ads_operator_ids'], [])
