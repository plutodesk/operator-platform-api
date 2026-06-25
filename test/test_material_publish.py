# -*- coding: utf-8 -*-

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from operator_platform.service import material as material_module
from operator_platform.service.material import MaterialService


class FakeMaterial:
    def __init__(self, **kwargs):
        self._id = kwargs.get('_id', '000000000000000000000001')
        self.version = kwargs.get('version', 1)
        self.production_status = kwargs.get('production_status', 'pending')
        self.started_date = kwargs.get('started_date', '')
        self.completed_date = kwargs.get('completed_date', '')
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.saved = False

    @property
    def id(self):
        return str(self._id)

    @property
    def info(self):
        return {
            'id': self.id,
            'version': self.version,
            'production_status': self.production_status,
            'name': getattr(self, 'name', ''),
        }

    async def save(self):
        self.saved = True


class MaterialPublishTest(unittest.IsolatedAsyncioTestCase):

    async def test_update_version_mismatch_adds_conflict(self):
        existing = FakeMaterial(version=2, name='old')
        with patch.object(material_module.Material, 'find_one', AsyncMock(return_value=existing)):
            result = await MaterialService.publish(
                updates=[{'id': existing.id, 'version': 1, 'name': 'new'}],
            )
        self.assertEqual(result['succeeded']['updated'], [])
        self.assertEqual(len(result['conflicts']), 1)
        self.assertEqual(result['conflicts'][0]['action'], 'update')

    async def test_delete_completed_rejected(self):
        existing = FakeMaterial(version=1, production_status='completed')
        with patch.object(material_module.Material, 'find_one', AsyncMock(return_value=existing)):
            result = await MaterialService.publish(
                deletes=[{'id': existing.id, 'version': 1}],
            )
        self.assertIn('不可删除', result['conflicts'][0]['message'])

    async def test_update_success_increments_version(self):
        existing = FakeMaterial(version=3, production_status='pending', name='a')
        with patch.object(material_module.Material, 'find_one', AsyncMock(return_value=existing)):
            result = await MaterialService.publish(
                updates=[{
                    'id': existing.id,
                    'version': 3,
                    'name': 'b',
                    'production_status': 'in_progress',
                }],
            )
        self.assertEqual(result['succeeded']['updated'], [existing.id])
        self.assertEqual(existing.version, 4)
        self.assertTrue(existing.saved)


if __name__ == '__main__':
    unittest.main()
