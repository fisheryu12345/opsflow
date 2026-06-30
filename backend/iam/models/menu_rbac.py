# -*- coding: utf-8 -*-
"""IAM RBAC models — Role / Menu / MenuButton / Permission bridges.

Migrated from dvadmin.system.models. IAM is the single source of truth for
all RBAC models. New tables use `iam_*` prefix; data migration copies from
the old `system_*` tables.
"""
from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


class Role(CoreModel):
    """角色 (was dvadmin.system.models.Role)"""
    name = models.CharField(max_length=64, verbose_name="角色名称")
    key = models.CharField(max_length=64, unique=True, verbose_name="权限字符")
    sort = models.IntegerField(default=1, verbose_name="角色顺序")
    status = models.BooleanField(default=True, verbose_name="角色状态")

    class Meta:
        db_table = table_prefix + "system_role"  # matches old table (will rename to iam_role later)
        verbose_name = "角色"
        verbose_name_plural = verbose_name
        ordering = ("sort",)

    def __str__(self):
        return self.name


class Menu(CoreModel):
    """菜单 — hierarchical navigation (was dvadmin.system.models.Menu)"""
    parent = models.ForeignKey(
        to="self", on_delete=models.CASCADE, verbose_name="上级菜单",
        null=True, blank=True, db_constraint=False,
    )
    icon = models.CharField(max_length=64, verbose_name="菜单图标", null=True, blank=True)
    name = models.CharField(max_length=64, verbose_name="菜单名称")
    name_en = models.CharField(max_length=128, verbose_name="菜单名称(英文)", null=True, blank=True)
    sort = models.IntegerField(default=1, verbose_name="显示排序", null=True, blank=True)
    is_link = models.BooleanField(default=False, verbose_name="是否外链")
    link_url = models.CharField(max_length=255, verbose_name="链接地址", null=True, blank=True)
    is_catalog = models.BooleanField(default=False, verbose_name="是否目录")
    web_path = models.CharField(max_length=128, verbose_name="路由地址", null=True, blank=True)
    component = models.CharField(max_length=128, verbose_name="组件地址", null=True, blank=True)
    component_name = models.CharField(max_length=50, verbose_name="组件名称", null=True, blank=True)
    status = models.BooleanField(default=True, blank=True, verbose_name="菜单状态")
    cache = models.BooleanField(default=False, blank=True, verbose_name="是否页面缓存")
    visible = models.BooleanField(default=True, blank=True, verbose_name="侧边栏中是否显示")
    is_iframe = models.BooleanField(default=False, blank=True, verbose_name="框架外显示")
    is_affix = models.BooleanField(default=False, blank=True, verbose_name="是否固定")

    @classmethod
    def get_all_parent(cls, id, all_list=None, nodes=None):
        if not all_list:
            all_list = cls.objects.values("id", "name", "parent")
        if nodes is None:
            nodes = []
        for ele in all_list:
            if ele.get("id") == id:
                parent_id = ele.get("parent")
                if parent_id is not None:
                    cls.get_all_parent(parent_id, all_list, nodes)
                nodes.append(ele)
        return nodes

    class Meta:
        db_table = table_prefix + "system_menu"
        verbose_name = "菜单"
        verbose_name_plural = verbose_name
        ordering = ("sort",)

    def __str__(self):
        return self.name


class MenuField(CoreModel):
    """菜单字段 — column-level permission target"""
    model = models.CharField(max_length=64, verbose_name='表名')
    menu = models.ForeignKey(to='Menu', on_delete=models.CASCADE, verbose_name='菜单', db_constraint=False)
    field_name = models.CharField(max_length=64, verbose_name='模型表字段名')
    title = models.CharField(max_length=64, verbose_name='字段显示名')

    class Meta:
        db_table = table_prefix + "system_menu_field"
        verbose_name = "菜单字段"
        verbose_name_plural = verbose_name
        ordering = ("id",)


class FieldPermission(CoreModel):
    """字段权限 — role × menu_field CRUD 权限"""
    role = models.ForeignKey(to='Role', on_delete=models.CASCADE, verbose_name='角色', db_constraint=False)
    field = models.ForeignKey(to='MenuField', on_delete=models.CASCADE, related_name='menu_field',
                              verbose_name='字段', db_constraint=False)
    is_query = models.BooleanField(default=True, verbose_name='是否可查询')
    is_create = models.BooleanField(default=True, verbose_name='是否可创建')
    is_update = models.BooleanField(default=True, verbose_name='是否可更新')

    class Meta:
        db_table = table_prefix + "system_field_permission"
        verbose_name = "字段权限"
        verbose_name_plural = verbose_name
        ordering = ("id",)


class MenuButton(CoreModel):
    """菜单按钮 — action-level permission (was dvadmin.system.models.MenuButton)"""
    menu = models.ForeignKey(
        to="Menu", db_constraint=False, related_name="menuPermission",
        on_delete=models.CASCADE, verbose_name="关联菜单",
    )
    name = models.CharField(max_length=64, verbose_name="名称")
    value = models.CharField(unique=True, max_length=64, verbose_name="权限值")
    api = models.CharField(max_length=200, verbose_name="接口地址")
    METHOD_CHOICES = (
        (0, "GET"),
        (1, "POST"),
        (2, "PUT"),
        (3, "DELETE"),
    )
    method = models.IntegerField(default=0, verbose_name="接口请求方法", null=True, blank=True)

    class Meta:
        db_table = table_prefix + "system_menu_button"
        verbose_name = "菜单按钮"
        verbose_name_plural = verbose_name
        ordering = ("-name",)

    def __str__(self):
        return f"{self.name}({self.value})"


class RoleMenuPermission(CoreModel):
    """角色-菜单权限桥接"""
    role = models.ForeignKey(
        to="Role", db_constraint=False, related_name="role_menu",
        on_delete=models.CASCADE, verbose_name="关联角色",
    )
    menu = models.ForeignKey(
        to="Menu", db_constraint=False, related_name="role_menu",
        on_delete=models.CASCADE, verbose_name="关联菜单",
    )

    class Meta:
        db_table = table_prefix + "role_menu_permission"
        verbose_name = "角色菜单权限"
        verbose_name_plural = verbose_name


class RoleMenuButtonPermission(CoreModel):
    """角色-按钮权限桥接"""
    role = models.ForeignKey(
        to="Role", db_constraint=False, related_name="role_menu_button",
        on_delete=models.CASCADE, verbose_name="关联角色",
    )
    menu_button = models.ForeignKey(
        to="MenuButton", db_constraint=False, related_name="menu_button_permission",
        on_delete=models.CASCADE, verbose_name="关联菜单按钮",
        null=True, blank=True,
    )
    DATASCOPE_CHOICES = (
        (0, "仅本人数据权限"),
        (1, "本部门及以下数据权限"),
        (2, "本部门数据权限"),
        (3, "全部数据权限"),
        (4, "自定数据权限"),
    )
    data_range = models.IntegerField(default=0, choices=DATASCOPE_CHOICES,
                                     verbose_name="数据权限范围")
    dept = models.ManyToManyField(to="system.Dept", verbose_name="数据权限-部门",
                                  blank=True, db_constraint=False)

    class Meta:
        db_table = table_prefix + "role_menu_button_permission"
        verbose_name = "角色按钮权限"
        verbose_name_plural = verbose_name
