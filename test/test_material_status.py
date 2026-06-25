# test/test_material_status.py
import unittest

from operator_platform.service.material_status import apply_production_status


class MaterialStatusTest(unittest.TestCase):
    def test_first_in_progress_sets_started_date(self):
        result = apply_production_status('pending', 'in_progress', '', '', '2026-06-25')
        self.assertEqual(result['production_status'], 'in_progress')
        self.assertEqual(result['started_date'], '2026-06-25')

    def test_second_in_progress_keeps_started_date(self):
        result = apply_production_status('pending', 'in_progress', '2026-06-01', '', '2026-06-25')
        self.assertEqual(result['started_date'], '2026-06-01')

    def test_enter_completed_updates_completed_date(self):
        result = apply_production_status('in_progress', 'completed', '2026-06-01', '', '2026-06-25')
        self.assertEqual(result['completed_date'], '2026-06-25')

    def test_reenter_completed_updates_completed_date(self):
        result = apply_production_status('in_progress', 'completed', '2026-06-01', '2026-06-10', '2026-06-25')
        self.assertEqual(result['completed_date'], '2026-06-25')
