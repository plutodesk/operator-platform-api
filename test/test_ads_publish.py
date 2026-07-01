# test/test_ads_publish.py
import unittest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from bson.objectid import ObjectId

import operator_platform  # noqa
from operator_platform.service.ads import AdsService
from operator_platform.service.google_ads import GoogleAdsUploadError
from operator_platform.service.unity_ads import UnityAdsUploadError
from operator_platform.error import ParamsError

PLATFORM_CONFIG_ID = '665a00000000000000000001'
TOKEN_CONFIG_ID = '665a00000000000000000002'


def make_platform(channel='google', product='Legacy Jigsaw', name='Google - Legacy Jigsaw'):
    platform = MagicMock()
    platform.id = PLATFORM_CONFIG_ID
    platform.channel = channel
    platform.product = product
    platform.name = name
    platform.enabled = True
    platform.token_config_id = TOKEN_CONFIG_ID
    platform.settings = {'customer_id': '11111', 'login_customer_id': ''}
    return platform


def make_token(name='Google Ads 默认'):
    token = MagicMock()
    token.id = TOKEN_CONFIG_ID
    token.name = name
    token.enabled = True
    return token


def make_completed(version=1, user_ids=None, material_type='video', upload_path='ads/material/test.jpg',
                   upload_paths=None, product='Legacy Jigsaw'):
    oid = ObjectId('507f1f77bcf86cd799439011')
    m = MagicMock()
    m._id = oid
    m.id = str(oid)
    m.version = version
    m.product = product
    m.production_status = 'completed'
    m.material_type = material_type
    m.upload_path = upload_path
    paths = upload_paths if upload_paths is not None else ([upload_path] if upload_path else [])
    m.upload_paths = paths
    m.name = 'Test Material'
    m.task_description = {'text': '', 'images': []}
    m.ads_operator_ids = user_ids or []
    m.channel_usage = {'google': False, 'facebook': False, 'unity': False}
    m.platform_publish = {}
    m.language = ''
    m.size = ''
    m.google_ads_asset = ''
    m.unity_creative_id = ''

    def build_info():
        return {
            'id': m.id,
            'version': m.version,
            'channel_usage': dict(m.channel_usage),
            'upload_paths': list(m.upload_paths),
            'platform_publish': dict(m.platform_publish),
            'google_ads_asset': m.google_ads_asset,
            'unity_creative_id': m.unity_creative_id,
        }

    type(m).info = PropertyMock(side_effect=build_info)
    m.save = AsyncMock()
    return m


class AdsPublishTest(unittest.IsolatedAsyncioTestCase):

    async def test_google_upload_success(self):
        m = make_completed(version=2)
        platform = make_platform()
        token = make_token()
        google_result = {
            'asset_type': 'IMAGE',
            'resource_name': 'customers/8969851272/assets/123',
        }
        google_cfg = {'customer_id': '11111'}
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m), \
                patch(
                    'operator_platform.service.ads.AdsConfigResolver.resolve_by_config_id',
                    new_callable=AsyncMock,
                    return_value=(platform, google_cfg),
                ), \
                patch('operator_platform.service.ads.TokenConfig.find_one', new_callable=AsyncMock, return_value=token), \
                patch(
                    'operator_platform.service.ads.GoogleAdsService.upload_file',
                    return_value=google_result,
                ) as upload_mock:
            result = await AdsService.publish(
                material_id=m.id, version=2, channel='google',
                operator_id='507f1f77bcf86cd799439099',
                platform_config_id=PLATFORM_CONFIG_ID,
                language='en', size='9x16',
            )
        upload_mock.assert_called_once_with(m, 'ads/material/test.jpg', cfg=google_cfg)
        self.assertEqual(result['api_status'], 'ok')
        self.assertIsNone(result['conflict'])
        self.assertTrue(result['material']['channel_usage']['google'])
        self.assertEqual(m.google_ads_asset, google_result['resource_name'])
        self.assertEqual(m.platform_publish['google']['name'], platform.name)
        self.assertEqual(m.platform_publish['google']['external_id'], google_result['resource_name'])
        self.assertEqual(len(m.platform_publish['google']['assets']), 1)
        self.assertEqual(m.version, 3)

    async def test_google_requires_platform_config_id(self):
        m = make_completed(version=2)
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m):
            with self.assertRaises(ParamsError):
                await AdsService.publish(m.id, 2, 'google', 'u1')

    async def test_google_upload_failure_does_not_save(self):
        m = make_completed(version=2)
        platform = make_platform()
        google_cfg = {'customer_id': '11111'}
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m), \
                patch(
                    'operator_platform.service.ads.AdsConfigResolver.resolve_by_config_id',
                    new_callable=AsyncMock,
                    return_value=(platform, google_cfg),
                ), \
                patch(
                    'operator_platform.service.ads.GoogleAdsService.upload_file',
                    side_effect=GoogleAdsUploadError('upload failed'),
                ):
            result = await AdsService.publish(
                m.id, 2, 'google', 'u1', platform_config_id=PLATFORM_CONFIG_ID,
            )
        self.assertEqual(result['api_status'], 'error')
        self.assertEqual(result['error_message'], 'upload failed')
        self.assertIsNone(result['material'])
        self.assertEqual(result['failed'], [{'upload_path': 'ads/material/test.jpg', 'error_message': 'upload failed'}])
        m.save.assert_not_called()

    async def test_google_multi_file_all_success(self):
        m = make_completed(
            version=2,
            upload_paths=['ads/material/a.mp4', 'ads/material/b.png'],
            material_type='video',
        )
        platform = make_platform()
        token = make_token()
        results = [
            {'asset_type': 'YOUTUBE_VIDEO', 'resource_name': 'customers/1/assets/v1'},
            {'asset_type': 'IMAGE', 'resource_name': 'customers/1/assets/i1'},
        ]
        google_cfg = {'customer_id': '11111'}
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m), \
                patch(
                    'operator_platform.service.ads.AdsConfigResolver.resolve_by_config_id',
                    new_callable=AsyncMock,
                    return_value=(platform, google_cfg),
                ), \
                patch('operator_platform.service.ads.TokenConfig.find_one', new_callable=AsyncMock, return_value=token), \
                patch(
                    'operator_platform.service.ads.GoogleAdsService.upload_file',
                    side_effect=results,
                ) as upload_mock:
            result = await AdsService.publish(
                m.id, 2, 'google', 'u1',
                platform_config_id=PLATFORM_CONFIG_ID,
                upload_paths=['ads/material/a.mp4', 'ads/material/b.png'],
            )
        self.assertEqual(upload_mock.call_count, 2)
        self.assertEqual(result['api_status'], 'ok')
        self.assertEqual(len(result['succeeded']), 2)
        self.assertEqual(result['failed'], [])
        assets = m.platform_publish['google']['assets']
        self.assertEqual(len(assets), 2)
        self.assertEqual(m.version, 4)

    async def test_google_partial_success(self):
        m = make_completed(version=2, upload_paths=['a.mp4', 'bad.png'])
        platform = make_platform()
        token = make_token()
        good_result = {
            'asset_type': 'YOUTUBE_VIDEO',
            'resource_name': 'customers/1/assets/v1',
        }
        google_cfg = {'customer_id': '11111'}
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m), \
                patch(
                    'operator_platform.service.ads.AdsConfigResolver.resolve_by_config_id',
                    new_callable=AsyncMock,
                    return_value=(platform, google_cfg),
                ), \
                patch('operator_platform.service.ads.TokenConfig.find_one', new_callable=AsyncMock, return_value=token), \
                patch(
                    'operator_platform.service.ads.GoogleAdsService.upload_file',
                    side_effect=[good_result, GoogleAdsUploadError('bad format')],
                ):
            result = await AdsService.publish(
                m.id, 2, 'google', 'u1',
                platform_config_id=PLATFORM_CONFIG_ID,
                upload_paths=['a.mp4', 'bad.png'],
            )
        self.assertEqual(result['api_status'], 'partial')
        self.assertEqual(len(result['succeeded']), 1)
        self.assertEqual(len(result['failed']), 1)
        self.assertEqual(len(m.platform_publish['google']['assets']), 1)
        self.assertEqual(m.version, 3)

    async def test_reject_empty_pending(self):
        m = make_completed(version=2)
        m.platform_publish = {
            'google': {
                'assets': [{'upload_path': 'ads/material/test.jpg', 'external_id': 'x'}],
            },
        }
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m):
            with self.assertRaises(ParamsError):
                await AdsService.publish(m.id, 2, 'google', 'u1', platform_config_id=PLATFORM_CONFIG_ID)

    async def test_legacy_republish_seeds_first_path(self):
        m = make_completed(
            version=2,
            upload_paths=['ads/material/a.mp4', 'ads/material/b.png'],
            material_type='video',
        )
        m.platform_publish = {
            'google': {
                'external_id': 'customers/1/assets/v1',
                'platform_config_id': PLATFORM_CONFIG_ID,
                'name': 'Google - Legacy Jigsaw',
            },
        }
        m.channel_usage = {'google': True, 'facebook': False, 'unity': False}
        m.google_ads_asset = 'customers/1/assets/v1'
        platform = make_platform()
        token = make_token()
        google_result = {'asset_type': 'IMAGE', 'resource_name': 'customers/1/assets/i1'}
        google_cfg = {'customer_id': '11111'}
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m), \
                patch(
                    'operator_platform.service.ads.AdsConfigResolver.resolve_by_config_id',
                    new_callable=AsyncMock,
                    return_value=(platform, google_cfg),
                ), \
                patch('operator_platform.service.ads.TokenConfig.find_one', new_callable=AsyncMock, return_value=token), \
                patch(
                    'operator_platform.service.ads.GoogleAdsService.upload_file',
                    return_value=google_result,
                ) as upload_mock:
            result = await AdsService.publish(
                m.id, 2, 'google', 'u1',
                platform_config_id=PLATFORM_CONFIG_ID,
                upload_paths=['ads/material/b.png'],
            )
        upload_mock.assert_called_once_with(m, 'ads/material/b.png', cfg=google_cfg)
        self.assertEqual(result['api_status'], 'ok')
        assets = m.platform_publish['google']['assets']
        self.assertEqual(len(assets), 2)
        paths = [a['upload_path'] for a in assets]
        self.assertIn('ads/material/a.mp4', paths)
        self.assertIn('ads/material/b.png', paths)
        legacy = next(a for a in assets if a['upload_path'] == 'ads/material/a.mp4')
        self.assertEqual(legacy['external_id'], 'customers/1/assets/v1')

    async def test_allow_republish_pending_files(self):
        m = make_completed(
            version=2,
            upload_paths=['a.mp4', 'b.png'],
        )
        m.platform_publish = {
            'google': {
                'assets': [{'upload_path': 'a.mp4', 'external_id': 'x', 'asset_type': 'YOUTUBE_VIDEO'}],
            },
        }
        m.channel_usage = {'google': True, 'facebook': False, 'unity': False}
        platform = make_platform()
        token = make_token()
        google_result = {'asset_type': 'IMAGE', 'resource_name': 'customers/1/assets/i1'}
        google_cfg = {'customer_id': '11111'}
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m), \
                patch(
                    'operator_platform.service.ads.AdsConfigResolver.resolve_by_config_id',
                    new_callable=AsyncMock,
                    return_value=(platform, google_cfg),
                ), \
                patch('operator_platform.service.ads.TokenConfig.find_one', new_callable=AsyncMock, return_value=token), \
                patch(
                    'operator_platform.service.ads.GoogleAdsService.upload_file',
                    return_value=google_result,
                ) as upload_mock:
            result = await AdsService.publish(
                m.id, 2, 'google', 'u1',
                platform_config_id=PLATFORM_CONFIG_ID,
                upload_paths=['b.png'],
            )
        upload_mock.assert_called_once_with(m, 'b.png', cfg=google_cfg)
        self.assertEqual(result['api_status'], 'ok')
        self.assertEqual(len(result['succeeded']), 1)
        self.assertEqual(result['succeeded'][0]['upload_path'], 'b.png')
        self.assertEqual(len(m.platform_publish['google']['assets']), 2)

    async def test_facebook_stub_still_works(self):
        m = make_completed(version=2)
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m):
            result = await AdsService.publish(m.id, 2, 'facebook', 'u1')
        self.assertEqual(result['api_status'], 'stub')
        self.assertTrue(result['material']['channel_usage']['facebook'])

    async def test_unity_upload_success(self):
        m = make_completed(version=2, material_type='video', upload_path='ads/material/test.mp4')
        platform = make_platform(channel='unity', name='Unity - Legacy Jigsaw')
        platform.settings = {'organization_id': 'org', 'campaign_set_id': 'set'}
        token = make_token('Unity 默认')
        unity_result = {
            'creative_id': '68f60cd12b96a4215276bb02',
            'name': 'Test Material',
            'type': 'portraitVideo',
            'status': 'uploaded',
        }
        unity_cfg = {'organization_id': 'org', 'campaign_set_id': 'set'}
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m), \
                patch(
                    'operator_platform.service.ads.AdsConfigResolver.resolve_by_config_id',
                    new_callable=AsyncMock,
                    return_value=(platform, unity_cfg),
                ), \
                patch('operator_platform.service.ads.TokenConfig.find_one', new_callable=AsyncMock, return_value=token), \
                patch(
                    'operator_platform.service.ads.UnityAdsService.upload_file',
                    return_value=unity_result,
                ):
            result = await AdsService.publish(
                material_id=m.id, version=2, channel='unity',
                operator_id='507f1f77bcf86cd799439099',
                platform_config_id=PLATFORM_CONFIG_ID,
                language='en', size='9x16',
            )
        self.assertEqual(result['api_status'], 'ok')
        self.assertTrue(result['material']['channel_usage']['unity'])
        self.assertEqual(m.unity_creative_id, unity_result['creative_id'])
        self.assertEqual(m.platform_publish['unity']['name'], platform.name)

    async def test_unity_upload_failure_does_not_save(self):
        m = make_completed(version=2, material_type='video', upload_path='ads/material/test.mp4')
        platform = make_platform(channel='unity')
        unity_cfg = {'organization_id': 'org', 'campaign_set_id': 'set'}
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m), \
                patch(
                    'operator_platform.service.ads.AdsConfigResolver.resolve_by_config_id',
                    new_callable=AsyncMock,
                    return_value=(platform, unity_cfg),
                ), \
                patch('operator_platform.service.ads.TokenConfig.find_one', new_callable=AsyncMock, return_value=make_token('Unity 默认')), \
                patch(
                    'operator_platform.service.ads.UnityAdsService.upload_file',
                    side_effect=UnityAdsUploadError('unity upload failed'),
                ):
            result = await AdsService.publish(
                m.id, 2, 'unity', 'u1', platform_config_id=PLATFORM_CONFIG_ID,
            )
        self.assertEqual(result['api_status'], 'error')
        self.assertIsNone(result['material'])
        m.save.assert_not_called()

    async def test_reject_non_completed(self):
        m = make_completed()
        m.production_status = 'in_progress'
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m):
            with self.assertRaises(ParamsError):
                await AdsService.publish(
                    m.id, 1, 'google', 'u1', platform_config_id=PLATFORM_CONFIG_ID,
                )

    async def test_version_conflict(self):
        m = make_completed(version=3)
        with patch('operator_platform.service.ads.Material.find_one', new_callable=AsyncMock, return_value=m):
            result = await AdsService.publish(
                m.id, 2, 'google', 'u1', platform_config_id=PLATFORM_CONFIG_ID,
            )
        self.assertEqual(result['api_status'], 'conflict')
        self.assertIsNotNone(result['conflict'])


class AdsPublishOptionsTest(unittest.IsolatedAsyncioTestCase):

    async def test_empty_without_enabled_tokens(self):
        with patch('operator_platform.service.ads.TokenConfig.query', new_callable=AsyncMock, return_value=[]):
            result = await AdsService.get_publish_options(product='Legacy Jigsaw')
        self.assertEqual(result, [])

    async def test_filter_by_product_with_default_fallback(self):
        token = make_token()
        token.channel = 'google'
        product_config = make_platform(product='Legacy Jigsaw')
        default_config = make_platform(product='', name='Google Default')
        default_config.id = '665a00000000000000000003'

        with patch('operator_platform.service.ads.TokenConfig.query', new_callable=AsyncMock, return_value=[token]), \
                patch('operator_platform.service.ads.AdPlatformConfig.query', new_callable=AsyncMock,
                      return_value=[product_config, default_config]), \
                patch('operator_platform.service.ads.AdsService._token_name_map', new_callable=AsyncMock,
                      return_value={TOKEN_CONFIG_ID: token.name}):
            matched = await AdsService.get_publish_options(product='Legacy Jigsaw')
            fallback = await AdsService.get_publish_options(product='Unknown Product')

        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]['channel'], 'google')
        self.assertEqual(matched[0]['configs'][0]['id'], product_config.id)
        self.assertEqual(fallback[0]['configs'][0]['id'], default_config.id)

    async def test_filter_by_product_returns_all_matching_configs(self):
        token = make_token()
        token.channel = 'unity'
        first = make_platform(channel='unity', product='Color Fow', name='Unity - Color Fow')
        second = make_platform(channel='unity', product='Color Fow', name='test1')
        second.id = '665a00000000000000000004'

        with patch('operator_platform.service.ads.TokenConfig.query', new_callable=AsyncMock, return_value=[token]), \
                patch('operator_platform.service.ads.AdPlatformConfig.query', new_callable=AsyncMock,
                      return_value=[first, second]), \
                patch('operator_platform.service.ads.AdsService._token_name_map', new_callable=AsyncMock,
                      return_value={TOKEN_CONFIG_ID: token.name}):
            result = await AdsService.get_publish_options(product='Color Fow')

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['channel'], 'unity')
        self.assertEqual({item['id'] for item in result[0]['configs']}, {first.id, second.id})
