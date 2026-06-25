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


if __name__ == '__main__':
    unittest.main()
