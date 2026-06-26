# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseMongo

__all__ = [
    'Material',
]


class Material(BaseMongo):
    structure = {
        'name': str,
        'product': str,
        'material_type': str,
        'priority': str,
        'creative_type': str,
        'creative_user_ids': list,
        'producer_user_ids': list,
        'tag_ids': list,
        'task_description': dict,
        'material_url': str,
        'upload_path': str,
        'upload_paths': list,
        'production_status': str,
        'started_date': str,
        'completed_date': str,
        'created_date': str,
        'version': int,
        'c_time': int,
        'u_time': int,
    }

    default = {
        'creative_user_ids': [],
        'producer_user_ids': [],
        'tag_ids': [],
        'task_description': {'text': '', 'images': []},
        'material_url': '',
        'upload_path': '',
        'upload_paths': [],
        'production_status': 'pending',
        'started_date': '',
        'completed_date': '',
        'version': 1,
    }
