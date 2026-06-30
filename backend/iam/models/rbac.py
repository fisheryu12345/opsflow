from django.db import models

from iam.models.menu_rbac import Role, Menu, MenuButton
from dvadmin.system.models import Users
from dvadmin.utils.models import CoreModel, table_prefix


class PermissionRequest(CoreModel):
    class RequestType(models.TextChoices):
        ROLE = 'role', '角色'
        MENU = 'menu', '菜单'
        MENU_BUTTON = 'menu_button', '按钮'
        PROJECT_ROLE = 'project_role', '项目角色'

    class Status(models.TextChoices):
        PENDING = 'pending', '待审批'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已驳回'

    PROJECT_ROLE_CHOICES = (
        ('admin', '管理员'),
        ('editor', '编辑者'),
        ('viewer', '只读'),
    )

    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='permission_requests', verbose_name='申请人')
    request_type = models.CharField(max_length=20, choices=RequestType.choices, verbose_name='申请类型')
    target_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='目标角色')
    target_menu = models.ForeignKey(Menu, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='目标菜单')
    target_menu_button = models.ForeignKey(MenuButton, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='目标按钮')
    target_project = models.ForeignKey('iam.Project', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='目标项目')
    target_project_role = models.CharField(max_length=20, choices=PROJECT_ROLE_CHOICES, null=True, blank=True, verbose_name='项目角色')
    selected_buttons = models.JSONField(default=list, blank=True, verbose_name='选中的按钮ID列表')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name='状态')
    reason = models.TextField(verbose_name='申请理由')
    reviewer = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_requests', verbose_name='审批人')
    review_comment = models.TextField(blank=True, default='', verbose_name='审批意见')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审批时间')

    class Meta:
        db_table = table_prefix + 'iam_permission_request'
        verbose_name = '权限申请'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f'{self.user} - {self.get_request_type_display()} - {self.get_status_display()}'


class UserDirectPermission(CoreModel):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='direct_permissions', verbose_name='用户')
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, null=True, blank=True, verbose_name='直接授权菜单')
    menu_button = models.ForeignKey(MenuButton, on_delete=models.CASCADE, null=True, blank=True, verbose_name='直接授权按钮')
    granted_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='granted_permissions', verbose_name='授权人')

    class Meta:
        db_table = table_prefix + 'iam_user_direct_permission'
        verbose_name = '用户直接授权'
        verbose_name_plural = verbose_name
        unique_together = [('user', 'menu'), ('user', 'menu_button')]

    def __str__(self):
        return f'{self.user} - direct permission'
