# -*- coding: utf-8 -*-
"""Preset serializers — 预设序列化器"""

import json

from rest_framework import serializers

from common.utils.serializers import CustomModelSerializer
from itsm.models.preset import Preset


class PresetSerializer(CustomModelSerializer):
    """预设 CRUD 序列化器 — 更新时级联同步引用该预设的 State"""

    reference_count = serializers.SerializerMethodField()

    class Meta:
        model = Preset
        fields = '__all__'
        read_only_fields = ['creator', 'create_datetime', 'update_datetime', 'project']

    referenced_by = serializers.SerializerMethodField()

    def get_reference_count(self, obj):
        return len(self.get_referenced_by(obj))

    def get_referenced_by(self, obj):
        """Return list of {workflow_name, state_name, field_title} that reference this preset."""
        from itsm.models.state import State
        refs = []
        # FK refs: State.preset → Preset
        for s in State.objects.filter(preset_id=obj.id).select_related('workflow'):
            wf_name = getattr(s.workflow, 'name', '') or ''
            refs.append({
                'workflow_name': wf_name,
                'state_name': s.name or '',
                'field_title': '',
                'type': 'FK',
            })
        # JSON refs: State.fields contains {"itsmPresetId": <id>} or {"preset_id": <id>}
        try:
            from django.db.models import Q
            json_states = State.objects.filter(
                Q(fields__contains=[{'itsmPresetId': obj.id}])
                | Q(fields__contains=[{'preset_id': obj.id}])
            ).select_related('workflow')
            for s in json_states:
                wf_name = getattr(s.workflow, 'name', '') or ''
                for rule in (s.fields or []):
                    pid = rule.get('itsmPresetId') or rule.get('preset_id')
                    try:
                        pid = int(pid)
                    except (ValueError, TypeError):
                        continue
                    if pid == obj.id:
                        refs.append({
                            'workflow_name': wf_name,
                            'state_name': s.name or '',
                            'field_title': rule.get('title', '') or rule.get('field', ''),
                            'type': 'JSON',
                        })
        except Exception:
            pass
        return refs

    def update(self, instance, validated_data):
        old_value = instance.value
        old_type = instance.preset_type
        instance = super().update(instance, validated_data)

        new_value = validated_data.get('value', old_value)
        new_type = validated_data.get('preset_type', old_type)
        if old_value != new_value or old_type != new_type:
            self._sync_referencing_states(instance)
            if instance.preset_type == 'options':
                self._sync_referencing_state_fields(instance)
                self._sync_referencing_fields(instance)
        return instance

    @staticmethod
    def _sync_referencing_states(preset):
        """更新所有引用此预设的 State.processors — 使用 save() 触发 auto_now 和信号"""
        from itsm.models.state import State
        states = State.objects.filter(preset=preset)
        if not states:
            return

        expanded = PresetSerializer._expand_value(preset)
        count = 0
        for state in states:
            state.processors = expanded
            state.save(update_fields=['processors'])
            count += 1
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            'Preset "%s" updated, synced %d State(s)', preset.name, count
        )

    @staticmethod
    def _sync_referencing_fields(preset):
        """DEPRECATED: Update Field ORM records (legacy). Primary sync now via _sync_referencing_state_fields."""
        from itsm.models.field import Field
        fields = Field.objects.filter(preset=preset)
        if not fields:
            return
        count = 0
        for field in fields:
            field.choice = preset.value
            field.save(update_fields=['choice'])
            count += 1
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            'Preset "%s" updated, synced %d legacy Field(s)', preset.name, count
        )

    @staticmethod
    def _sync_referencing_state_fields(preset):
        """Sync preset changes into State.fields JSONField (Rule[] format).

        Scans both itsmPresetId (new form-create format) and preset_id (legacy format).
        Writes options into Rule.props.options per form-create convention.
        """
        from itsm.models.state import State
        from django.db.models import Q

        # Search for both new (itsmPresetId) and legacy (preset_id) format
        states = State.objects.filter(
            Q(fields__contains=[{'itsmPresetId': preset.id}])
            | Q(fields__contains=[{'preset_id': preset.id}])
        )
        if not states:
            return
        count = 0
        for state in states:
            updated = False
            for rule in (state.fields or []):
                pid = rule.get('itsmPresetId') or rule.get('preset_id')
                try:
                    pid = int(pid)
                except (ValueError, TypeError):
                    continue
                if pid == preset.id:
                    # Write options into form-create Rule format (top-level options)
                    rule['options'] = preset.value
                    updated = True
                    count += 1
            if updated:
                state.save(update_fields=['fields'])
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            'Preset "%s" updated, synced %d embedded rule(s)', preset.name, count
        )

    @staticmethod
    def _expand_value(preset):
        """将预设值展开为 State.processors 兼容的字符串格式"""
        val = preset.value
        if preset.preset_type == 'text':
            return str(val) if val is not None else ''
        return json.dumps(val, ensure_ascii=False) if val is not None else '[]'
