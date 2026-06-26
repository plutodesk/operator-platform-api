# -*- coding: utf-8 -*-

import unittest

from operator_platform.service.material import MaterialService


class MaterialListSpecTest(unittest.TestCase):

    def test_build_spec_keyword_and_product(self):
        spec = MaterialService._build_spec({
            'keyword': '春节',
            'product': 'Legacy Jigsaw',
            'tag_ids': ['t1', 't2'],
        })
        self.assertEqual(spec['product'], 'Legacy Jigsaw')
        self.assertEqual(spec['tag_ids'], {'$all': ['t1', 't2']})
        self.assertIn('$regex', spec['name'])


class MaterialListInvolvementTest(unittest.TestCase):

    def test_build_spec_involvement_producer(self):
        spec = MaterialService._build_spec(
            {'involvement': 'producer'},
            current_user_id='user_alice',
        )
        self.assertEqual(spec['producer_user_ids'], 'user_alice')

    def test_build_spec_involvement_creative(self):
        spec = MaterialService._build_spec(
            {'involvement': 'creative'},
            current_user_id='user_bob',
        )
        self.assertEqual(spec['creative_user_ids'], 'user_bob')

    def test_build_spec_involvement_ads_operator(self):
        spec = MaterialService._build_spec(
            {'involvement': 'ads_operator'},
            current_user_id='user_carol',
        )
        self.assertEqual(spec['ads_operator_ids'], 'user_carol')

    def test_build_spec_language_size_channel_date(self):
        spec = MaterialService._build_spec({
            'language': 'en',
            'size': '9x16',
            'channels': ['google', 'facebook'],
            'completed_date_from': '2026-06-01',
            'completed_date_to': '2026-06-30',
            'ads_operator_ids': ['u1', 'u2'],
        })
        self.assertEqual(spec['language'], 'en')
        self.assertEqual(spec['size'], '9x16')
        self.assertEqual(spec['channel_usage.google'], True)
        self.assertEqual(spec['channel_usage.facebook'], True)
        self.assertEqual(spec['completed_date']['$gte'], '2026-06-01')
        self.assertEqual(spec['completed_date']['$lte'], '2026-06-30')
        self.assertEqual(spec['ads_operator_ids'], {'$in': ['u1', 'u2']})


if __name__ == '__main__':
    unittest.main()
