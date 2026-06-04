# -*- coding: utf-8 -*-
"""Admin registration for CMDB MySQL models"""

from django.contrib import admin

from .models.classification import Classification
from .models.model_definition import ModelDefinition, ModelField
from .models.attribute_group import AttributeGroup
from .models.association import AssociationType, ModelAssociation
from .models.object_unique import ObjectUnique
from .models.mainline_topo import MainlineTopo


@admin.register(Classification)
class ClassificationAdmin(admin.ModelAdmin):
    list_display = ['cls_id', 'name', 'sort_order']
    search_fields = ['cls_id', 'name']
    ordering = ['sort_order']


class ModelFieldInline(admin.TabularInline):
    model = ModelField
    extra = 0
    fields = ['name', 'label', 'field_type', 'required', 'sort_order']


@admin.register(ModelDefinition)
class ModelDefinitionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'classification', 'is_builtin', 'source']
    list_filter = ['is_builtin', 'source', 'classification']
    search_fields = ['code', 'name']
    inlines = [ModelFieldInline]


@admin.register(ModelField)
class ModelFieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'label', 'model_definition', 'field_type', 'required', 'sort_order']
    list_filter = ['field_type', 'required']
    search_fields = ['name', 'label']


@admin.register(AttributeGroup)
class AttributeGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_definition', 'sort_order']
    list_filter = ['model_definition']


@admin.register(AssociationType)
class AssociationTypeAdmin(admin.ModelAdmin):
    list_display = ['asst_id', 'name', 'direction']
    search_fields = ['asst_id', 'name']


@admin.register(ModelAssociation)
class ModelAssociationAdmin(admin.ModelAdmin):
    list_display = ['source_model', 'association_type', 'target_model', 'mapping']
    list_filter = ['association_type', 'mapping']


@admin.register(ObjectUnique)
class ObjectUniqueAdmin(admin.ModelAdmin):
    list_display = ['model_definition', 'keys']
    list_filter = ['model_definition']


@admin.register(MainlineTopo)
class MainlineTopoAdmin(admin.ModelAdmin):
    list_display = ['model_definition', 'parent_model', 'sort_order']
    list_filter = ['model_definition']
    ordering = ['sort_order']
