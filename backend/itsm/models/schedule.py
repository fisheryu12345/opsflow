# -*- coding: utf-8 -*-
"""SLA Working Time Model — Schedule, Day, Duration

BK-ITSM parity: Schedule → Day → Duration hierarchy for working-time-aware SLA.
"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class Duration(CoreModel):
    """Working time segment within a single day, e.g. "Morning 08:00-12:00"."""
    name = models.CharField(max_length=128, verbose_name="时段名称")
    name_en = models.CharField(max_length=128, blank=True, default='', verbose_name="时段名称(英文)")
    start_time = models.TimeField(verbose_name="开始时间")
    end_time = models.TimeField(verbose_name="结束时间")

    class Meta:
        db_table = table_prefix + "itsm_sla_duration"
        verbose_name = "工作时间段"
        verbose_name_plural = verbose_name
        ordering = ['start_time']

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"

    def display_name(self, lang='zh'):
        return self.name_en if lang == 'en' and self.name_en else self.name


class Day(CoreModel):
    """Day classification: NORMAL (recurring weekday), WORKDAY (overtime range), HOLIDAY (exclusion range)."""
    DAY_TYPE_CHOICES = (
        ('NORMAL', '工作日'),
        ('WORKDAY', '加班日'),
        ('HOLIDAY', '节假日'),
    )

    name = models.CharField(max_length=128, verbose_name="日期名称")
    name_en = models.CharField(max_length=128, blank=True, default='', verbose_name="日期名称(英文)")
    day_of_week = models.CharField(
        max_length=32, default='-1', verbose_name="周几",
        help_text="Comma-separated weekday indices: 0=Mon,1=Tue,2=Wed,3=Thu,4=Fri,5=Sat,6=Sun. Used for NORMAL type.",
    )
    type_of_day = models.CharField(
        max_length=16, choices=DAY_TYPE_CHOICES, default='NORMAL', verbose_name="日期类型",
    )
    start_date = models.DateField(null=True, blank=True, verbose_name="开始日期",
                                   help_text="Date range start for WORKDAY/HOLIDAY types.")
    end_date = models.DateField(null=True, blank=True, verbose_name="结束日期",
                                 help_text="Date range end for WORKDAY/HOLIDAY types.")
    durations = models.ManyToManyField(Duration, blank=True, verbose_name="工作时间段")

    class Meta:
        db_table = table_prefix + "itsm_sla_day"
        verbose_name = "日期定义"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name} [{self.get_type_of_day_display()}]"

    def display_name(self, lang='zh'):
        return self.name_en if lang == 'en' and self.name_en else self.name

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.type_of_day == 'NORMAL':
            if self.start_date or self.end_date:
                raise ValidationError("NORMAL type should not have start_date/end_date; use day_of_week instead.")
        else:
            if not self.start_date or not self.end_date:
                raise ValidationError(f"{self.type_of_day} type requires both start_date and end_date.")


class Schedule(CoreModel):
    """Working schedule aggregating NORMAL days, WORKDAY overtime days, and HOLIDAY exclusions."""
    name = models.CharField(max_length=128, verbose_name="排班名称")
    name_en = models.CharField(max_length=128, blank=True, default='', verbose_name="排班名称(英文)")
    project = models.ForeignKey(
        'iam.Project', on_delete=models.CASCADE, null=True, blank=True,
        related_name='sla_schedules', verbose_name='Project',
    )
    is_builtin = models.BooleanField(default=False, verbose_name="内置排班",
                                      help_text="Built-in schedules cannot be deleted.")
    days = models.ManyToManyField(Day, blank=True, related_name='schedule_days',
                                   verbose_name="常规工作日",
                                   help_text="NORMAL type days (recurring weekdays).")
    workdays = models.ManyToManyField(Day, blank=True, related_name='schedule_workdays',
                                       verbose_name="加班日",
                                       help_text="WORKDAY type days (overtime date ranges).")
    holidays = models.ManyToManyField(Day, blank=True, related_name='schedule_holidays',
                                       verbose_name="节假日",
                                       help_text="HOLIDAY type days (holiday date ranges).")

    class Meta:
        db_table = table_prefix + "itsm_sla_schedule"
        verbose_name = "排班表"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name}{' (内置)' if self.is_builtin else ''}"

    def display_name(self, lang='zh'):
        return self.name_en if lang == 'en' and self.name_en else self.name

    @classmethod
    def seed_builtin_schedules(cls):
        """Create built-in 5x8 and 7x24 schedules. Idempotent — skips if already exist."""
        # 7×24 schedule
        d24, _ = Duration.objects.get_or_create(
            name='全天', name_en='All Day',
            defaults={'start_time': '00:00:00', 'end_time': '23:59:59'},
        )
        day_7, _ = Day.objects.get_or_create(
            name='每天', name_en='Every Day',
            defaults={'day_of_week': '0,1,2,3,4,5,6', 'type_of_day': 'NORMAL'},
        )
        day_7.durations.add(d24)
        sched_7x24, created = Schedule.objects.get_or_create(
            name='7×24', name_en='7×24',
            defaults={'is_builtin': True},
        )
        sched_7x24.days.add(day_7)

        # 5×8 schedule
        d_am, _ = Duration.objects.get_or_create(
            name='上午', name_en='Morning',
            defaults={'start_time': '08:00:00', 'end_time': '12:00:00'},
        )
        d_pm, _ = Duration.objects.get_or_create(
            name='下午', name_en='Afternoon',
            defaults={'start_time': '14:00:00', 'end_time': '18:00:00'},
        )
        day_weekday, _ = Day.objects.get_or_create(
            name='工作日', name_en='Weekday',
            defaults={'day_of_week': '0,1,2,3,4', 'type_of_day': 'NORMAL'},
        )
        day_weekday.durations.add(d_am, d_pm)
        sched_5x8, created = Schedule.objects.get_or_create(
            name='5×8 标准', name_en='5×8 Standard',
            defaults={'is_builtin': True},
        )
        sched_5x8.days.add(day_weekday)

    def clean(self):
        from django.core.exceptions import ValidationError
        normal_days = self.days.filter(type_of_day='NORMAL')
        if not normal_days.exists():
            raise ValidationError("Schedule must have at least one NORMAL day.")
        has_duration = any(d.durations.exists() for d in normal_days)
        if not has_duration:
            raise ValidationError("At least one NORMAL day must have Duration segments.")
