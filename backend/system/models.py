from django.db import models
class Dept(models.Model):
    class Meta:
        managed = False
        db_table = 'opsflow_iam_dept'
class RoleMenuButtonPermission(models.Model):
    dept = models.ManyToManyField('system.Dept', blank=True, db_constraint=False)
    class Meta:
        managed = False
        db_table = 'opsflow_iam_role_menu_button_permission'
