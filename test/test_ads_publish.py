# test/test_ads_publish.py
import unittest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from bson.objectid import ObjectId

import operator_platform  # noqa
from operator_platform.service.ads import AdsService
from operator_platform.service.google_ads import GoogleAdsUploadError
from operator_platform.error import ParamsError


def make_completed(version=1, user_ids=None, material_type='video', upload_path='ads/material/test.jpg'):
    oid = ObjectId('507f1f77bcf86cd799439011')
    m = MagicMock()
    m._id = oid
    m.id = str(oid)
    m.version = version
    m.production_status = 'completed'
    m.material_type = material_type
    m.upload_path = upload_path
    m.upload_paths = [upload_path] if upload_path else []
    m.name = 'Test Material'
    m.task_description = {'text': '', 'images': []}
    m.ads_operator_ids = user_ids or []
    m.channel_usage = {'google': False, 'facebook': False, 'unity': False}
    m.language = ''
    m.size = ''
    m.google_ads_asset = ''
    type(m).info = PropertyMock(
        side_effect=lambda: {
            'id': m.id,
            'version': m.version,
            'channel_usage': dict(m.channel_usage),
            'google_ads_asset': m.google_ads_asset,
        },
    )
    m.save = AsyncMock()
    return m


class AdsPublishTest(unittest.IsolatedAsyncioTestCase):

    async def test_google_upload_success(self):
        m = make_completed(version=2)
        google_result = {
            'asset_type': 'IMAGE',
            'resource_name': 'customers/8969851272/assets/123',
        }
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m), \
                patch('operator_platform.service.ads.GoogleAdsService.upload_material', new_callable=AsyncMock, return_value=google_result):
            result = await AdsService.publish(
                material_id=m.id, version=2, channel='google',
                operator_id='507f1f77bcf86cd799439099', language='en', size='9x16',
            )
        self.assertEqual(result['api_status'], 'ok')
        self.assertIsNone(result['conflict'])
        self.assertTrue(result['material']['channel_usage']['google'])
        self.assertEqual(m.google_ads_asset, google_result['resource_name'])
        self.assertEqual(m.version, 3)

    async def test_google_upload_failure_does_not_save(self):
        m = make_completed(version=2)
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m), \
                patch(
                    'operator_platform.service.ads.GoogleAdsService.upload_material',
                    new_callable=AsyncMock,
                    side_effect=GoogleAdsUploadError('upload failed'),
                ):
            result = await AdsService.publish(m.id, 2, 'google', 'u1')
        self.assertEqual(result['api_status'], 'error')
        self.assertEqual(result['error_message'], 'upload failed')
        self.assertIsNone(result['material'])
        m.save.assert_not_called()

    async def test_facebook_stub_still_works(self):
        m = make_completed(version=2)
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m):
            result = await AdsService.publish(m.id, 2, 'facebook', 'u1')
        self.assertEqual(result['api_status'], 'stub')
        self.assertTrue(result['material']['channel_usage']['facebook'])

    async def test_reject_non_completed(self):
        m = make_completed()
        m.production_status = 'in_progress'
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m):
            with self.assertRaises(ParamsError):
                await AdsService.publish(m.id, 1, 'google', 'u1')

    async def test_version_conflict(self):
        m = make_completed(version=3)
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m):
            result = await AdsService.publish(m.id, 2, 'google', 'u1')
        self.assertEqual(result['api_status'], 'conflict')
        self.assertIsNotNone(result['conflict'])
        self.assertIsNone(result['material'])
