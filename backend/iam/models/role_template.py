"""RoleTemplate — pre-configured Role + Menu/Button bindings for quick project setup."""
from django.db import models
from common.utils.models import CoreModel, table_prefix


class RoleTemplate(CoreModel):
    name = models.CharField(max_length=128, verbose_name="模板名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="模板编码")
    source_role = models.ForeignKey(
        'iam.IAMRole', on_delete=models.SET_NULL, null=True, blank=True,
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
        """Apply this template's IAMPermission bindings to a target IAMRole."""
        from iam.models.permission import IAMRolePermission, IAMPermission
        from iam.models.page_config import PageTab, PageButton
        # Clear existing
        IAMRolePermission.objects.filter(role=role).delete()
        # Apply template: reconstruct codenames from menus/buttons stored as old IDs
        for entry in self.menus:
            menu_id = entry.get('menu_id')
            btn_ids = entry.get('button_ids', [])
            # Look up PageTabs whose app matches this menu (via Menu.app)
            if menu_id:
                from iam.models.page_config import IAMMenu as OldMenu
                menu = OldMenu.objects.filter(id=menu_id).first()
                if menu and menu.app:
                    tab_perms = PageTab.objects.filter(app=menu.app).values_list('required_perm', flat=True)
                    for codename in tab_perms:
                        if codename:
                            perm = IAMPermission.objects.filter(codename=codename).first()
                            if perm:
                                IAMRolePermission.objects.get_or_create(role=role, permission=perm)
                    # Also add button perms
                    buttons = PageButton.objects.filter(tab__app=menu.app)
                    for btn in buttons:
                        if btn.required_perm:
                            perm = IAMPermission.objects.filter(codename=btn.required_perm).first()
                            if perm:
                                IAMRolePermission.objects.get_or_create(role=role, permission=perm)
