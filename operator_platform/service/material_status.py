# -*- encoding: utf-8 -*-
#
# @Date: 2026

VALID_STATUSES = {'pending', 'in_progress', 'completed'}


def apply_production_status(old_status, new_status, started_date, completed_date, today):
    if new_status not in VALID_STATUSES:
        raise ValueError('invalid status')
    started_date = started_date or ''
    completed_date = completed_date or ''
    if new_status == 'in_progress' and not started_date:
        started_date = today
    if new_status == 'completed' and old_status != 'completed':
        completed_date = today
    return {
        'production_status': new_status,
        'started_date': started_date,
        'completed_date': completed_date,
    }
