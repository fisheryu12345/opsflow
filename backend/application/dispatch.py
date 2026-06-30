#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import connection


def is_tenants_mode():
    """
    判断是否为租户模式
    :return:
    """
    return hasattr(connection, "tenant") and connection.tenant.schema_name


# ================================================= #
# ******************** 初始化 ******************** #
# ================================================= #
def _get_all_system_config():
    data = {}
    from dvadmin.system.models import SystemConfig

    system_config_obj = (
        SystemConfig.objects.filter(parent_id__isnull=False)
        .values("parent__key", "key", "value", "form_item_type")
        .order_by("sort")
    )
    for system_config in system_config_obj:
        value = system_config.get("value", "")
        if value and system_config.get("form_item_type") == 7:
            value = value[0].get("url")
        if value and system_config.get("form_item_type") == 11:
            new_value = []
            for ele in value:
                new_value.append({
                    "key": ele.get('key'),
                    "title": ele.get('title'),
                    "value": ele.get('value'),
                })
            new_value.sort(key=lambda s: s["key"])
            value = new_value
        data[f"{system_config.get('parent__key')}.{system_config.get('key')}"] = value
    return data


def init_dictionary():
    """
    初始化字典配置
    :return:
    """
    settings.DICTIONARY_CONFIG = {}
    return


def init_system_config():
    """
    初始化系统配置
    :param name:
    :return:
    """
    try:

        if is_tenants_mode():
            from django_tenants.utils import tenant_context, get_tenant_model

            for tenant in get_tenant_model().objects.filter():
                with tenant_context(tenant):
                    settings.SYSTEM_CONFIG[connection.tenant.schema_name] = _get_all_system_config()
        else:
            settings.SYSTEM_CONFIG = _get_all_system_config()
    except Exception as e:
        print("请先进行数据库迁移!")
    return


def refresh_dictionary():
    settings.DICTIONARY_CONFIG = {}


def refresh_system_config():
    """
    刷新系统配置
    :return:
    """
    if is_tenants_mode():
        from django_tenants.utils import tenant_context, get_tenant_model

        for tenant in get_tenant_model().objects.filter():
            with tenant_context(tenant):
                settings.SYSTEM_CONFIG[connection.tenant.schema_name] = _get_all_system_config()
    else:
        settings.SYSTEM_CONFIG = _get_all_system_config()


# ================================================= #
# ******************** 字典管理 ******************** #
# ================================================= #
def get_dictionary_config(schema_name=None):
    """
    获取字典所有配置
    :param schema_name: 对应字典配置的租户schema_name值
    :return:
    """
    if not settings.DICTIONARY_CONFIG:
        refresh_dictionary()
    if is_tenants_mode():
        dictionary_config = settings.DICTIONARY_CONFIG[schema_name or connection.tenant.schema_name]
    else:
        dictionary_config = settings.DICTIONARY_CONFIG
    return dictionary_config or {}


def get_dictionary_values(key, schema_name=None):
    """
    获取字典数据数组
    :param key: 对应字典配置的key值(字典编号)
    :param schema_name: 对应字典配置的租户schema_name值
    :return:
    """
    dictionary_config = get_dictionary_config(schema_name)
    return dictionary_config.get(key)


def get_dictionary_label(key, name, schema_name=None):
    """
    获取获取字典label值
    :param key: 字典管理中的key值(字典编号)
    :param name: 对应字典配置的value值
    :param schema_name: 对应字典配置的租户schema_name值
    :return:
    """
    children = get_dictionary_values(key, schema_name) or []
    for ele in children:
        if ele.get("value") == str(name):
            return ele.get("label")
    return ""


# ================================================= #
# ******************** 系统配置 ******************** #
# ================================================= #
def get_system_config(schema_name=None):
    """
    获取系统配置中所有配置
    1.只传父级的key，返回全部子级，{ "父级key.子级key" : "值" }
    2."父级key.子级key"，返回子级值
    :param schema_name: 对应字典配置的租户schema_name值
    :return:
    """
    if not settings.SYSTEM_CONFIG:
        refresh_system_config()
    if is_tenants_mode():
        dictionary_config = settings.SYSTEM_CONFIG[schema_name or connection.tenant.schema_name]
    else:
        dictionary_config = settings.SYSTEM_CONFIG
    return dictionary_config or {}


def get_system_config_values(key, schema_name=None):
    """
    获取系统配置数据数组
    :param key: 对应系统配置的key值(字典编号)
    :param schema_name: 对应系统配置的租户schema_name值
    :return:
    """
    system_config = get_system_config(schema_name)
    return system_config.get(key)


def get_system_config_label(key, name, schema_name=None):
    """
    获取获取系统配置label值
    :param key: 系统配置中的key值(字典编号)
    :param name: 对应系统配置的value值
    :param schema_name: 对应系统配置的租户schema_name值
    :return:
    """
    children = get_system_config_values(key, schema_name) or []
    for ele in children:
        if ele.get("value") == str(name):
            return ele.get("label")
    return ""
