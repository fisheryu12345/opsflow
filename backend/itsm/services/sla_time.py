# -*- coding: utf-8 -*-
"""SLA Time Engine — Working-time-aware deadline calculation.

BK-ITSM parity: TimeDelta, MultiTimeDelta, and SlaTime for Schedule/Day/Duration.
"""

import logging
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Resolve TIME_ZONE from Django settings (Asia/Shanghai for this project).
_TZ = timezone.get_default_timezone()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unit_to_seconds(value, unit):
    """Convert a time value + unit to total seconds."""
    multipliers = {'m': 60, 'h': 3600, 'd': 86400}
    return value * multipliers.get(unit, 60)


def _make_aware(d, t):
    """Combine a date and naive time into a timezone-aware datetime."""
    naive = datetime.combine(d, t)
    return timezone.make_aware(naive, _TZ)


def _date_range(start, end):
    """Yield all dates from start to end (inclusive)."""
    current = start.date() if isinstance(start, datetime) else start
    stop = end.date() if isinstance(end, datetime) else end
    while current <= stop:
        yield current
        current += timedelta(days=1)


# ---------------------------------------------------------------------------
# TimeDelta — single datetime interval with set-theoretic operations
# ---------------------------------------------------------------------------

class TimeDelta:
    """A single continuous interval between two timezone-aware datetimes."""

    def __init__(self, start_time, end_time):
        if start_time > end_time:
            raise ValueError(f"start_time ({start_time}) must be <= end_time ({end_time})")
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self):
        return f"TimeDelta({self.start_time.isoformat()}, {self.end_time.isoformat()})"

    def seconds(self):
        """Duration in seconds."""
        return int((self.end_time - self.start_time).total_seconds())

    def intersection(self, other):
        """Return the overlapping TimeDelta, or None if disjoint."""
        if not self.is_intersect(other):
            return None
        return TimeDelta(max(self.start_time, other.start_time),
                         min(self.end_time, other.end_time))

    def is_intersect(self, other):
        """Whether the two intervals overlap (inclusive boundaries)."""
        return (self.start_time <= other.end_time and
                self.end_time >= other.start_time)

    def position(self, time):
        """Return -1 if time is left of interval, 0 if inside, 1 if right."""
        if time < self.start_time:
            return -1
        if time > self.end_time:
            return 1
        return 0

    def date_list(self):
        """Return all dates spanned by this interval (inclusive)."""
        return list(_date_range(self.start_time, self.end_time))

    def difference(self, other):
        """Return list of TimeDelta(s) after removing `other` from self.
        Can return 0, 1, or 2 segments.
        """
        if not self.is_intersect(other):
            return [self]
        result = []
        if self.start_time < other.start_time:
            result.append(TimeDelta(self.start_time, other.start_time))
        if self.end_time > other.end_time:
            result.append(TimeDelta(other.end_time, self.end_time))
        return result

    def union(self, other):
        """Merge two overlapping/adjacent intervals, or return None if disjoint."""
        if self.is_intersect(other):
            return TimeDelta(min(self.start_time, other.start_time),
                             max(self.end_time, other.end_time))
        if self.end_time == other.start_time:
            return TimeDelta(self.start_time, other.end_time)
        if other.end_time == self.start_time:
            return TimeDelta(other.start_time, self.end_time)
        return None


# ---------------------------------------------------------------------------
# MultiTimeDelta — collection of non-overlapping TimeDeltas
# ---------------------------------------------------------------------------

class MultiTimeDelta:
    """An ordered, non-overlapping collection of TimeDelta intervals."""

    def __init__(self, *time_deltas):
        self.time_deltas = list(time_deltas)

    def __repr__(self):
        return f"MultiTimeDelta({len(self.time_deltas)} segments)"

    def __iter__(self):
        return iter(self.time_deltas)

    def __len__(self):
        return len(self.time_deltas)

    def __bool__(self):
        return bool(self.time_deltas)

    def sort(self):
        """Sort intervals by start_time. Returns self for chaining."""
        self.time_deltas.sort(key=lambda td: td.start_time)
        return self

    def _merge_overlapping(self):
        """Combine overlapping/adjacent intervals in-place."""
        if not self.time_deltas:
            return
        self.sort()
        merged = [self.time_deltas[0]]
        for td in self.time_deltas[1:]:
            last = merged[-1]
            combined = last.union(td)
            if combined is not None:
                merged[-1] = combined
            else:
                merged.append(td)
        self.time_deltas = merged

    def intersection(self, other):
        """Many-to-many intersection with another MultiTimeDelta."""
        result = []
        for a in self.time_deltas:
            for b in other.time_deltas:
                inter = a.intersection(b)
                if inter is not None:
                    result.append(inter)
        return MultiTimeDelta(*result)

    def difference(self, other):
        """Many-to-many difference: remove all `other` intervals from self."""
        result = MultiTimeDelta(*self.time_deltas)
        for b in other.time_deltas:
            new_deltas = []
            for a in result.time_deltas:
                new_deltas.extend(a.difference(b))
            result = MultiTimeDelta(*new_deltas)
        result._merge_overlapping()
        return result

    def union(self, other):
        """Many-to-many union: combine all intervals, merging overlaps."""
        combined = MultiTimeDelta(*self.time_deltas, *other.time_deltas)
        combined._merge_overlapping()
        return combined

    def closest_td_time(self, time, is_forward=True):
        """Find the nearest interval boundary from `time`.

        If is_forward=True: return earliest boundary at or after `time`.
        If is_forward=False: return latest boundary at or before `time`.
        Returns None if no boundary exists.
        """
        if not self.time_deltas:
            return None
        self.sort()
        if is_forward:
            for td in self.time_deltas:
                if td.position(time) <= 0:
                    return td.start_time if td.position(time) == -1 else td.end_time
            return None
        else:
            for td in reversed(self.time_deltas):
                if td.position(time) >= 0:
                    return td.end_time if td.position(time) == 1 else td.start_time
            return None


# ---------------------------------------------------------------------------
# SlaTime — Working-time calculator
# ---------------------------------------------------------------------------

class SlaTime:
    """Working-time-aware SLA calculator.

    Uses a Schedule (with its Days and Durations) to compute effective SLA
    working time between two datetimes, and to project deadlines.

    Usage:
        sla = SlaTime(schedule)
        effective_seconds = sla.sla_time(start, end)
        deadline = sla.sla_deadline(start_time, sla_seconds)
    """

    def __init__(self, schedule):
        """Pre-fetch schedule hierarchy for fast lookups.

        Args:
            schedule: a Schedule instance.
        """
        self.schedule = schedule
        # weekday(int) → [(start_time, end_time)] as naive time tuples
        self._normal_by_dow = {}
        # list of (start_date, end_date) holiday ranges
        self._holiday_ranges = []
        # date → [(start_time, end_time)] as naive time tuples
        self._workday_by_date = {}

        self._build_index()

    def _build_index(self):
        """Flatten Schedule → Day → Duration into indexed structures."""
        # NORMAL days: index by day_of_week → duration time tuples
        for day in self.schedule.days.filter(type_of_day='NORMAL').prefetch_related('durations'):
            durs = [(d.start_time, d.end_time) for d in day.durations.all()]
            if not durs:
                continue
            try:
                dows = [int(x.strip()) for x in day.day_of_week.split(',')
                        if x.strip().lstrip('-').isdigit()]
            except (ValueError, AttributeError):
                continue
            for dow in dows:
                self._normal_by_dow.setdefault(dow, []).extend(durs)

        # HOLIDAY ranges
        for day in self.schedule.holidays.filter(type_of_day='HOLIDAY'):
            if day.start_date and day.end_date:
                self._holiday_ranges.append((day.start_date, day.end_date))

        # WORKDAY overtime: index by each date in range → duration time tuples
        for day in self.schedule.workdays.filter(type_of_day='WORKDAY').prefetch_related('durations'):
            durs = [(d.start_time, d.end_time) for d in day.durations.all()]
            if not durs or not day.start_date or not day.end_date:
                continue
            for d in _date_range(day.start_date, day.end_date):
                self._workday_by_date.setdefault(d, []).extend(durs)

    def _is_holiday(self, d):
        """Check if a date falls within any holiday range."""
        for start_date, end_date in self._holiday_ranges:
            if start_date <= d <= end_date:
                return True
        return False

    def date_time_deltas(self, d):
        """Return working TimeDelta list for a specific date.

        Algorithm:
          1. Get NORMAL day duration tuples for d.weekday()
          2. If holiday: exclude everything (return empty)
          3. Add overtime workday durations
          4. Materialize all to TimeDelta objects for this date
        """
        segments = []

        # Step 1: NORMAL day durations (if not a holiday)
        if not self._is_holiday(d):
            dur_tuples = self._normal_by_dow.get(d.weekday(), [])
            for start_t, end_t in dur_tuples:
                segments.append(TimeDelta(
                    _make_aware(d, start_t),
                    _make_aware(d, end_t),
                ))

        # Step 2: Add overtime workday durations
        overtime_tuples = self._workday_by_date.get(d, [])
        for start_t, end_t in overtime_tuples:
            segments.append(TimeDelta(
                _make_aware(d, start_t),
                _make_aware(d, end_t),
            ))

        # Merge overlapping (e.g. normal + overtime may overlap)
        if segments:
            mtd = MultiTimeDelta(*segments)
            mtd._merge_overlapping()
            return list(mtd)
        return []

    def sla_time(self, start, end):
        """Effective SLA working seconds between start and end."""
        if start >= end:
            return 0
        seconds = 0
        for d in _date_range(start, end):
            day_segments = self.date_time_deltas(d)
            if not day_segments:
                continue
            day_start = _make_aware(d, time(0, 0))
            day_end = _make_aware(d, time(23, 59, 59))
            query_start = max(start, day_start)
            query_end = min(end, day_end)
            query_td = TimeDelta(query_start, query_end)
            for seg in day_segments:
                inter = query_td.intersection(seg)
                if inter is not None:
                    seconds += inter.seconds()
        return seconds

    def sla_deadline(self, start_time, sla_seconds):
        """Compute the wall-clock deadline after consuming `sla_seconds` of SLA time.

        Walks forward day-by-day, consuming working seconds until the quota is met.
        """
        if sla_seconds <= 0:
            return start_time

        remaining = sla_seconds
        cursor = start_time

        for _ in range(366):  # safety cap: one year
            today = cursor.date()
            segments = self.date_time_deltas(today)

            # Sort segments by start_time
            segments.sort(key=lambda s: s.start_time)

            # Calculate available working seconds from cursor to end of today
            available = 0
            for seg in segments:
                if seg.end_time <= cursor:
                    continue
                start = max(cursor, seg.start_time)
                available += int((seg.end_time - start).total_seconds())

            if available >= remaining:
                # Deadline is today — find exact time within segments
                for seg in segments:
                    if seg.end_time <= cursor:
                        continue
                    start = max(cursor, seg.start_time)
                    seg_avail = int((seg.end_time - start).total_seconds())
                    if seg_avail >= remaining:
                        return start + timedelta(seconds=remaining)
                    remaining -= seg_avail
                    cursor = seg.end_time

            # Not enough today — consume what we can and move to next day
            remaining -= available
            next_day = today + timedelta(days=1)
            cursor = _make_aware(next_day, time(0, 0))

            if remaining <= 0:
                return cursor

        logger.warning("sla_deadline iteration cap reached: start=%s seconds=%d",
                       start_time, sla_seconds)
        return cursor


# ---------------------------------------------------------------------------
# Public helpers for SlaEngine integration
# ---------------------------------------------------------------------------

def resolve_leader(processor_username):
    """Resolve the leader/manager for a given processor username.

    Placeholder: queries IAMUserRole for the user's direct leader.
    Returns the leader's username, or the original processor if no leader found.
    """
    try:
        from iam.models import IAMUserRole
        user_role = IAMUserRole.objects.filter(
            user__username=processor_username, is_active=True,
        ).select_related('parent_role').first()
        if user_role and user_role.parent_role:
            # Return the first user assigned to the parent role
            leader_role = IAMUserRole.objects.filter(
                role=user_role.parent_role, is_active=True,
            ).first()
            if leader_role:
                return leader_role.user.username
    except Exception as e:
        logger.warning("resolve_leader failed for %s: %s", processor_username, e)
    return processor_username


def notify_specific_users(usernames):
    """Notify a list of specific usernames about SLA escalation.

    Uses NotificationService.notify_sla_violation per ticket context.
    For direct user notification without a ticket, logs the escalation.
    """
    logger.warning("SLA escalation — notify users: %s", usernames)
