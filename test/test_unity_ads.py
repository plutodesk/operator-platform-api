# test/test_unity_ads.py
import unittest
from unittest.mock import MagicMock, patch

import operator_platform  # noqa
from operator_platform.error import ParamsError
from operator_platform.service.unity_ads import UnityAdsService, UnityAdsUploadError


def make_material(material_type='video', upload_path='ads/material/a.mp4', size=''):
    m = MagicMock()
    m.material_type = material_type
    m.upload_path = upload_path
    m.upload_paths = [upload_path]
    m.name = 'Demo'
    m.language = 'en'
    m.size = size
    return m


class UnityAdsServiceTest(unittest.TestCase):

    def test_resolve_portrait_video(self):
        spec = UnityAdsService._resolve_creative_spec(make_material(), language='en', size='9x16')
        self.assertEqual(spec['file_field'], 'videoFile')
        self.assertIn('video', spec['creative_info'])

    def test_resolve_landscape_video(self):
        spec = UnityAdsService._resolve_creative_spec(make_material(), size='16x9')
        self.assertEqual(spec['file_field'], 'landscapeVideoFile')
        self.assertIn('landscapeVideo', spec['creative_info'])

    def test_resolve_square_end_card(self):
        spec = UnityAdsService._resolve_creative_spec(
            make_material(material_type='image', upload_path='ads/material/a.jpeg', size='1x1'),
        )
        self.assertEqual(spec['file_field'], 'squareEndCardFile')
        self.assertIn('squareEndCard', spec['creative_info'])

    def test_reject_missing_upload_path(self):
        m = make_material()
        m.upload_path = ''
        m.upload_paths = []
        with self.assertRaises(ParamsError):
            UnityAdsService._resolve_creative_spec(m)

    @patch('operator_platform.service.unity_ads.requests.post')
    @patch('operator_platform.service.unity_ads.UnityAdsService._fetch_upload_bytes')
    @patch('operator_platform.service.unity_ads.UnityAdsService._load_cfg')
    def test_upload_creative_success(self, load_cfg, fetch_bytes, post):
        load_cfg.return_value = {
            'key_id': 'kid',
            'secret_key': 'secret',
            'organization_id': 'org1',
            'campaign_set_id': 'app1',
        }
        fetch_bytes.return_value = b'video-bytes'
        resp = MagicMock()
        resp.status_code = 201
        resp.json.return_value = {
            'id': 'creative123',
            'name': 'Demo',
            'language': 'en',
            'type': 'portraitVideo',
            'status': 'uploaded',
        }
        post.return_value = resp

        result = UnityAdsService._upload_creative_sync(make_material(), language='en', size='9x16')
        self.assertEqual(result['creative_id'], 'creative123')
        self.assertEqual(result['type'], 'portraitVideo')
        post.assert_called_once()

    @patch('operator_platform.service.unity_ads.requests.post')
    @patch('operator_platform.service.unity_ads.UnityAdsService._fetch_upload_bytes')
    @patch('operator_platform.service.unity_ads.UnityAdsService._load_cfg')
    def test_upload_creative_http_error(self, load_cfg, fetch_bytes, post):
        load_cfg.return_value = {
            'key_id': 'kid',
            'secret_key': 'secret',
            'organization_id': 'org1',
            'campaign_set_id': 'app1',
        }
        fetch_bytes.return_value = b'video-bytes'
        resp = MagicMock()
        resp.status_code = 403
        resp.text = 'Forbidden'
        resp.json.return_value = {'detail': 'Not Authorized'}
        post.return_value = resp

        with self.assertRaises(UnityAdsUploadError):
            UnityAdsService._upload_creative_sync(make_material())


if __name__ == '__main__':
    unittest.main()
