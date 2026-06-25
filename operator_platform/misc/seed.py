# -*- encoding: utf-8 -*-
#
# @Date: 2026

import asyncio

from seal.utils.tools import time10

from operator_platform.db import Material, Tag, User

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

PRODUCTS = [
    'Legacy Jigsaw', 'Fantasy Jigsaw', 'Fun Color', 'Color Fow', 'Color Master', 'Pixel Coloring',
]


async def seed_tags():
    now = time10()
    for index, name in enumerate(PRESET_TAGS):
        if await Tag.find_one({'name': name}):
            continue
        tag = Tag(name=name, color='', sort=index, c_time=now)
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
    today = __import__('datetime').date.today().strftime('%Y-%m-%d')
    samples = [
        ('春节素材 A', 'Legacy Jigsaw', 'pending', 'P0'),
        ('夏日活动 B', 'Fantasy Jigsaw', 'in_progress', 'P1'),
        ('万圣节 C', 'Fun Color', 'completed', 'P2'),
        ('试玩素材 D', 'Color Fow', 'pending', 'P1'),
        ('迭代视频 E', 'Color Master', 'in_progress', 'P0'),
        ('原创图片 F', 'Pixel Coloring', 'completed', 'P1'),
        ('ASMR 素材 G', 'Legacy Jigsaw', 'pending', 'P2'),
        ('真人拍摄 H', 'Fantasy Jigsaw', 'in_progress', 'P1'),
        ('节日限定 I', 'Fun Color', 'completed', 'P0'),
        ('游戏过程 J', 'Color Master', 'pending', 'P2'),
    ]
    for index, (name, product, status, priority) in enumerate(samples):
        started = today if status != 'pending' else ''
        completed = today if status == 'completed' else ''
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
            started_date=started,
            completed_date=completed,
            created_date=today,
            version=1,
            c_time=now + index,
            u_time=now + index,
        )
        await material.save()


async def main():
    await seed_tags()
    await seed_users()
    await seed_materials()
    print('seed complete')


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
