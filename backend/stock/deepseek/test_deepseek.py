"""
DeepSeek API 单元测试

运行方式：
python -m pytest test_deepseek.py -v
或
python test_deepseek.py
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from stock.deepseek.deepseek import DeepSeekClient, create_deepseek_client
except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保已安装依赖: pip install langchain langchain-openai httpx python-dotenv")
    sys.exit(1)


class TestDeepSeekClient(unittest.TestCase):
    """DeepSeek 客户端测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_api_key = "test-api-key-12345"
        self.test_base_url = "https://api.deepseek.com/v1"
    
    def test_initialization_with_api_key(self):
        """测试使用 API Key 初始化"""
        client = DeepSeekClient(api_key=self.test_api_key)
        self.assertEqual(client.api_key, self.test_api_key)
        self.assertEqual(client.model, "deepseek-chat")
        self.assertEqual(client.temperature, 0.7)
        self.assertEqual(client.max_tokens, 2000)
    
    def test_initialization_without_api_key(self):
        """测试未提供 API Key 时抛出异常"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                DeepSeekClient()
            self.assertIn("未提供 API Key", str(context.exception))
    
    def test_initialization_with_custom_params(self):
        """测试自定义参数初始化"""
        client = DeepSeekClient(
            api_key=self.test_api_key,
            model="deepseek-coder",
            temperature=0.3,
            max_tokens=1000,
            system_prompt="你是一个测试助手",
            timeout=30
        )
        
        self.assertEqual(client.model, "deepseek-coder")
        self.assertEqual(client.temperature, 0.3)
        self.assertEqual(client.max_tokens, 1000)
        self.assertEqual(client.timeout, 30)
        self.assertEqual(len(client.messages), 1)  # 系统提示词
    
    def test_system_prompt_added_to_messages(self):
        """测试系统提示词是否正确添加到消息列表"""
        client = DeepSeekClient(
            api_key=self.test_api_key,
            system_prompt="测试系统提示词"
        )
        
        self.assertEqual(len(client.messages), 1)
        self.assertEqual(client.messages[0].content, "测试系统提示词")
    
    @patch('stock.deepseek.deepseek.ChatOpenAI')
    def test_chat_method(self, mock_chat_openai):
        """测试 chat 方法"""
        # Mock LLM 响应
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "这是AI的回复"
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm
        
        client = DeepSeekClient(api_key=self.test_api_key)
        response = client.chat("你好")
        
        self.assertEqual(response, "这是AI的回复")
        self.assertEqual(len(client.messages), 2)  # 用户消息 + AI回复
    
    @patch('stock.deepseek.deepseek.ChatOpenAI')
    def test_chat_with_clear_history(self, mock_chat_openai):
        """测试清空对话历史"""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "回复"
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm
        
        client = DeepSeekClient(api_key=self.test_api_key)
        
        # 进行两轮对话
        client.chat("第一轮")
        client.chat("第二轮", clear_history=True)
        
        # 清空后应该只有系统提示词（如果有）+ 当前轮次的消息
        self.assertLessEqual(len(client.messages), 2)
    
    def test_reset_conversation(self):
        """测试重置对话"""
        client = DeepSeekClient(
            api_key=self.test_api_key,
            system_prompt="系统提示词"
        )
        
        # 模拟添加了一些消息
        client.messages.append(Mock())
        client.messages.append(Mock())
        
        # 重置
        client.reset_conversation()
        
        # 应该只剩下系统提示词
        self.assertEqual(len(client.messages), 1)
    
    def test_get_conversation_history(self):
        """测试获取对话历史"""
        from langchain.schema import HumanMessage, AIMessage, SystemMessage
        
        client = DeepSeekClient(api_key=self.test_api_key)
        
        # 手动添加一些消息
        client.messages = [
            SystemMessage(content="系统消息"),
            HumanMessage(content="用户消息"),
            AIMessage(content="AI回复")
        ]
        
        history = client.get_conversation_history()
        
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["role"], "system")
        self.assertEqual(history[1]["role"], "user")
        self.assertEqual(history[2]["role"], "assistant")
    
    def test_factory_function(self):
        """测试工厂函数"""
        client = create_deepseek_client(
            api_key=self.test_api_key,
            model="deepseek-coder",
            temperature=0.5
        )
        
        self.assertIsInstance(client, DeepSeekClient)
        self.assertEqual(client.model, "deepseek-coder")
        self.assertEqual(client.temperature, 0.5)


class TestDeepSeekIntegration(unittest.TestCase):
    """集成测试（需要真实的 API Key）"""
    
    @unittest.skipIf(not os.getenv("DEEPSEEK_API_KEY"), "未设置 DEEPSEEK_API_KEY 环境变量")
    def test_real_api_call(self):
        """测试真实 API 调用"""
        try:
            client = DeepSeekClient(
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                temperature=0.7
            )
            
            response = client.chat("你好，请用一句话介绍自己")
            
            self.assertIsNotNone(response)
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            
        except Exception as e:
            self.fail(f"API 调用失败: {e}")


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
