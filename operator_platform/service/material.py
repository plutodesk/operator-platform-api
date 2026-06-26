# -*- encoding: utf-8 -*-
#
# @Date: 2026

from datetime import date

from bson.objectid import ObjectId

from operator_platform.db import Material
from operator_platform.error import ParamsError
from operator_platform.service.material_status import apply_production_status
from seal.utils.tools import time10

__all__ = [
    'MaterialService',
]

MATERIAL_FIELDS = [
    'name', 'product', 'material_type', 'priority', 'creative_type',
    'creative_user_ids', 'producer_user_ids', 'tag_ids', 'task_description',
    'material_url', 'upload_path', 'upload_paths', 'production_status',
    'language', 'size', 'ads_operator_ids', 'channel_usage',
]


class MaterialService(object):

    INVOLVEMENT_MAP = {
        'producer': 'producer_user_ids',
        'creative': 'creative_user_ids',
        'ads_operator': 'ads_operator_ids',
    }

    @classmethod
    def _object_id(cls, material_id):
        try:
            return ObjectId(material_id)
        except Exception:
            raise ParamsError

    @classmethod
    def _today(cls):
        return date.today().strftime('%Y-%m-%d')

    @classmethod
    def _build_spec(cls, filters, current_user_id=None):
        spec = {}
        if filters.get('keyword'):
            spec['name'] = {'$regex': filters['keyword'], '$options': 'i'}
        if filters.get('product'):
            spec['product'] = filters['product']
        if filters.get('production_status'):
            spec['production_status'] = filters['production_status']
        if filters.get('material_type'):
            spec['material_type'] = filters['material_type']
        if filters.get('tag_ids'):
            spec['tag_ids'] = {'$all': filters['tag_ids']}
        if filters.get('producer_user_ids'):
            spec['producer_user_ids'] = {'$in': filters['producer_user_ids']}
        if filters.get('creative_user_ids'):
            spec['creative_user_ids'] = {'$in': filters['creative_user_ids']}
        involvement = filters.get('involvement')
        if involvement in cls.INVOLVEMENT_MAP and current_user_id:
            spec[cls.INVOLVEMENT_MAP[involvement]] = current_user_id
        elif filters.get('ads_operator_ids'):
            spec['ads_operator_ids'] = {'$in': filters['ads_operator_ids']}
        if filters.get('language'):
            spec['language'] = filters['language']
        if filters.get('size'):
            spec['size'] = filters['size']
        channels = filters.get('channels') or []
        for ch in channels:
            spec[f'channel_usage.{ch}'] = True
        date_from = filters.get('completed_date_from')
        date_to = filters.get('completed_date_to')
        if date_from or date_to:
            spec['completed_date'] = {}
            if date_from:
                spec['completed_date']['$gte'] = date_from
            if date_to:
                spec['completed_date']['$lte'] = date_to
        return spec

    @classmethod
    async def list_materials(cls, page=1, page_size=20, current_user_id=None, **filters):
        page = max(int(page or 1), 1)
        page_size = int(page_size or 20)
        if page_size not in (20, 50, 100):
            page_size = 20
        spec = cls._build_spec(filters, current_user_id=current_user_id)
        total = await Material.count_documents(spec)
        skip = (page - 1) * page_size
        material_list = await Material.query(
            spec,
            sort=[('c_time', -1)],
            skip=skip,
            limit=page_size,
        )
        return {
            'items': [m.info for m in material_list],
            'total': total,
            'page': page,
            'page_size': page_size,
        }

    @classmethod
    def _normalize_channel_usage(cls, value):
        base = {'google': False, 'facebook': False, 'unity': False}
        if isinstance(value, dict):
            base.update({k: bool(value.get(k)) for k in base})
        return base

    @classmethod
    def _normalize_upload_fields(cls, fields):
        paths = fields.get('upload_paths')
        if paths is None and fields.get('upload_path'):
            paths = [fields['upload_path']]
        elif paths is None:
            paths = []
        fields['upload_paths'] = [path for path in paths if path]
        fields['upload_path'] = fields['upload_paths'][0] if fields['upload_paths'] else ''
        return fields

    @classmethod
    def _extract_fields(cls, item):
        data = {}
        for key in MATERIAL_FIELDS:
            if key in item:
                data[key] = item[key]
        if 'channel_usage' in data:
            data['channel_usage'] = cls._normalize_channel_usage(data['channel_usage'])
        return cls._normalize_upload_fields(data)

    @classmethod
    async def _create_material(cls, item, today):
        fields = cls._extract_fields(item)
        status = fields.get('production_status') or 'pending'
        status_patch = apply_production_status(
            'pending', status, '', '', today,
        )
        now = time10()
        material = Material(
            name=fields.get('name') or '',
            product=fields.get('product') or '',
            material_type=fields.get('material_type') or '',
            priority=fields.get('priority') or '',
            creative_type=fields.get('creative_type') or '',
            creative_user_ids=fields.get('creative_user_ids') or [],
            producer_user_ids=fields.get('producer_user_ids') or [],
            tag_ids=fields.get('tag_ids') or [],
            task_description=fields.get('task_description') or {'text': '', 'images': []},
            material_url=fields.get('material_url') or '',
            upload_path=fields.get('upload_path') or '',
            upload_paths=fields.get('upload_paths') or [],
            production_status=status_patch['production_status'],
            started_date=status_patch['started_date'],
            completed_date=status_patch['completed_date'],
            language=fields.get('language') or '',
            size=fields.get('size') or '',
            ads_operator_ids=fields.get('ads_operator_ids') or [],
            channel_usage=cls._normalize_channel_usage(fields.get('channel_usage')),
            created_date=today,
            version=1,
            c_time=now,
            u_time=now,
        )
        await material.save()
        return material

    @classmethod
    async def publish(cls, creates=None, updates=None, deletes=None):
        creates = creates or []
        updates = updates or []
        deletes = deletes or []
        today = cls._today()
        succeeded = {'created': [], 'updated': [], 'deleted': []}
        conflicts = []

        for item in creates:
            material = await cls._create_material(item, today)
            succeeded['created'].append(material.id)

        for item in updates:
            material_id = item.get('id')
            version = item.get('version')
            if not material_id or version is None:
                conflicts.append({
                    'id': material_id or '',
                    'action': 'update',
                    'message': 'Params Error',
                })
                continue
            existing = await Material.find_one({'_id': cls._object_id(material_id)})
            if not existing or existing.version != version:
                conflicts.append({
                    'id': material_id,
                    'action': 'update',
                    'message': '数据已被他人更新，请刷新后再编辑',
                    'serverMaterial': existing.info if existing else None,
                })
                continue
            fields = cls._extract_fields(item)
            new_status = fields.get('production_status', existing.production_status)
            status_patch = apply_production_status(
                existing.production_status,
                new_status,
                existing.started_date,
                existing.completed_date,
                today,
            )
            update_doc = {
                **fields,
                **status_patch,
                'version': existing.version + 1,
                'u_time': time10(),
            }
            for key, value in update_doc.items():
                setattr(existing, key, value)
            await existing.save()
            succeeded['updated'].append(material_id)

        for item in deletes:
            material_id = item.get('id')
            version = item.get('version')
            if not material_id or version is None:
                conflicts.append({
                    'id': material_id or '',
                    'action': 'delete',
                    'message': 'Params Error',
                })
                continue
            existing = await Material.find_one({'_id': cls._object_id(material_id)})
            if not existing:
                conflicts.append({
                    'id': material_id,
                    'action': 'delete',
                    'message': 'Params Error',
                })
                continue
            if existing.production_status != 'pending':
                conflicts.append({
                    'id': material_id,
                    'action': 'delete',
                    'message': '仅未制作任务可删除',
                    'serverMaterial': existing.info,
                })
                continue
            if existing.version != version:
                conflicts.append({
                    'id': material_id,
                    'action': 'delete',
                    'message': '数据已被他人更新，请刷新后再编辑',
                    'serverMaterial': existing.info,
                })
                continue
            await Material.find_one_and_delete({'_id': existing._id})
            succeeded['deleted'].append(material_id)

        return {'succeeded': succeeded, 'conflicts': conflicts}
