# -*- coding: utf-8 -*-
"""Serializers for MySQL schema models (CoreModel subclasses)

使用 dvadmin 统一的 CustomModelSerializer 基类。
"""

from dvadmin.utils.serializers import CustomModelSerializer

from ..models.classification import Classification
from ..models.model_definition import ModelDefinition, ModelField
from ..models.attribute_group import AttributeGroup
from ..models.association import AssociationType, ModelAssociation
from ..models.object_unique import ObjectUnique
from ..models.mainline_topo import MainlineTopo


# ─── Classification ───

class ClassificationSerializer(CustomModelSerializer):
    class Meta:
        model = Classification
        fields = '__all__'
        read_only_fields = ['id']


class ClassificationCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = Classification
        fields = '__all__'


# ─── ModelDefinition ───

class ModelDefinitionSerializer(CustomModelSerializer):
    class Meta:
        model = ModelDefinition
        fields = '__all__'
        read_only_fields = ['id']


class ModelDefinitionCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = ModelDefinition
        fields = '__all__'


# ─── ModelField ───

class ModelFieldSerializer(CustomModelSerializer):
    class Meta:
        model = ModelField
        fields = '__all__'
        read_only_fields = ['id']


class ModelFieldCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = ModelField
        fields = '__all__'


# ─── AttributeGroup ───

class AttributeGroupSerializer(CustomModelSerializer):
    class Meta:
        model = AttributeGroup
        fields = '__all__'
        read_only_fields = ['id']


# ─── AssociationType ───

class AssociationTypeSerializer(CustomModelSerializer):
    class Meta:
        model = AssociationType
        fields = '__all__'
        read_only_fields = ['id']


# ─── ModelAssociation ───

class ModelAssociationSerializer(CustomModelSerializer):
    class Meta:
        model = ModelAssociation
        fields = '__all__'
        read_only_fields = ['id']


# ─── ObjectUnique ───

class ObjectUniqueSerializer(CustomModelSerializer):
    class Meta:
        model = ObjectUnique
        fields = '__all__'
        read_only_fields = ['id']


# ─── MainlineTopo ───

class MainlineTopoSerializer(CustomModelSerializer):
    class Meta:
        model = MainlineTopo
        fields = '__all__'
        read_only_fields = ['id']
