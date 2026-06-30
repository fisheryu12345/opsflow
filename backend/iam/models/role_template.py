"""RoleTemplate — pre-configured Role + Menu/Button bindings for quick project setup."""
from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


class RoleTemplate(CoreModel):
    name = models.CharField(max_length=128, verbose_name="模板名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="模板编码")
    source_role = models.ForeignKey(
        'iam.Role', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="来源角色",
    )
    menus = models.JSONField(default=list, verbose_name="菜单权限列表")  # [{menu_id, button_ids: [...]}]
    is_system = models.BooleanField(default=False, verbose_name="系统预置")

    class Meta:
        db_table = table_prefix + "iam_role_template"
        verbose_name = "角色模板"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name} ({'system' if self.is_system else 'custom'})"

    def apply_to_role(self, role):
        """Apply this template's menu/button permissions to a target Role."""
        from iam.models.menu_rbac import RoleMenuPermission, RoleMenuButtonPermission, Menu, MenuButton
        # Clear existing
        RoleMenuPermission.objects.filter(role=role).delete()
        RoleMenuButtonPermission.objects.filter(role=role).delete()
        # Apply template
        for entry in self.menus:
            menu_id = entry.get('menu_id')
            if menu_id and Menu.objects.filter(id=menu_id).exists():
                RoleMenuPermission.objects.get_or_create(role=role, menu_id=menu_id)
            for btn_id in entry.get('button_ids', []):
                if MenuButton.objects.filter(id=btn_id).exists():
                    RoleMenuButtonPermission.objects.get_or_create(role=role, menu_button_id=btn_id)
