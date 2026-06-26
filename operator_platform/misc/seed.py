# -*- encoding: utf-8 -*-
#
# @Date: 2026

import argparse
import asyncio

from seal.utils.tools import time10

from operator_platform.db import Material, Tag, User
from operator_platform.libs.color_palette import assign_color

PRESET_TAGS = [
    'AI生成', '内容迭代', '游戏过程', '真人拍摄', 'ASMR', '节日限定', '奇幻', '风俗',
    '温馨', '可爱', '夸张卡通', '写实', '复古', '暗黑', '明亮', '美漫', '动物', '植物',
    '人群', '老人', '小孩', '女人', '男人', '室内场景', '室外风景', '交通工具', '静物',
    '时尚', '文字', '宗教',
]

SEED_USERS = [
    {'email': 'admin@bidderdesk.com', 'name': 'Admin', 'role': 'admin'},
    {'email': 'alice@bidderdesk.com', 'name': 'Alice', 'role': 'user'},
    {'email': 'bob@bidderdesk.com', 'name': 'Bob', 'role': 'user'},
    {'email': 'carol@bidderdesk.com', 'name': 'Carol', 'role': 'user'},
    {'email': 'dave@bidderdesk.com', 'name': 'Dave', 'role': 'user'},
]

# 样例日期：创建 / 开始 / 完成（测试用 2026-06-24）
SAMPLE_MATERIALS = [
  # name, product, status, priority, created_date, started_date, completed_date
    ('春节素材 A', 'Legacy Jigsaw', 'pending', 'P0', '2026-06-20', '', ''),
    ('夏日活动 B', 'Fantasy Jigsaw', 'in_progress', 'P1', '2026-06-22', '2026-06-24', ''),
    ('万圣节 C', 'Fun Color', 'completed', 'P2', '2026-06-21', '2026-06-23', '2026-06-24'),
    ('试玩素材 D', 'Color Fow', 'pending', 'P1', '2026-06-19', '', ''),
    ('迭代视频 E', 'Color Master', 'in_progress', 'P0', '2026-06-23', '2026-06-24', ''),
    ('原创图片 F', 'Pixel Coloring', 'completed', 'P1', '2026-06-18', '2026-06-22', '2026-06-24'),
    ('ASMR 素材 G', 'Legacy Jigsaw', 'pending', 'P2', '2026-06-24', '', ''),
    ('真人拍摄 H', 'Fantasy Jigsaw', 'in_progress', 'P1', '2026-06-24', '2026-06-24', ''),
    ('节日限定 I', 'Fun Color', 'completed', 'P0', '2026-06-17', '2026-06-20', '2026-06-24'),
    ('游戏过程 J', 'Color Master', 'pending', 'P2', '2026-06-15', '', ''),
]


async def seed_tags():
    now = time10()
    for index, name in enumerate(PRESET_TAGS):
        existing = await Tag.find_one({'name': name})
        if existing:
            if not existing.color:
                existing.color = assign_color(name)
                await existing.save()
            continue
        tag = Tag(name=name, color=assign_color(name), sort=index, c_time=now)
        await tag.save()


async def seed_users():
    now = time10()
    for item in SEED_USERS:
        if await User.find_one({'email': item['email']}):
            continue
        user = User(
            user_id=f'manual:{item["email"]}',
            name=item['name'],
            email=item['email'],
            avatar='',
            role=item['role'],
            active=True,
            c_time=now,
        )
        await user.save()


async def seed_materials():
    if await Material.count_documents({}) > 0:
        return
    now = time10()
    for index, row in enumerate(SAMPLE_MATERIALS):
        name, product, status, priority, created_date, started_date, completed_date = row
        material = Material(
            name=name,
            product=product,
            material_type=['video', 'image', 'playable'][index % 3],
            priority=priority,
            creative_type='iteration' if index % 2 else 'original',
            creative_user_ids=[],
            producer_user_ids=[],
            tag_ids=[],
            task_description={'text': f'{name} 任务描述', 'images': []},
            material_url='',
            upload_path='',
            production_status=status,
            started_date=started_date,
            completed_date=completed_date,
            created_date=created_date,
            version=1,
            c_time=now + (len(SAMPLE_MATERIALS) - index),
            u_time=now + (len(SAMPLE_MATERIALS) - index),
        )
        await material.save()


async def refresh_material_dates():
    """按制作状态刷新已有素材的日期字段（便于本地测试）。"""
    materials = await Material.query({})
    for material in materials:
        status = material.production_status
        if status == 'pending':
            material.started_date = ''
            material.completed_date = ''
            if not material.created_date:
                material.created_date = '2026-06-20'
        elif status == 'in_progress':
            material.started_date = '2026-06-24'
            material.completed_date = ''
            if not material.created_date:
                material.created_date = '2026-06-22'
        elif status == 'completed':
            material.started_date = material.started_date or '2026-06-23'
            material.completed_date = '2026-06-24'
            if not material.created_date:
                material.created_date = '2026-06-21'
        await material.save()
    print(f'refreshed dates on {len(materials)} materials')


async def main(refresh_dates=False):
    await seed_tags()
    await seed_users()
    await seed_materials()
    if refresh_dates:
        await refresh_material_dates()
    print('seed complete')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--refresh-dates',
        action='store_true',
        help='refresh started/completed/created dates on existing materials',
    )
    args = parser.parse_args()
    asyncio.get_event_loop().run_until_complete(main(refresh_dates=args.refresh_dates))
