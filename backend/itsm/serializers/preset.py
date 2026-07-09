# -*- coding: utf-8 -*-
"""Preset serializers — 预设序列化器"""

import json

from rest_framework import serializers

from common.utils.serializers import CustomModelSerializer
from itsm.models.preset import Preset


class PresetSerializer(CustomModelSerializer):
    """预设 CRUD 序列化器 — 更新时级联同步引用该预设的 State"""

    class Meta:
        model = Preset
        fields = '__all__'
        read_only_fields = ['creator', 'create_datetime', 'update_datetime', 'project']

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
        """更新所有引用此预设的 Field 模型记录（options 类型）"""
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
            'Preset "%s" updated, synced %d Field(s)', preset.name, count
        )

    @staticmethod
    def _sync_referencing_state_fields(preset):
        """更新 State.fields JSON 中引用此预设的内嵌字段"""
        from itsm.models.state import State
        states = State.objects.filter(fields__contains=[{"preset_id": preset.id}])
        if not states:
            return
        count = 0
        for state in states:
            updated = False
            for f in state.fields:
                if f.get('preset_id') == preset.id:
                    f['choice'] = preset.value
                    updated = True
                    count += 1
            if updated:
                state.save(update_fields=['fields'])
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            'Preset "%s" updated, synced %d embedded field(s)', preset.name, count
        )

    @staticmethod
    def _expand_value(preset):
        """将预设值展开为 State.processors 兼容的字符串格式"""
        val = preset.value
        if preset.preset_type == 'text':
            return str(val) if val is not None else ''
        return json.dumps(val, ensure_ascii=False) if val is not None else '[]'
