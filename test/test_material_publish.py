# test/test_material_publish.py
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import operator_platform  # noqa: F401

from bson.objectid import ObjectId
from operator_platform.service.material import MaterialService


def make_material(
    material_id='507f1f77bcf86cd799439011',
    version=1,
    production_status='pending',
    name='春节素材 A',
    started_date='',
    completed_date='',
):
    oid = ObjectId(material_id)
    obj = MagicMock()
    obj._id = oid
    obj.id = str(oid)
    obj.version = version
    obj.production_status = production_status
    obj.name = name
    obj.product = 'Legacy Jigsaw'
    obj.material_type = 'video'
    obj.priority = 'P0'
    obj.creative_type = 'iteration'
    obj.creative_user_ids = []
    obj.producer_user_ids = []
    obj.tag_ids = []
    obj.task_description = {'text': '', 'images': []}
    obj.material_url = ''
    obj.upload_path = ''
    obj.upload_paths = []
    obj.started_date = started_date
    obj.completed_date = completed_date
    obj.created_date = '2026-06-20'
    obj.c_time = 1
    obj.u_time = 1
    obj.info = {
        'id': obj.id,
        'version': version,
        'name': name,
        'production_status': production_status,
    }
    obj.save = AsyncMock()
    return obj


class MaterialPublishTest(unittest.IsolatedAsyncioTestCase):

    async def test_b1_two_rows_concurrent_update(self):
        m1 = make_material('507f1f77bcf86cd799439011', version=1)
        m2 = make_material('507f1f77bcf86cd799439012', version=2)
        async def find_one(spec):
            oid = spec['_id']
            if oid == m1._id:
                return m1
            if oid == m2._id:
                return m2
            return None
        with patch('operator_platform.service.material.Material.find_one', side_effect=find_one):
            with patch('operator_platform.service.material.Material.find_one_and_delete', new_callable=AsyncMock):
                result = await MaterialService.publish(
                    updates=[
                        {'id': m1.id, 'version': 1, 'name': 'A1'},
                        {'id': m2.id, 'version': 2, 'name': 'B1'},
                    ],
                )
        self.assertEqual(result['succeeded']['updated'], [m1.id, m2.id])
        self.assertEqual(result['conflicts'], [])
        self.assertEqual(m1.version, 2)
        self.assertEqual(m2.version, 3)

    async def test_b2_same_row_version_conflict(self):
        m = make_material(version=2)
        with patch('operator_platform.service.material.Material.find_one', new_callable=AsyncMock, return_value=m):
            result = await MaterialService.publish(
                updates=[{'id': m.id, 'version': 1, 'name': 'stale'}],
            )
        self.assertEqual(result['succeeded']['updated'], [])
        self.assertEqual(len(result['conflicts']), 1)
        self.assertEqual(result['conflicts'][0]['action'], 'update')
        self.assertIn('已被他人更新', result['conflicts'][0]['message'])

    async def test_b3_update_then_delete_stale_version(self):
        m = make_material(version=2)
        with patch('operator_platform.service.material.Material.find_one', new_callable=AsyncMock, return_value=m):
            result = await MaterialService.publish(
                deletes=[{'id': m.id, 'version': 1}],
            )
        self.assertEqual(result['succeeded']['deleted'], [])
        self.assertEqual(result['conflicts'][0]['action'], 'delete')
        self.assertIn('已被他人更新', result['conflicts'][0]['message'])

    async def test_b4_delete_completed_rejected(self):
        m = make_material(production_status='completed', version=1)
        with patch('operator_platform.service.material.Material.find_one', new_callable=AsyncMock, return_value=m):
            result = await MaterialService.publish(
                deletes=[{'id': m.id, 'version': 1}],
            )
        self.assertIn('已完成任务不可删除', result['conflicts'][0]['message'])

    async def test_b5_mixed_batch_partial_success(self):
        ok = make_material('507f1f77bcf86cd799439011', version=1)
        stale = make_material('507f1f77bcf86cd799439012', version=3)
        async def find_one(spec):
            oid = spec['_id']
            if oid == ok._id:
                return ok
            if oid == stale._id:
                return stale
            return None
        created = MagicMock()
        created.id = '507f1f77bcf86cd799439013'
        created.save = AsyncMock()
        with patch('operator_platform.service.material.Material.find_one', side_effect=find_one):
            with patch.object(MaterialService, '_create_material', new_callable=AsyncMock, return_value=created):
                result = await MaterialService.publish(
                    creates=[{'name': 'new row'}],
                    updates=[
                        {'id': ok.id, 'version': 1, 'name': 'ok'},
                        {'id': stale.id, 'version': 1, 'name': 'bad'},
                    ],
                )
        self.assertEqual(result['succeeded']['created'], [created.id])
        self.assertEqual(result['succeeded']['updated'], [ok.id])
        self.assertEqual(len(result['conflicts']), 1)
        self.assertEqual(result['conflicts'][0]['id'], stale.id)

    async def test_b6_missing_version(self):
        result = await MaterialService.publish(
            updates=[{'id': '507f1f77bcf86cd799439011', 'name': 'no version'}],
        )
        self.assertEqual(result['succeeded']['updated'], [])
        self.assertEqual(result['conflicts'][0]['message'], 'Params Error')
