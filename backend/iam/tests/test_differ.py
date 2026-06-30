"""Differ 单元测试 — DeptDiff / UserDiff 算法

Diff 算法是纯逻辑无 I/O，使用 SimpleTestCase 即可。
"""
from django.test import SimpleTestCase

from iam.sync.differ import Differ, DeptNode, UserEntry, DeptDiff, UserDiff


class TestDeptDiff(SimpleTestCase):
    """部门树 Diff 算法测试"""

    def test_all_added(self):
        """所有部门都是新增的（本地无映射）"""
        remote = [
            DeptNode(dn="OU=IT,DC=example,DC=com", name="IT"),
            DeptNode(dn="OU=HR,DC=example,DC=com", name="HR"),
        ]
        local = {}
        diff = Differ.diff_depts(remote, local)
        self.assertEqual(len(diff.added), 2)
        self.assertEqual(len(diff.disabled), 0)
        self.assertEqual(len(diff.updated), 0)

    def test_all_disabled(self):
        """所有本地部门都已经不存在远端"""
        remote = []
        local = {
            "OU=IT,DC=old,DC=com": type("obj", (), {"dept_id": 1, "remote_attrs": {"name": "IT"}})(),
            "OU=HR,DC=old,DC=com": type("obj", (), {"dept_id": 2, "remote_attrs": {"name": "HR"}})(),
        }
        diff = Differ.diff_depts(remote, local)
        self.assertEqual(len(diff.added), 0)
        self.assertEqual(len(diff.disabled), 2)
        self.assertCountEqual(diff.disabled, [1, 2])

    def test_partial_add_and_disable(self):
        """部分新增、部分禁用、部分不变"""
        remote = [
            DeptNode(dn="OU=IT,DC=example,DC=com", name="IT"),
        ]
        local = {
            "OU=IT,DC=example,DC=com": type("obj", (), {"dept_id": 10, "remote_attrs": {"name": "IT"}})(),
            "OU=HR,DC=example,DC=com": type("obj", (), {"dept_id": 20, "remote_attrs": {"name": "HR"}})(),
        }
        diff = Differ.diff_depts(remote, local)
        self.assertEqual(len(diff.added), 0)   # 无新增
        self.assertEqual(len(diff.disabled), 1)  # HR 被禁用
        self.assertEqual(diff.disabled, [20])
        self.assertEqual(len(diff.updated), 0)  # 属性无变化

    def test_attrs_changed_trigger_update(self):
        """远端属性变化应触发更新"""
        remote = [
            DeptNode(dn="OU=IT,DC=example,DC=com", name="IT Dept", attributes={"ou": "IT Dept", "description": "Updated"}),
        ]
        local = {
            "OU=IT,DC=example,DC=com": type("obj", (), {
                "dept_id": 1,
                "remote_attrs": {"ou": "IT", "description": "Original"},
            })(),
        }
        diff = Differ.diff_depts(remote, local)
        self.assertEqual(len(diff.updated), 1)
        self.assertEqual(diff.updated[0]["dept_id"], 1)

    def test_attrs_unchanged_no_update(self):
        """远端属性无变化不应触发更新"""
        remote = [
            DeptNode(dn="OU=IT,DC=example,DC=com", name="IT Dept", attributes={"ou": "IT"}),
        ]
        local = {
            "OU=IT,DC=example,DC=com": type("obj", (), {
                "dept_id": 1,
                "remote_attrs": {"ou": "IT"},
            })(),
        }
        diff = Differ.diff_depts(remote, local)
        self.assertEqual(len(diff.updated), 0)

    def test_parse_parent_dn(self):
        """DN 层级解析"""
        self.assertEqual(Differ.parse_parent_dn("OU=IT,DC=example,DC=com"), "DC=example,DC=com")
        self.assertEqual(Differ.parse_parent_dn("CN=Users,DC=example,DC=com"), "DC=example,DC=com")
        self.assertEqual(Differ.parse_parent_dn("DC=example,DC=com"), "DC=com")
        self.assertIsNone(Differ.parse_parent_dn(""))

    def test_dept_name_from_dn(self):
        """从 DN 提取名称"""
        self.assertEqual(Differ._dept_name_from_dn("OU=IT Department,DC=example,DC=com"), "IT Department")
        self.assertEqual(Differ._dept_name_from_dn("DC=example,DC=com"), "example")


class TestUserDiff(SimpleTestCase):
    """用户列表 Diff 算法测试"""

    def test_all_users_added(self):
        """所有用户都是新增的"""
        remote = [
            UserEntry(dn="CN=zhangsan,OU=IT,DC=example,DC=com", username="zhangsan", dept_dn="OU=IT,DC=example,DC=com"),
        ]
        local = {}
        dept_map = {"OU=IT,DC=example,DC=com": 1}
        diff = Differ.diff_users(remote, local, dept_map)
        self.assertEqual(len(diff.added), 1)
        self.assertEqual(diff.added[0]["username"], "zhangsan")
        self.assertEqual(diff.added[0]["dept_id"], 1)

    def test_user_disabled_when_removed(self):
        """远端删除用户应触发禁用"""
        remote = []
        local = {
            "CN=lisi,OU=IT,DC=example,DC=com": type("obj", (), {"user_id": 1, "remote_attrs": {"mail": "lisi@test.com"}})(),
        }
        diff = Differ.diff_users(remote, local, {})
        self.assertEqual(len(diff.disabled), 1)
        self.assertEqual(diff.disabled, [1])

    def test_user_updated_on_attr_change(self):
        """属性变化应触发更新"""
        remote = [
            UserEntry(dn="CN=wangwu,OU=IT,DC=example,DC=com", username="wangwu",
                      dept_dn="OU=IT,DC=example,DC=com",
                      attributes={"mail": "new@test.com", "displayName": "Wang Wu"}),
        ]
        local = {
            "CN=wangwu,OU=IT,DC=example,DC=com": type("obj", (), {
                "user_id": 5,
                "remote_attrs": {"mail": "old@test.com", "displayName": "Wang Wu"},
            })(),
        }
        dept_map = {"OU=IT,DC=example,DC=com": 10}
        diff = Differ.diff_users(remote, local, dept_map)
        self.assertEqual(len(diff.updated), 1)
        self.assertEqual(diff.updated[0]["user_id"], 5)
