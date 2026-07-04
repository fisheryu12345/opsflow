"""CoreModel base class — all models inherit from this"""

from importlib import import_module

from django.apps import apps
from django.db import models
from django.conf import settings

from application import settings

table_prefix = settings.TABLE_PREFIX  # 数据库表名前缀


class CoreModel(models.Model):
    """
    核心标准抽象模型模型,可直接继承使用
    增加审计字段, 覆盖字段时, 字段名称请勿修改, 必须统一审计字段名称
    """
    id = models.BigAutoField(primary_key=True, help_text="Id", verbose_name="Id")
    description = models.CharField(max_length=255, verbose_name="描述", null=True, blank=True, help_text="描述")
    creator = models.IntegerField(null=True, blank=True, verbose_name='创建人', help_text="创建人", db_column='creator_id')
    modifier = models.CharField(max_length=255, null=True, blank=True, help_text="修改人", verbose_name="修改人")
    dept_belong_id = models.CharField(max_length=255, help_text="数据归属部门", null=True, blank=True,
                                      verbose_name="数据归属部门")
    update_datetime = models.DateTimeField(auto_now=True, null=True, blank=True, help_text="修改时间",
                                           verbose_name="修改时间")
    create_datetime = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="创建时间",
                                           verbose_name="创建时间")

    class Meta:
        abstract = True
        verbose_name = '核心模型'
        verbose_name_plural = verbose_name


def get_all_models_objects(model_name=None):
    """
    获取所有 models 对象
    :return: {}
    """
    settings.ALL_MODELS_OBJECTS = {}
    if not settings.ALL_MODELS_OBJECTS:
        all_models = apps.get_models()
        for item in list(all_models):
            table = {
                "tableName": item._meta.verbose_name,
                "table": item.__name__,
                "tableFields": []
            }
            for field in item._meta.fields:
                fields = {
                    "title": field.verbose_name,
                    "field": field.name
                }
                table['tableFields'].append(fields)
            settings.ALL_MODELS_OBJECTS.setdefault(item.__name__, {"table": table, "object": item})
    if model_name:
        return settings.ALL_MODELS_OBJECTS[model_name] or {}
    return settings.ALL_MODELS_OBJECTS or {}


def get_model_from_app(app_name):
    """获取模型里的字段"""
    model_module = import_module(app_name + '.models')
    filter_model = [
        getattr(model_module, item) for item in dir(model_module)
        if item != 'CoreModel' and issubclass(getattr(model_module, item).__class__, models.base.ModelBase)
    ]
    model_list = []
    for model in filter_model:
        if model.__name__ == 'AbstractUser':
            continue
        fields = [
            {'title': field.verbose_name, 'name': field.name, 'object': field}
            for field in model._meta.fields
        ]
        model_list.append({
            'app': app_name,
            'verbose': model._meta.verbose_name,
            'model': model.__name__,
            'object': model,
            'fields': fields
        })
    return model_list


def get_custom_app_models(app_name=None):
    """
    获取所有项目下的app里的models
    """
    if app_name:
        return get_model_from_app(app_name)
    all_apps = apps.get_app_configs()
    res = []
    for app in all_apps:
        if app.name.startswith('django'):
            continue
        if app.name in settings.COLUMN_EXCLUDE_APPS:
            continue
        try:
            all_models = get_model_from_app(app.name)
            if all_models:
                for model in all_models:
                    res.append(model)
        except Exception as e:
            pass
    return res
