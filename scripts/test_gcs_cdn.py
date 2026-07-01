#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""在 DEBUG=false（生产模式）下检测 GCS 桶与 CDN 权限，不受本地 fallback 干扰。"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import operator_platform  # noqa: F401 — 加载 conf.yaml

from google.api_core.exceptions import Forbidden, GoogleAPIError
from google.cloud.storage.client import Client
from google.oauth2.service_account import Credentials
from seal.conf import options

from operator_platform.db.local_storage import UPLOAD_ROOT
from operator_platform.service.cdn import effective_cdn_url, use_local_upload
from operator_platform.service.resource import ResourceService

TEST_PREFIX = '_healthcheck/operator-platform'


@dataclass
class CheckItem:
    name: str
    passed: bool | None  # None = 跳过
    detail: str = ''


@dataclass
class Report:
    conf_lines: list[str] = field(default_factory=list)
    prod_lines: list[str] = field(default_factory=list)
    runtime_notes: list[str] = field(default_factory=list)
    checks: list[CheckItem] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)

    def add(self, name: str, passed: bool | None, detail: str = '') -> None:
        self.checks.append(CheckItem(name=name, passed=passed, detail=detail))

    @property
    def all_passed(self) -> bool:
        return all(c.passed is not False for c in self.checks if c.passed is not None)


@contextmanager
def _production_mode():
    """检测期间强制 DEBUG=false，模拟生产行为（GCS 403 直接报错，不走本地 fallback）。"""
    saved = options.DEBUG
    options.DEBUG = False
    try:
        yield
    finally:
        options.DEBUG = saved


def _short_error(msg: str, max_len: int = 200) -> str:
    if 'storage.objects.create' in msg:
        return '无 storage.objects.create 权限，无法向桶写入对象'
    if 'storage.buckets.get' in msg:
        return '无 storage.buckets.get 权限，无法读取桶元数据'
    if len(msg) > max_len:
        return msg[:max_len] + '…'
    return msg


def _gcs_client() -> Client:
    return Client(credentials=Credentials.from_service_account_info(
        options.GC_KEY,
        scopes=['https://www.googleapis.com/auth/devstorage.read_write'],
    ))


def _collect_config(report: Report) -> None:
    local_upload = getattr(options, 'LOCAL_UPLOAD', None)
    gc_key = options.GC_KEY or {}

    report.conf_lines = [
        f'LOCAL              = {options.LOCAL}',
        f'LOCAL_UPLOAD       = {local_upload}',
        f'DEBUG              = {options.DEBUG}',
        f'BUCKET             = {(options.BUCKET or "").strip() or "（未配置）"}',
        f'CDN_URL            = {(options.CDN_URL or "").strip() or "（未配置）"}',
        f'GC_KEY 服务账号     = {gc_key.get("client_email") or "（未配置）"}',
        f'use_local_upload() = {use_local_upload()}',
        f'effective_cdn_url()= {effective_cdn_url()}  ← 当前运行时的 CDN 地址',
    ]

    with _production_mode():
        report.prod_lines = [
            'DEBUG              = false（检测期间强制）',
            f'use_local_upload() = {use_local_upload()}',
            f'effective_cdn_url()= {effective_cdn_url()}  ← 生产模式 CDN 地址',
            'GCS 403            = 直接报错，不 fallback 本地',
        ]

    if options.DEBUG:
        report.runtime_notes.append(
            '当前 conf.yaml 中 DEBUG=true：线上 API 会返回本地 CDN 地址，'
            '且 GCS 403 时上传会静默落到本地。'
        )
    if use_local_upload():
        if local_upload is not None:
            report.runtime_notes.append('当前 LOCAL_UPLOAD=true：上传始终走本地，与 DEBUG 无关。')
        else:
            report.runtime_notes.append('当前 LOCAL=true：上传始终走本地，与 DEBUG 无关。')


def _check_gcs_credentials() -> tuple[bool, str]:
    gc_key = options.GC_KEY or {}
    if not gc_key.get('client_email') or not gc_key.get('private_key'):
        return False, 'GC_KEY 缺少 client_email 或 private_key'
    try:
        Credentials.from_service_account_info(
            gc_key,
            scopes=['https://www.googleapis.com/auth/devstorage.read_write'],
        )
    except Exception as exc:  # noqa: BLE001
        return False, f'GC_KEY 无效: {exc}'
    return True, '凭证格式正确'


def _check_gcs_bucket_metadata(bucket_name: str) -> tuple[bool, str]:
    try:
        _gcs_client().bucket(bucket_name).reload()
    except Forbidden as exc:
        return False, _short_error(exc.message)
    except GoogleAPIError as exc:
        return False, str(exc)
    return True, f'桶 "{bucket_name}" 元数据可读'


def _gcs_direct_roundtrip(bucket_name: str, blob_name: str, body: bytes) -> tuple[bool, str]:
    blob = _gcs_client().bucket(bucket_name).blob(blob_name)
    try:
        blob.upload_from_string(body, content_type='text/plain')
        if not blob.exists():
            return False, '上传成功但 blob.exists() 为 False'
        if blob.download_as_bytes() != body:
            return False, '下载内容与上传内容不一致'
        blob.delete()
        if blob.exists():
            return False, '删除失败，对象仍存在'
    except Forbidden as exc:
        return False, _short_error(exc.message)
    except GoogleAPIError as exc:
        return False, str(exc)
    return True, f'对象 {blob_name} 上传/下载/删除均正常'


def _gcs_object_exists(bucket_name: str, object_key: str) -> bool:
    try:
        return _gcs_client().bucket(bucket_name).blob(object_key).exists()
    except GoogleAPIError:
        return False


async def _gcs_upload_via_service_production(prefix: str, body: bytes) -> tuple[bool, str, str]:
    """在 DEBUG=false 下调用 ResourceService，403 直接失败，不 fallback 本地。"""
    upload_file = {
        'filename': 'probe.txt',
        'body': body,
        'content_type': 'text/plain',
    }
    with _production_mode():
        try:
            name = await ResourceService.upload_resource(prefix, upload_file)
        except Forbidden as exc:
            return False, '', _short_error(exc.message)
        except Exception as exc:  # noqa: BLE001
            return False, '', str(exc)

    local_path = os.path.join(UPLOAD_ROOT, name)
    if os.path.isfile(local_path):
        return False, name, f'意外写入本地（生产模式不应发生）: {local_path}'

    bucket_name = (options.BUCKET or '').strip()
    if bucket_name and _gcs_object_exists(bucket_name, name):
        return True, name, f'对象已写入 GCS: gs://{bucket_name}/{name}'

    return False, name, f'上传返回 key={name}，但在 GCS 中未找到对象'


def _http_probe(url: str, method: str = 'GET', timeout: int = 15) -> tuple[bool, int | None, str]:
    req = Request(url, method=method, headers={'User-Agent': 'operator-platform-gcs-cdn-test/1.0'})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return True, resp.status, ''
    except HTTPError as exc:
        return True, exc.code, f'HTTP {exc.code}'
    except URLError as exc:
        return False, None, str(exc.reason)


def _production_cdn_base() -> str:
    cdn_base = (options.CDN_URL or '').strip()
    if not cdn_base:
        return ''
    return cdn_base if cdn_base.endswith('/') else f'{cdn_base}/'


def _run_checks(args: argparse.Namespace) -> Report:
    report = Report()
    _collect_config(report)

    bucket_name = (options.BUCKET or '').strip()
    cdn_base = _production_cdn_base()

    with _production_mode():
        probe_id = uuid.uuid4().hex[:12]
        probe_body = (
            f'operator-platform probe {probe_id} @ '
            f'{datetime.now(timezone.utc).isoformat()}'
        ).encode()
        probe_blob = f'{TEST_PREFIX}/{probe_id}.txt'

        cred_ok, cred_detail = _check_gcs_credentials()
        report.add('GCS 服务账号凭证', cred_ok, cred_detail)

        if not bucket_name:
            report.add('GCS 桶配置', False, 'BUCKET 未配置')
        elif not cred_ok:
            report.add('GCS 桶元数据', None, '凭证无效，已跳过')
            report.add('GCS 对象上传（直连）', None, '凭证无效，已跳过')
            report.add('GCS 上传（ResourceService, DEBUG=false）', None, '凭证无效，已跳过')
            report.add('CDN 对象 URL', None, '凭证无效，已跳过')
        else:
            meta_ok, meta_detail = _check_gcs_bucket_metadata(bucket_name)
            report.add(
                'GCS 桶元数据',
                True if meta_ok else None,
                meta_detail if meta_ok else f'{meta_detail}（不影响对象上传测试）',
            )

            if use_local_upload():
                report.add('GCS 对象上传（直连）', None, 'LOCAL/LOCAL_UPLOAD 开启，生产模式也会走本地，已跳过 GCS 上传')
                report.add('GCS 上传（ResourceService, DEBUG=false）', None, '同上，已跳过')
                report.add('CDN 对象 URL', None, '同上，已跳过')
            else:
                rt_ok, rt_detail = _gcs_direct_roundtrip(bucket_name, probe_blob, probe_body)
                report.add('GCS 对象上传（直连）', rt_ok, rt_detail)

                svc_ok, svc_name, svc_detail = asyncio.run(
                    _gcs_upload_via_service_production(f'{TEST_PREFIX}/service', probe_body),
                )
                report.add('GCS 上传（ResourceService, DEBUG=false）', svc_ok, svc_detail)
                if svc_ok and svc_name:
                    try:
                        _gcs_client().bucket(bucket_name).blob(svc_name).delete()
                    except GoogleAPIError:
                        pass

                if cdn_base and rt_ok:
                    cdn_probe_blob = f'{TEST_PREFIX}/cdn-probe-{probe_id}.txt'
                    cdn_rt_ok, cdn_rt_detail = _gcs_direct_roundtrip(
                        bucket_name, cdn_probe_blob, probe_body,
                    )
                    if not cdn_rt_ok:
                        report.add('CDN 对象 URL', False, f'探针对象上传 GCS 失败: {cdn_rt_detail}')
                    else:
                        cdn_object_url = f'{cdn_base}{cdn_probe_blob}'
                        reachable = False
                        status = None
                        err = ''
                        for attempt in range(1, args.cdn_retries + 1):
                            reachable, status, err = _http_probe(cdn_object_url, method='GET')
                            if reachable and status == 200:
                                break
                            if attempt < args.cdn_retries:
                                time.sleep(args.cdn_wait)
                        cdn_ok = reachable and status == 200
                        detail = f'GET {cdn_object_url} → HTTP {status or "无响应"}'
                        if err and not cdn_ok:
                            detail += f'（{err}）'
                        report.add('CDN 对象 URL', cdn_ok, detail)
                        try:
                            _gcs_client().bucket(bucket_name).blob(cdn_probe_blob).delete()
                        except GoogleAPIError:
                            pass
                elif not cdn_base:
                    report.add('CDN 对象 URL', None, 'CDN_URL 未配置，已跳过')
                else:
                    report.add('CDN 对象 URL', None, 'GCS 直连上传失败，已跳过')

        if not cdn_base:
            report.add('CDN 根 URL 可达性', False, 'CDN_URL 未配置')
        else:
            reachable, status, err = _http_probe(cdn_base, method='HEAD')
            if not reachable or status is None:
                reachable, status, err = _http_probe(cdn_base, method='GET')
            if not reachable:
                report.add('CDN 根 URL 可达性', False, f'无法连接 {cdn_base}（{err}）')
            elif status in (403, 404):
                report.add(
                    'CDN 根 URL 可达性',
                    True,
                    f'HEAD/GET {cdn_base} → HTTP {status}（根路径 403/404 正常，关键看对象 URL）',
                )
            else:
                report.add('CDN 根 URL 可达性', True, f'HEAD/GET {cdn_base} → HTTP {status}')

    failed_gcs = any(
        c.passed is False and 'GCS' in c.name
        for c in report.checks
    )
    if failed_gcs:
        report.tips.append(
            'GCS 权限不足：请在 GCP Console 为服务账号授予桶的 Storage Object Admin 权限。'
        )
    if options.DEBUG and report.all_passed:
        report.tips.append(
            '生产模式检测已通过。若要将线上行为切换为 GCS/CDN，请将 conf.yaml 中 DEBUG 改为 false。'
        )
    elif options.DEBUG and not report.all_passed:
        report.tips.append(
            '当前 DEBUG=true 会掩盖 GCS 权限问题（403 时 fallback 本地）。'
            '请先修复上方失败项，再将 DEBUG 改为 false。'
        )

    return report


def _status_label(passed: bool | None) -> str:
    if passed is True:
        return '通过'
    if passed is False:
        return '失败'
    return '跳过'


def _print_report(report: Report) -> None:
    print('\n' + '=' * 60)
    print('GCS / CDN 可用性检测报告（生产模式 DEBUG=false）')
    print('=' * 60)

    print('\n【当前 conf.yaml 配置（线上实际行为）】')
    for line in report.conf_lines:
        print(f'  {line}')

    if report.runtime_notes:
        print('\n【与本次检测的差异说明】')
        for note in report.runtime_notes:
            print(f'  · {note}')

    print('\n【本次检测模式（模拟 DEBUG=false 生产环境）】')
    for line in report.prod_lines:
        print(f'  {line}')

    print('\n【检测结果】（以上述生产模式执行，不含本地 fallback）')
    for item in report.checks:
        label = _status_label(item.passed)
        print(f'  [{label}] {item.name}')
        if item.detail:
            print(f'         {item.detail}')

    passed = sum(1 for c in report.checks if c.passed is True)
    failed = sum(1 for c in report.checks if c.passed is False)
    skipped = sum(1 for c in report.checks if c.passed is None)
    print(f'\n【统计】通过 {passed} / 失败 {failed} / 跳过 {skipped}')

    if report.tips:
        print('\n【建议】')
        for tip in report.tips:
            print(f'  · {tip}')

    print('\n【结论】', end='')
    if report.all_passed:
        print('生产模式下 GCS 与 CDN 链路可用，权限正常。')
    else:
        print('生产模式下存在失败项，GCS/CDN 权限或配置有问题。')
    print('=' * 60 + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='在 DEBUG=false 生产模式下检测 GCS 桶与 CDN 权限',
    )
    parser.add_argument(
        '--cdn-retries',
        type=int,
        default=3,
        help='CDN 对象 URL 探测重试次数（默认 3）',
    )
    parser.add_argument(
        '--cdn-wait',
        type=float,
        default=2.0,
        help='CDN 对象 URL 探测间隔秒数（默认 2）',
    )
    args = parser.parse_args()
    report = _run_checks(args)
    _print_report(report)
    sys.exit(0 if report.all_passed else 1)


if __name__ == '__main__':
    main()
