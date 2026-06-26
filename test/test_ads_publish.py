# test/test_ads_publish.py
import unittest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from bson.objectid import ObjectId

import operator_platform  # noqa
from operator_platform.service.ads import AdsService
from operator_platform.error import ParamsError


def make_completed(version=1, user_ids=None):
    oid = ObjectId('507f1f77bcf86cd799439011')
    m = MagicMock()
    m._id = oid
    m.id = str(oid)
    m.version = version
    m.production_status = 'completed'
    m.ads_operator_ids = user_ids or []
    m.channel_usage = {'google': False, 'facebook': False, 'unity': False}
    m.language = ''
    m.size = ''
    type(m).info = PropertyMock(
        side_effect=lambda: {
            'id': m.id,
            'version': m.version,
            'channel_usage': dict(m.channel_usage),
        },
    )
    m.save = AsyncMock()
    return m


class AdsPublishStubTest(unittest.IsolatedAsyncioTestCase):

    async def test_stub_marks_channel_and_adds_operator(self):
        m = make_completed(version=2)
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m):
            result = await AdsService.publish_stub(
                material_id=m.id, version=2, channel='google',
                user_id='operator_1', language='en', size='9x16',
            )
        self.assertEqual(result['api_status'], 'stub')
        self.assertIsNone(result['conflict'])
        self.assertTrue(result['material']['channel_usage']['google'])
        self.assertIn('operator_1', m.ads_operator_ids)
        self.assertEqual(m.version, 3)

    async def test_reject_non_completed(self):
        m = make_completed()
        m.production_status = 'in_progress'
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m):
            with self.assertRaises(ParamsError):
                await AdsService.publish_stub(m.id, 1, 'google', 'u1')

    async def test_version_conflict(self):
        m = make_completed(version=3)
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m):
            result = await AdsService.publish_stub(m.id, 2, 'google', 'u1')
        self.assertIsNotNone(result['conflict'])
        self.assertIsNone(result['material'])
