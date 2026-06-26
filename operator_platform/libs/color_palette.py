# -*- encoding: utf-8 -*-
#
# @Date: 2026

__all__ = [
    'PALETTE',
    'assign_color',
]

# Keep in sync with operator-platform-ui/src/libs/colorPalette.ts
PALETTE = [
    '#3370FF',
    '#00D6B9',
    '#34C724',
    '#FFC60A',
    '#FF8800',
    '#F54A45',
    '#7A45E6',
    '#F01D94',
    '#8F959E',
    '#14C0FF',
    '#B449C3',
    '#645ABF',
]


def assign_color(key):
    """Deterministic palette color for a stable string key (e.g. tag name)."""
    text = str(key or '')
    hash_value = 0
    for char in text:
        hash_value = (hash_value * 31 + ord(char)) & 0xFFFFFFFF
    return PALETTE[hash_value % len(PALETTE)]
