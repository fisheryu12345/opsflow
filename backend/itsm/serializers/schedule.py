# -*- coding: utf-8 -*-
"""Serializers for Schedule, Day, Duration models."""

from rest_framework import serializers
from itsm.models import Duration, Day, Schedule
from common.utils.serializers import CustomModelSerializer


class DurationSerializer(CustomModelSerializer):
    class Meta:
        model = Duration
        fields = '__all__'


class DaySerializer(CustomModelSerializer):
    duration_ids = serializers.PrimaryKeyRelatedField(
        source='durations', many=True, queryset=Duration.objects.all(),
        required=False, write_only=True,
    )
    durations_detail = DurationSerializer(source='durations', many=True, read_only=True)

    class Meta:
        model = Day
        fields = '__all__'
        read_only_fields = ['create_datetime', 'update_datetime']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['durations'] = DurationSerializer(instance.durations.all(), many=True).data
        return data

    def validate(self, attrs):
        type_of_day = attrs.get('type_of_day', self.instance.type_of_day if self.instance else 'NORMAL')
        start_date = attrs.get('start_date', self.instance.start_date if self.instance else None)
        end_date = attrs.get('end_date', self.instance.end_date if self.instance else None)
        if type_of_day == 'NORMAL':
            if start_date or end_date:
                raise serializers.ValidationError(
                    "NORMAL type uses day_of_week; do not set start_date/end_date.")
        else:
            if not start_date or not end_date:
                raise serializers.ValidationError(
                    f"{type_of_day} type requires both start_date and end_date.")
        return attrs


class ScheduleSerializer(CustomModelSerializer):
    days_detail = DaySerializer(source='days', many=True, read_only=True)
    day_ids = serializers.PrimaryKeyRelatedField(
        source='days', many=True, queryset=Day.objects.all(),
        required=False, write_only=True,
    )
    workday_ids = serializers.PrimaryKeyRelatedField(
        source='workdays', many=True, queryset=Day.objects.all(),
        required=False, write_only=True,
    )
    holiday_ids = serializers.PrimaryKeyRelatedField(
        source='holidays', many=True, queryset=Day.objects.all(),
        required=False, write_only=True,
    )

    class Meta:
        model = Schedule
        fields = '__all__'
        read_only_fields = ['create_datetime', 'update_datetime', 'is_builtin']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['days'] = DaySerializer(instance.days.all(), many=True).data
        data['workdays'] = DaySerializer(instance.workdays.all(), many=True).data
        data['holidays'] = DaySerializer(instance.holidays.all(), many=True).data
        return data

    def create(self, validated_data):
        days = validated_data.pop('days', [])
        workdays = validated_data.pop('workdays', [])
        holidays = validated_data.pop('holidays', [])
        schedule = Schedule.objects.create(**validated_data)
        if days:
            schedule.days.set(days)
        if workdays:
            schedule.workdays.set(workdays)
        if holidays:
            schedule.holidays.set(holidays)
        return schedule

    def update(self, instance, validated_data):
        days = validated_data.pop('days', None)
        workdays = validated_data.pop('workdays', None)
        holidays = validated_data.pop('holidays', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if days is not None:
            instance.days.set(days)
        if workdays is not None:
            instance.workdays.set(workdays)
        if holidays is not None:
            instance.holidays.set(holidays)
        return instance
