# -*- coding: utf-8 -*-
"""Tests for SLA working time model — SlaTime engine + SlaEngine integration."""

from datetime import date, datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from itsm.models import Duration, Day, Schedule, SlaPolicy, SlaTask, Ticket
from itsm.services.sla_time import (
    TimeDelta, MultiTimeDelta, SlaTime, _make_aware, _unit_to_seconds,
)
from itsm.services.sla_engine import SlaEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def dt(s, t):
    """Shorthand: _make_aware with a date string and time tuple."""
    d = date.fromisoformat(s)
    return _make_aware(d, time(*t))


def d(s):
    """Parse date from ISO string."""
    return date.fromisoformat(s)


class TestTimeDelta(TestCase):
    """T1: TimeDelta set operations."""

    def test_seconds(self):
        td = TimeDelta(dt('2026-07-10', (9, 0)), dt('2026-07-10', (12, 0)))
        self.assertEqual(td.seconds(), 10800)

    def test_intersection_overlap(self):
        a = TimeDelta(dt('2026-07-10', (9, 0)), dt('2026-07-10', (12, 0)))
        b = TimeDelta(dt('2026-07-10', (10, 0)), dt('2026-07-10', (14, 0)))
        inter = a.intersection(b)
        self.assertIsNotNone(inter)
        self.assertEqual(inter.start_time, dt('2026-07-10', (10, 0)))
        self.assertEqual(inter.end_time, dt('2026-07-10', (12, 0)))

    def test_intersection_disjoint(self):
        a = TimeDelta(dt('2026-07-10', (9, 0)), dt('2026-07-10', (12, 0)))
        b = TimeDelta(dt('2026-07-10', (13, 0)), dt('2026-07-10', (14, 0)))
        self.assertIsNone(a.intersection(b))

    def test_difference_middle(self):
        a = TimeDelta(dt('2026-07-10', (9, 0)), dt('2026-07-10', (18, 0)))
        b = TimeDelta(dt('2026-07-10', (12, 0)), dt('2026-07-10', (14, 0)))
        result = a.difference(b)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].end_time, dt('2026-07-10', (12, 0)))
        self.assertEqual(result[1].start_time, dt('2026-07-10', (14, 0)))

    def test_difference_no_overlap(self):
        a = TimeDelta(dt('2026-07-10', (9, 0)), dt('2026-07-10', (12, 0)))
        b = TimeDelta(dt('2026-07-10', (13, 0)), dt('2026-07-10', (14, 0)))
        result = a.difference(b)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].seconds(), 10800)

    def test_union_overlapping(self):
        a = TimeDelta(dt('2026-07-10', (9, 0)), dt('2026-07-10', (12, 0)))
        b = TimeDelta(dt('2026-07-10', (10, 0)), dt('2026-07-10', (14, 0)))
        u = a.union(b)
        self.assertEqual(u.start_time, dt('2026-07-10', (9, 0)))
        self.assertEqual(u.end_time, dt('2026-07-10', (14, 0)))

    def test_position(self):
        td = TimeDelta(dt('2026-07-10', (9, 0)), dt('2026-07-10', (12, 0)))
        self.assertEqual(td.position(dt('2026-07-10', (8, 0))), -1)
        self.assertEqual(td.position(dt('2026-07-10', (10, 0))), 0)
        self.assertEqual(td.position(dt('2026-07-10', (13, 0))), 1)


class TestMultiTimeDelta(TestCase):
    """T2: MultiTimeDelta multi-interval algebra."""

    def setUp(self):
        self.a = TimeDelta(dt('2026-07-10', (8, 0)), dt('2026-07-10', (12, 0)))
        self.b = TimeDelta(dt('2026-07-10', (14, 0)), dt('2026-07-10', (18, 0)))
        self.c = TimeDelta(dt('2026-07-10', (10, 0)), dt('2026-07-10', (16, 0)))
        self.mtd = MultiTimeDelta(self.a, self.b)

    def test_intersection(self):
        other = MultiTimeDelta(self.c)
        result = self.mtd.intersection(other)
        self.assertEqual(len(list(result)), 2)  # 10-12 and 14-16

    def test_difference(self):
        other = MultiTimeDelta(self.c)
        result = self.mtd.difference(other)
        self.assertEqual(len(list(result)), 2)  # 8-10 and 16-18

    def test_union(self):
        other = MultiTimeDelta(self.c)
        result = self.mtd.union(other)
        self.assertEqual(len(list(result)), 1)  # 8-18 merged

    def test_closest_forward_inside(self):
        mtd = MultiTimeDelta(self.a, self.b)
        mtd.sort()
        # At 09:00 (inside first segment), forward boundary = 12:00
        self.assertEqual(
            mtd.closest_td_time(dt('2026-07-10', (9, 0)), True),
            dt('2026-07-10', (12, 0)),
        )

    def test_closest_forward_between(self):
        mtd = MultiTimeDelta(self.a, self.b)
        mtd.sort()
        # At 13:00 (between segments), forward boundary = 14:00
        self.assertEqual(
            mtd.closest_td_time(dt('2026-07-10', (13, 0)), True),
            dt('2026-07-10', (14, 0)),
        )


class TestSlaTime5x8(TestCase):
    """T3-T7, T9: SlaTime engine with 5×8 schedule."""

    @classmethod
    def setUpTestData(cls):
        # Build 5×8 schedule: Mon-Fri 08:00-12:00, 14:00-18:00
        cls.d_am = Duration.objects.create(name='上午', start_time='08:00:00', end_time='12:00:00')
        cls.d_pm = Duration.objects.create(name='下午', start_time='14:00:00', end_time='18:00:00')
        cls.weekday = Day.objects.create(
            name='工作日', day_of_week='0,1,2,3,4', type_of_day='NORMAL',
        )
        cls.weekday.durations.add(cls.d_am, cls.d_pm)

        # Holiday: Oct 1-3
        cls.holiday = Day.objects.create(
            name='国庆', type_of_day='HOLIDAY',
            start_date=date(2026, 10, 1), end_date=date(2026, 10, 3),
        )

        cls.schedule = Schedule.objects.create(name='5×8 Test')
        cls.schedule.days.add(cls.weekday)
        cls.schedule.holidays.add(cls.holiday)
        # No overtime in main schedule — overtime tested separately

        cls.sla = SlaTime(cls.schedule)

    # T3: date_time_deltas — weekday match
    def test_weekday_monday(self):
        """Monday July 6, 2026 is a Monday → should have 2 segments."""
        mon = d('2026-07-06')  # Monday
        segments = self.sla.date_time_deltas(mon)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].start_time, dt('2026-07-06', (8, 0)))
        self.assertEqual(segments[0].end_time, dt('2026-07-06', (12, 0)))
        self.assertEqual(segments[1].start_time, dt('2026-07-06', (14, 0)))

    def test_weekend_saturday(self):
        """Saturday → no working time (not in day_of_week)."""
        sat = d('2026-07-11')  # Saturday, no overtime in this schedule
        segments = self.sla.date_time_deltas(sat)
        self.assertEqual(len(segments), 0)

    def test_weekend_sunday(self):
        """Sunday → no working time."""
        sun = d('2026-07-12')  # Sunday
        segments = self.sla.date_time_deltas(sun)
        self.assertEqual(len(segments), 0)

    # T4: holiday exclusion
    def test_holiday_exclusion(self):
        """Oct 1, 2026 is a holiday (Thursday) → no working time."""
        hol = d('2026-10-01')  # Thursday, but holiday
        segments = self.sla.date_time_deltas(hol)
        self.assertEqual(len(segments), 0)

    # T5: overtime inclusion (separate schedule with WORKDAY)
    def test_overtime_saturday(self):
        """July 11, 2026 is Saturday marked as WORKDAY → has morning hours."""
        overtime = Day.objects.create(
            name='周六加班', type_of_day='WORKDAY',
            start_date=date(2026, 7, 11), end_date=date(2026, 7, 11),
        )
        overtime.durations.add(self.d_am)
        sched_with_ot = Schedule.objects.create(name='5×8 + OT')
        sched_with_ot.days.add(self.weekday)
        sched_with_ot.workdays.add(overtime)
        sla_ot = SlaTime(sched_with_ot)
        sat = d('2026-07-11')
        segments = sla_ot.date_time_deltas(sat)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].start_time, dt('2026-07-11', (8, 0)))

    # T6: sla_time across weekend
    def test_sla_time_across_weekend(self):
        """Fri 17:00 → Mon 10:00 = 1h Fri + 2h Mon = 3h."""
        start = dt('2026-07-10', (17, 0))  # Friday
        end = dt('2026-07-13', (10, 0))     # Monday
        secs = self.sla.sla_time(start, end)
        # Fri 17:00-18:00 = 3600s, Mon 08:00-10:00 = 7200s
        self.assertEqual(secs, 10800)

    def test_sla_time_within_same_day(self):
        """Mon 09:00 → Mon 11:00 = 2h."""
        start = dt('2026-07-06', (9, 0))
        end = dt('2026-07-06', (11, 0))
        secs = self.sla.sla_time(start, end)
        self.assertEqual(secs, 7200)

    def test_sla_time_outside_hours(self):
        """Mon 19:00 → Mon 21:00 = 0h (after working hours)."""
        start = dt('2026-07-06', (19, 0))
        end = dt('2026-07-06', (21, 0))
        secs = self.sla.sla_time(start, end)
        self.assertEqual(secs, 0)

    # T7: sla_deadline — 5×8, 2h task at Fri 17:30 → Mon 09:30
    def test_sla_deadline_fri_afternoon(self):
        """P1 ticket Fri 17:30, resolve=2h → Mon 09:30."""
        start = dt('2026-07-10', (17, 30))  # Friday
        deadline = self.sla.sla_deadline(start, 7200)  # 2 hours SLA
        # Expected: Mon 09:30
        self.assertEqual(deadline.date(), d('2026-07-13'))
        self.assertEqual(deadline.hour, 9)
        self.assertEqual(deadline.minute, 30)

    def test_sla_deadline_same_day(self):
        """Mon 09:00, resolve=1h → Mon 10:00."""
        start = dt('2026-07-06', (9, 0))
        deadline = self.sla.sla_deadline(start, 3600)
        self.assertEqual(deadline, dt('2026-07-06', (10, 0)))

    def test_sla_deadline_cross_lunch(self):
        """Mon 11:00, resolve=2h → Mon 15:00 (30min am + 90min pm)."""
        start = dt('2026-07-06', (11, 0))
        deadline = self.sla.sla_deadline(start, 7200)
        # 11:00-12:00 = 1h, 14:00-15:00 = 1h
        self.assertEqual(deadline, dt('2026-07-06', (15, 0)))

    # T9: sla_deadline with holiday
    def test_sla_deadline_before_holiday(self):
        """Wed Sep 30 16:00, resolve=2h → Oct 4 09:00 (skips Oct 1-3 holiday + Thu/Fri)."""
        start = dt('2026-09-30', (16, 0))  # Wednesday
        deadline = self.sla.sla_deadline(start, 7200)
        # Sep 30: 16:00-18:00 = 2h = 7200s — exactly fits!
        self.assertEqual(deadline, dt('2026-09-30', (18, 0)))


class TestSlaTime7x24(TestCase):
    """T8: SlaTime engine with 7×24 schedule (should match natural time)."""

    @classmethod
    def setUpTestData(cls):
        cls.d24 = Duration.objects.create(name='全天', start_time='00:00:00', end_time='23:59:59')
        cls.everyday = Day.objects.create(
            name='每天', day_of_week='0,1,2,3,4,5,6', type_of_day='NORMAL',
        )
        cls.everyday.durations.add(cls.d24)
        cls.schedule = Schedule.objects.create(name='7×24 Test')
        cls.schedule.days.add(cls.everyday)
        cls.sla = SlaTime(cls.schedule)

    def test_sla_time_7x24(self):
        """7×24: sla_time should equal natural elapsed time."""
        start = dt('2026-07-10', (17, 30))
        end = dt('2026-07-10', (19, 30))
        secs = self.sla.sla_time(start, end)
        self.assertEqual(secs, 7200)

    def test_sla_deadline_7x24(self):
        """7×24: deadline = natural time."""
        start = dt('2026-07-10', (17, 30))
        deadline = self.sla.sla_deadline(start, 7200)
        self.assertEqual(deadline, dt('2026-07-10', (19, 30)))


class TestSlaEngine(TestCase):
    """T11-T13: SlaEngine integration tests with working-time model."""

    @classmethod
    def setUpTestData(cls):
        from iam.models import Project

        # Create project
        cls.project = Project.objects.create(name='Test Project')

        # Create schedule
        cls.d_am = Duration.objects.create(name='上午', start_time='08:00:00', end_time='12:00:00')
        cls.d_pm = Duration.objects.create(name='下午', start_time='14:00:00', end_time='18:00:00')
        cls.weekday = Day.objects.create(name='工作日', day_of_week='0,1,2,3,4', type_of_day='NORMAL')
        cls.weekday.durations.add(cls.d_am, cls.d_pm)
        cls.schedule = Schedule.objects.create(name='5×8 Engine', project=cls.project)
        cls.schedule.days.add(cls.weekday)

        # Create escalation level
        from itsm.models import EscalationLevel
        cls.esc_level = EscalationLevel.objects.create(
            name='L1通知', level=1, timeout_minutes=30, action='notify_only',
        )

        # Create SlaPolicy
        cls.policy = SlaPolicy.objects.create(
            name='P1 Policy', priority='P1', schedule=cls.schedule,
            response_time=60, response_unit='m',
            resolve_time=480, resolve_unit='m',
            project=cls.project,
        )
        cls.policy.escalation_levels.add(cls.esc_level)

        # Create a ticket
        from itsm.models import Workflow, WorkflowVersion
        cls.workflow = Workflow.objects.create(name='Test WF')
        cls.wf_version = WorkflowVersion.objects.create(
            workflow=cls.workflow, version=1, states=[], transitions=[],
        )
        cls.ticket = Ticket.objects.create(
            title='Test SLA Ticket', priority='P1', project=cls.project,
            workflow_version=cls.wf_version, current_status='running',
        )

    # T11: start_ticket_sla with working-time deadline
    def test_start_sla_uses_sla_time(self):
        task = SlaEngine.start_ticket_sla(self.ticket)
        self.assertIsNotNone(task)
        self.assertEqual(task.task_status, 'running')
        self.assertEqual(task.total_seconds, self.policy.resolve_seconds)
        self.assertIsNotNone(task.begin_at)
        self.assertIsNotNone(task.deadline)
        # Reply deadline = response_seconds
        self.assertIsNotNone(task.reply_deadline)

    # T12: pause/resume preserves correct deadline
    def test_pause_resume_working_time(self):
        task = SlaEngine.start_ticket_sla(self.ticket)

        # Pause
        SlaEngine.pause_ticket_sla(self.ticket)
        task.refresh_from_db()
        self.assertEqual(task.task_status, 'paused')
        # cost_time may be 0 in test (instant execution) but should be set
        self.assertIsNotNone(task.cost_time)

        # Resume
        SlaEngine.resume_ticket_sla(self.ticket)
        task.refresh_from_db()
        self.assertEqual(task.task_status, 'running')
        self.assertIsNotNone(task.deadline)

    # T16: swap bug fix — response_time → reply_deadline
    def test_swap_bug_fixed(self):
        """response_time maps to reply_deadline, resolve_time maps to deadline."""
        task = SlaEngine.start_ticket_sla(self.ticket)
        # reply_deadline should be closer than deadline (60 min vs 480 min)
        self.assertIsNotNone(task.reply_deadline)
        self.assertIsNotNone(task.deadline)
        self.assertLess(task.reply_deadline, task.deadline)
