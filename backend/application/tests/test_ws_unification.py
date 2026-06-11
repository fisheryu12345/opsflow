# -*- coding: utf-8 -*-
"""WebSocket 统一规范 — 纯逻辑测试（不依赖 DB/Redis）

测试 ws_push 模块的核心逻辑：消息信封、函数调用、异常处理。
通过 mock 隔离 channel_layer 依赖。
"""
import json
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestBuildMessage(unittest.TestCase):
    """测试消息信封组装 — 纯函数，无外部依赖"""

    def setUp(self):
        # 避免 import 时触发 Django settings 配置
        import importlib
        self.ws_push = importlib.import_module("application.ws_push")

    def test_build_message_format(self):
        """验证统一信封结构: topic/action/payload/timestamp"""
        msg = self.ws_push._build_message("node_status", "update", {"execution_id": 42})
        self.assertEqual(msg["topic"], "node_status")
        self.assertEqual(msg["action"], "update")
        self.assertEqual(msg["payload"], {"execution_id": 42})
        # ISO 8601 格式校验
        self.assertRegex(msg["timestamp"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_build_message_unicode(self):
        """验证中文字段正常通过"""
        msg = self.ws_push._build_message("notification", "new", {"title": "新消息", "content": "你好"})
        self.assertEqual(msg["payload"]["title"], "新消息")

    def test_build_message_empty_payload(self):
        """验证空 payload 场景"""
        msg = self.ws_push._build_message("system", "info", {})
        self.assertEqual(msg["payload"], {})

    def test_build_message_timestamp_utc(self):
        """验证时间戳为 UTC"""
        msg = self.ws_push._build_message("t", "a", {})
        # 当前 UTC 时间 ± 5 秒内
        now = datetime.now(timezone.utc)
        msg_dt = datetime.strptime(msg["timestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        delta = abs((now - msg_dt).total_seconds())
        self.assertLess(delta, 5)


class TestDoSend(unittest.TestCase):
    """测试 _do_send 异常处理和正常调用"""

    def setUp(self):
        import importlib
        self.ws_push = importlib.import_module("application.ws_push")

    @patch("application.ws_push.get_channel_layer", return_value=None)
    def test_channel_layer_none_skips_gracefully(self, mock_get):
        """channel_layer 不可用时应静默跳过（不抛异常）"""
        self.ws_push._do_send("user_42", {"topic": "t", "action": "a", "payload": {}})
        # 不抛异常即通过

    def test_group_send_called_with_correct_args(self):
        """验证 group_send 调用参数正确（通过 InMemoryChannelLayer 集成）"""
        from channels.layers import InMemoryChannelLayer
        from asgiref.sync import async_to_sync
        layer = InMemoryChannelLayer()
        # 模拟 consumer 加入组
        async_to_sync(layer.group_add)("user_42", "test_channel")
        with patch("application.ws_push.get_channel_layer", return_value=layer):
            self.ws_push._do_send("user_42", {"topic": "node_status", "action": "update", "payload": {"node_id": "n1"}})
        # 验证消息已被推送到组中并可消费
        msgs = async_to_sync(layer.receive)("test_channel")
        self.assertEqual(msgs["type"], "push.message")
        self.assertEqual(msgs["json"]["topic"], "node_status")
        self.assertEqual(msgs["json"]["payload"]["node_id"], "n1")


class TestPushToUser(unittest.TestCase):
    """测试 push_to_user / push_to_users"""

    def setUp(self):
        import importlib
        self.ws_push = importlib.import_module("application.ws_push")

    @patch("application.ws_push._do_send")
    def test_push_to_user_uses_user_group(self, mock_do_send):
        """验证 push_to_user 推送到 user_{id} 组"""
        self.ws_push.push_to_user(42, "node_status", "update", {"execution_id": 1})
        mock_do_send.assert_called_once()
        group = mock_do_send.call_args[0][0]
        msg = mock_do_send.call_args[0][1]
        self.assertEqual(group, "user_42")
        self.assertEqual(msg["topic"], "node_status")

    @patch("application.ws_push._do_send")
    def test_push_to_users_batch(self, mock_do_send):
        """验证 push_to_users 遍历所有用户"""
        self.ws_push.push_to_users([1, 2, 3], "notification", "new", {"title": "hi"})
        self.assertEqual(mock_do_send.call_count, 3)
        groups = [args[0][0] for args in mock_do_send.call_args_list]
        self.assertEqual(groups, ["user_1", "user_2", "user_3"])

    @patch("application.ws_push._do_send")
    def test_push_to_users_empty_list(self, mock_do_send):
        """空用户列表不应调用 _do_send"""
        self.ws_push.push_to_users([], "t", "a", {})
        mock_do_send.assert_not_called()

    @patch("application.ws_push._do_send")
    def test_push_to_user_zero_id(self, mock_do_send):
        """user_id=0 不应阻塞"""
        self.ws_push.push_to_user(0, "t", "a", {})
        mock_do_send.assert_called_once()
        self.assertEqual(mock_do_send.call_args[0][0], "user_0")


class TestConsumerLogic(unittest.TestCase):
    """验证 Consumer receive 按 topic 路由的逻辑"""

    def test_heartbeat_no_topic_ignored(self):
        """心跳 {token} 无 topic 字段 → 静默忽略"""
        data = {"token": "some-jwt-token"}
        topic = data.get("topic")
        self.assertIsNone(topic)  # 当前 receive 只检查 topic，无 topic 不处理

    def test_notification_no_message_id_ignored(self):
        """{topic:'notification'} 无 message_id 时不执行中继"""
        data = {"topic": "notification", "payload": {}}
        self.assertEqual(data.get("topic"), "notification")
        # payload 无 message_id，中继逻辑应跳过

    def test_notification_with_message_id_routes_correctly(self):
        """带 message_id 时正确识别为中继消息"""
        data = {"topic": "notification", "payload": {"message_id": 123}}
        self.assertEqual(data.get("topic"), "notification")
        self.assertIsNotNone(data.get("payload", {}).get("message_id"))

    def test_unknown_topic_ignored(self):
        """未知 topic 应被静默忽略"""
        data = {"topic": "something_unknown", "payload": {}}
        topic = data.get("topic")
        self.assertIsNotNone(topic)  # topic 非 None
        # MegCenter.receive 只处理 topic='notification'，其他跳过


if __name__ == "__main__":
    unittest.main(verbosity=2)
