# -*- coding: utf-8 -*-
"""Serializers for ITSM app — ServiceCategory, SlaPolicy with i18n support"""

from rest_framework import serializers
from common.utils.serializers import CustomModelSerializer
from common.utils.language import get_request_lang
from itsm.models import ServiceCategory, SlaPolicy


class ServiceCategorySerializer(CustomModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = get_request_lang(self.context.get('request'))
        if lang == 'en' and instance.name_en:
            data['name'] = instance.name_en
        return data


class ServiceCategoryCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"


class SlaPolicySerializer(CustomModelSerializer):
    escalation_level_ids = serializers.PrimaryKeyRelatedField(
        source='escalation_levels', many=True, queryset=SlaPolicy._meta.get_field('escalation_levels').remote_field.model.objects.all(),
        required=False, write_only=True,
    )

    class Meta:
        model = SlaPolicy
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = get_request_lang(self.context.get('request'))
        if lang == 'en' and instance.name_en:
            data['name'] = instance.name_en
        # Nest schedule name for display
        if instance.schedule_id:
            data['schedule_name'] = instance.schedule.display_name(lang)
        # Nest escalation levels
        data['escalation_levels'] = [
            {'id': e.id, 'name': e.name, 'name_en': e.name_en, 'level': e.level}
            for e in instance.escalation_levels.filter(is_active=True)
        ]
        return data

    def validate(self, attrs):
        # Application-level unique_together for priority+schedule+project
        # (nullable project cannot use DB constraint — NULL != NULL in SQL)
        priority = attrs.get('priority', self.instance.priority if self.instance else None)
        schedule = attrs.get('schedule', self.instance.schedule if self.instance else None)
        project = attrs.get('project', self.instance.project if self.instance else None)
        if priority and schedule:
            existing = SlaPolicy.objects.filter(priority=priority, schedule=schedule)
            if project:
                existing = existing.filter(project=project)
            else:
                existing = existing.filter(project__isnull=True)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError(
                    f"SlaPolicy with priority={priority}, schedule={schedule}"
                    f" already exists for this project scope."
                )
        return attrs
