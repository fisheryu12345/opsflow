# -*- coding: utf-8 -*-
"""Serializers for Trigger & TriggerAction with i18n support"""

from django.db import transaction
from rest_framework import serializers
from common.utils.serializers import CustomModelSerializer
from common.utils.language import get_request_lang
from itsm.models import Trigger, TriggerAction


class TriggerActionSerializer(CustomModelSerializer):
    class Meta:
        model = TriggerAction
        fields = ['id', 'action_type', 'config', 'trigger', 'order']
        read_only_fields = ['trigger', 'order']


class TriggerSerializer(CustomModelSerializer):
    actions = TriggerActionSerializer(many=True, required=False)
    state_ids = serializers.PrimaryKeyRelatedField(
        source='states', many=True,
        queryset=Trigger._meta.get_field('states').remote_field.model.objects.all(),
        required=False, write_only=True,
    )

    class Meta:
        model = Trigger
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = get_request_lang(self.context.get('request'))
        if lang == 'en' and instance.name_en:
            data['name'] = instance.name_en
        if instance.workflow_id:
            data['workflow_name'] = getattr(instance.workflow, 'name', str(instance.workflow))
        # Nest states for display
        data['states'] = [
            {'id': s.id, 'name': s.name, 'type': s.type, 'node_key': s.node_key}
            for s in instance.states.all()
        ]
        # Nest actions for display (read path; write uses nested serializer)
        data['actions'] = TriggerActionSerializer(instance.actions.all(), many=True).data
        return data

    @transaction.atomic
    def create(self, validated_data):
        actions_data = validated_data.pop('actions', [])
        states = validated_data.pop('states', [])
        trigger = Trigger.objects.create(**validated_data)
        trigger.states.set(states)
        for i, action_data in enumerate(actions_data):
            action_data.pop('id', None)  # strip client-supplied IDs
            TriggerAction.objects.create(trigger=trigger, order=i, **action_data)
        return trigger

    @transaction.atomic
    def update(self, instance, validated_data):
        actions_data = validated_data.pop('actions', None)
        states = validated_data.pop('states', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if states is not None:
            instance.states.set(states)
        if actions_data is not None:
            # Diff by action id: update existing, delete removed, create new
            existing_ids = set(instance.actions.values_list('id', flat=True))
            submitted_ids = set()
            for i, action_data in enumerate(actions_data):
                action_data.pop('trigger', None)  # read_only
                aid = action_data.pop('id', None)
                action_data['order'] = i
                if aid and aid in existing_ids:
                    TriggerAction.objects.filter(id=aid).update(**action_data)
                    submitted_ids.add(aid)
                else:
                    TriggerAction.objects.create(trigger=instance, **action_data)
                    if aid:
                        submitted_ids.add(aid)
            # Delete actions removed by the client
            to_delete = existing_ids - submitted_ids
            if to_delete:
                instance.actions.filter(id__in=to_delete).delete()
        return instance
