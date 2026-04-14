"""
DeepSeek API 集成示例 - 结合本地日历库与 AI 增强说明

本代码结合本地日历库与 AI 模型，实现国内夜盘交易状态的判断和同步。
"""

import os
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from django.template.loader import render_to_string
from stock.deepseek import DeepSeekClient
from datetime import datetime
from stock.models import StrategyConfig
from stock.utils.send_mail import send_email

# 引入中国日历库以获取准确的节假日信息
try:
    from chinese_calendar import is_workday, is_holiday, get_holiday_detail
except ImportError:
    print("[WARN] chinesecalendar 未安装，将降级为纯 AI 判断模式。建议运行: pip install chinesecalendar")
    is_workday = None


# ==================== 1. 定义数据结构（Pydantic Model）====================
class NightTradingStatus(BaseModel):
    """夜盘交易状态响应模型"""
    is_trading: bool = Field(description="当前是否处于夜盘交易时间")
    reason: str = Field(description="判断原因说明")


# ==================== 2. 核心逻辑：规则校验 + AI 增强 ====================
def create_night_trading_checker():
    """
    创建夜盘交易状态检查器
    
    Returns:
        callable: 执行检查的函数
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "sk-217d89e0760c4e6eab307e87383f34b5")
    client = DeepSeekClient(api_key=api_key)
    
    parser = JsonOutputParser(pydantic_object=NightTradingStatus)
    
    prompt = PromptTemplate(
        template="""
已知日期 {date} 的基础交易状态为：{base_status}。
请基于此事实，生成一段关于国内期货市场夜盘交易的详细说明。

{format_instructions}

要求：
1. is_trading 必须严格等于 {base_is_trading}。
2. reason: 解释为什么该日期有/没有夜盘（例如提及星期几、是否为调休等）。
""",
        input_variables=["date", "base_status", "base_is_trading"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    def check_and_sync():
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # --- 方案二：使用本地规则库进行硬性判断 ---
            if is_workday:
                # 判断明天是否工作且非节假日
                # 注意：这里根据原代码逻辑，查询的是“当前日期”的状态来决定明天的任务暂停情况
                # 通常夜盘属于第二天凌晨，但业务上往往在当天白天配置。
                # 此处沿用原逻辑：检查 today 来决定当前的 pause_open_task_job
                is_trading_day = is_workday(dt) and not is_holiday(dt)
                
                if is_trading_day:
                    base_reason = "工作日"
                elif is_holiday(dt):
                    # 如果是节假日，获取具体节日名称
                    holiday_name = get_holiday_detail(dt)[1] or "法定节假日"
                    base_reason = f"节假日({holiday_name})"
                else:
                    base_reason = "周末或法定节假日"
            else:
                # 降级处理：简单判断星期几
                is_trading_day = dt.weekday() < 5
                base_reason = "周一至周五" if is_trading_day else "周末"

            print(f"[INFO] 规则引擎判定 [{date_str}]: {'交易中' if is_trading_day else '休市中'} ({base_reason})")
            
            # --- 方案一：利用 AI 生成更专业的说明文本 ---
            formatted_prompt = prompt.format(
                date=date_str, 
                base_status=base_reason,
                base_is_trading=is_trading_day
            )
            
            print(f"[INFO] 发送请求到 DeepSeek 生成说明...")
            response_text = client.chat(formatted_prompt)
            
            result = parser.parse(response_text)
            status = NightTradingStatus(**result)
            
            # 最终安全校验：确保 AI 没有篡改核心逻辑
            final_is_trading = status.is_trading if status.is_trading == is_trading_day else is_trading_day
            
            pause_open_task = not final_is_trading
            updated_count = StrategyConfig.objects.update(pause_open_task_job=pause_open_task)
            
            print(f"✅ 配置同步成功: pause_open_task_job={pause_open_task}, 影响 {updated_count} 条记录")
            
            # --- 新增：如果是节假日暂停交易，发送邮件通知 ---
            if not final_is_trading and is_workday and is_holiday(dt):
                _send_holiday_notification(date_str, base_reason, status.reason)
            
            return {
                'success': True,
                'is_trading': final_is_trading,
                'reason': status.reason,
                'pause_open_task_job': pause_open_task,
                'updated_count': updated_count
            }
            
        except Exception as e:
            error_msg = f"❌ 检查失败: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    return check_and_sync


def _send_holiday_notification(date_str, base_reason, ai_reason):
    """
    发送节假日暂停交易通知邮件
    
    Args:
        date_str: 日期字符串 (YYYY-MM-DD)
        base_reason: 基础原因（来自日历库）
        ai_reason: AI 生成的详细说明
    """
    try:
        # 使用 Django Template 渲染 HTML
        html_content = render_to_string('stock/night_trading_holiday_notice.html', {
            'date_str': date_str,
            'base_reason': base_reason,
            'ai_reason': ai_reason,
        })
        
        # 发送邮件
        subject = f"⚠️ 期货交易暂停通知 - {date_str} 夜盘休市"
        receiver_email = os.getenv('EMAIL_RECEIVER', '312711936@qq.com')
        
        success = send_email(
            subject=subject,
            body=html_content,
            receiver_email=receiver_email,
            is_html=True
        )
        
        if success:
            print(f"📧 邮件通知已发送至: {receiver_email}")
        else:
            print(f"⚠️ 邮件发送失败，请检查邮箱配置")
            
    except Exception as e:
        print(f"⚠️ 发送邮件时出错: {str(e)}")
        # 邮件发送失败不影响主流程


# ==================== 3. 便捷函数 ====================
def check_night_trading_and_sync_config():
    """
    检查夜盘交易状态并同步到策略配置（便捷函数）
    
    Returns:
        dict: 检查结果和同步状态
    """
    checker = create_night_trading_checker()
    return checker()


# ==================== 4. 主程序入口 ====================
if __name__ == "__main__":
    print("="*60)
    print("夜盘交易状态检查工具 (混合增强版)")
    print("="*60)
    result = check_night_trading_and_sync_config()
    print("\n" + "="*60)
    if result['success']:
        print("✅ 执行成功")
        print(f"   - 夜盘状态: {'交易中' if result['is_trading'] else '休市中'}")
        print(f"   - 原因: {result['reason']}")
        print(f"   - 暂停任务: {result['pause_open_task_job']}")
    else:
        print("❌ 执行失败")
        print(f"   - 错误: {result['error']}")
    print("="*60)
