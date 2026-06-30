# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from operator_platform.misc.crypto import decrypt_json, encrypt_json, mask_secret
from operator_platform.service.ad_platform_config import AdPlatformConfigService
from operator_platform.service.token_config import TokenConfigService


class CryptoTest(unittest.TestCase):

    @patch('operator_platform.misc.crypto.options')
    def test_encrypt_decrypt_roundtrip(self, options):
        options.CONFIG_ENCRYPTION_KEY = 'test-secret-key'
        options.COFIG_SECRET = ''
        payload = {'refresh_token': 'abc123', 'developer_token': 'dev456'}
        enc = encrypt_json(payload)
        self.assertEqual(decrypt_json(enc), payload)

    def test_mask_secret(self):
        self.assertEqual(mask_secret('1234567890'), '1234…7890')


class TokenConfigServiceTest(unittest.IsolatedAsyncioTestCase):

    @patch('operator_platform.service.token_config.encrypt_json')
    @patch('operator_platform.service.token_config.decrypt_json')
    @patch('operator_platform.service.token_config.TokenConfig')
    async def test_create_google_token(self, token_cls, decrypt_json_mock, encrypt_json_mock):
        encrypt_json_mock.return_value = 'enc'
        decrypt_json_mock.return_value = {
            'refresh_token': 'refresh',
            'developer_token': 'dev',
        }
        token = token_cls.return_value
        token.channel = 'google'
        token.info = {'id': 't1', 'name': 'Main', 'channel': 'google', 'enabled': True}
        token._credentials_enc = 'enc'
        token.save = unittest.mock.AsyncMock()

        with patch.object(TokenConfigService, '_public_info', return_value={'id': 't1'}):
            result = await TokenConfigService.create_token(
                name='Main',
                channel='google',
                credentials={
                    'refresh_token': 'refresh',
                    'developer_token': 'dev',
                },
            )
        self.assertEqual(result['id'], 't1')


class AdPlatformConfigServiceTest(unittest.IsolatedAsyncioTestCase):

    def test_normalize_google_settings(self):
        settings = AdPlatformConfigService._normalize_settings(
            'google',
            {'customer_id': '896-985-1272', 'login_customer_id': ''},
        )
        self.assertEqual(settings['customer_id'], '8969851272')

    @patch('operator_platform.service.ad_platform_config.AdPlatformConfig')
    async def test_ensure_name_unique_rejects_duplicate(self, config_cls):
        existing = unittest.mock.Mock()
        existing.id = 'cfg1'
        config_cls.find_one = unittest.mock.AsyncMock(return_value=existing)

        with self.assertRaises(Exception):
            await AdPlatformConfigService._ensure_name_unique('Unity - Fun Color')

        await AdPlatformConfigService._ensure_name_unique('Unity - Fun Color', exclude_id='cfg1')
        config_cls.find_one.assert_called_with({'name': 'Unity - Fun Color'})

    @patch('operator_platform.service.ad_platform_config.TokenConfig')
    @patch('operator_platform.service.ad_platform_config.AdPlatformConfig')
    async def test_create_config_allows_duplicate_product(self, config_cls, token_cls):
        token_id = '665a00000000000000000002'
        token = unittest.mock.Mock()
        token.id = token_id
        token.name = 'Unity 默认'
        token.enabled = True
        token.channel = 'unity'
        token_cls.find_one = unittest.mock.AsyncMock(return_value=token)

        config_cls.find_one = unittest.mock.AsyncMock(return_value=None)
        config = config_cls.return_value
        config.id = 'cfg2'
        config.info = {'id': 'cfg2', 'name': 'test1', 'channel': 'unity', 'product': 'Color Fow'}
        config.save = unittest.mock.AsyncMock()

        with patch.object(
            AdPlatformConfigService, '_validate_channel', new=unittest.mock.AsyncMock(return_value='unity'),
        ):
            result = await AdPlatformConfigService.create_config(
                name='test1',
                channel='unity',
                product='Color Fow',
                token_config_id=token_id,
                settings={
                    'organization_id': '1375631575107',
                    'campaign_set_id': '68f60802872bd4a7a9d50071',
                },
            )
        self.assertEqual(result['id'], 'cfg2')
        config.save.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
