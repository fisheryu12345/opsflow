"""Page-level permission config — PageTab + PageButton

These models define what tabs and buttons each app has,
and what IAMPermission codename is required to access each.
Frontend renders purely from the /api/iam/page-permissions/ API.
"""
from django.db import models

from dvadmin.utils.models import CoreModel, table_prefix


class IAMMenu(models.Model):
    """菜单 — 侧边栏导航配置 (replaces dvadmin Menu, maps to legacy DB schema)"""
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name="描述")
    modifier = models.CharField(max_length=255, null=True, blank=True, verbose_name="修改人")
    dept_belong_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="部门归属")
    update_datetime = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="修改时间")
    create_datetime = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="创建时间")
    icon = models.CharField(max_length=64, null=True, blank=True, verbose_name="图标")
    name = models.CharField(max_length=64, verbose_name="名称")
    sort = models.IntegerField(default=1, null=True, blank=True, verbose_name="排序")
    is_link = models.BooleanField(default=False, verbose_name="是否外链")
    link_url = models.CharField(max_length=255, null=True, blank=True, verbose_name="链接地址")
    is_catalog = models.BooleanField(default=False, verbose_name="是否目录")
    web_path = models.CharField(max_length=128, null=True, blank=True, verbose_name="路由地址")
    component = models.CharField(max_length=128, null=True, blank=True, verbose_name="组件地址")
    component_name = models.CharField(max_length=50, null=True, blank=True, verbose_name="组件名称")
    status = models.BooleanField(default=True, blank=True, verbose_name="状态")
    cache = models.BooleanField(default=False, blank=True, verbose_name="缓存")
    visible = models.BooleanField(default=True, blank=True, verbose_name="可见")
    is_iframe = models.BooleanField(default=False, blank=True, verbose_name="iframe")

    @classmethod
    def get_all_parent(cls, menu_id, all_list=None, nodes=None):
        if not all_list:
            all_list = cls.objects.values("id", "name", "dept_belong_id")
        if nodes is None:
            nodes = []
        for ele in all_list:
            if ele.get("id") == menu_id:
                parent_id = ele.get("dept_belong_id")
                if parent_id is not None:
                    cls.get_all_parent(parent_id, all_list, nodes)
                nodes.append(ele)
        return nodes

    class Meta:
        db_table = table_prefix + "iam_menu"
        verbose_name = "菜单"
        verbose_name_plural = verbose_name
        ordering = ("sort",)

    def __str__(self):
        return self.name


class PageTab(CoreModel):
    """Tab 配置 — 每个应用有哪些 tab"""
    app = models.CharField(max_length=64, verbose_name="所属应用",
                            help_text="opsflow / itsm / cmdb")
    key = models.CharField(max_length=64, verbose_name="Tab 标识",
                            help_text="如 templates / dashboard")
    label_zh = models.CharField(max_length=128, verbose_name="中文标签")
    label_en = models.CharField(max_length=128, verbose_name="英文标签")
    icon = models.CharField(max_length=64, verbose_name="图标名",
                            help_text="Element Plus 图标组件名")
    sort = models.IntegerField(default=1, verbose_name="排序")
    required_perm = models.CharField(
        max_length=128, null=True, blank=True, verbose_name="所需权限 codename",
        help_text="null 表示无需特殊权限（如 dashboard/logs 默认开放）"
    )
    is_default = models.BooleanField(default=False, verbose_name="是否默认 tab")
    visible = models.BooleanField(default=True, verbose_name="是否可见")

    class Meta:
        db_table = table_prefix + "iam_page_tab"
        verbose_name = "页面 Tab 配置"
        verbose_name_plural = verbose_name
        unique_together = ('app', 'key')
        ordering = ['app', 'sort']

    def __str__(self):
        return f"[{self.app}] {self.label_zh}"


class PageButton(CoreModel):
    """按钮配置 — Tab 内的按钮"""
    tab = models.ForeignKey(
        PageTab, on_delete=models.CASCADE, related_name='buttons',
        verbose_name="归属 Tab",
    )
    key = models.CharField(max_length=64, verbose_name="按钮标识",
                            help_text="如 create / delete")
    label_zh = models.CharField(max_length=128, verbose_name="中文标签")
    label_en = models.CharField(max_length=128, verbose_name="英文标签")
    icon = models.CharField(max_length=64, null=True, blank=True, verbose_name="图标名")
    required_perm = models.CharField(max_length=128, verbose_name="所需权限 codename")
    style = models.CharField(max_length=32, default='default', verbose_name="按钮样式",
                              help_text="primary / danger / default / text")
    sort = models.IntegerField(default=1, verbose_name="排序")

    class Meta:
        db_table = table_prefix + "iam_page_button"
        verbose_name = "页面按钮配置"
        verbose_name_plural = verbose_name
        unique_together = ('tab', 'key')
        ordering = ['sort']

    def __str__(self):
        return f"{self.tab.key}.{self.key}"
