from datetime import datetime, timezone, timedelta
import time

def unix_to_beijing_readable(unix_timestamp: float) -> str:
    """
    将Unix时间戳转换为北京时间可读格式
    
    Args:
        unix_timestamp: Unix时间戳（秒或毫秒）
    
    Returns:
        北京时间字符串，格式: "2026-04-06 15:42:01"
    """
    # 判断是毫秒还是秒时间戳
    if unix_timestamp > 1e12:  # 毫秒时间戳
        unix_timestamp = unix_timestamp / 1000
    
    # 转换为UTC时间
    dt_utc = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    
    # 转换为北京时间 (UTC+8)
    beijing_tz = timezone(timedelta(hours=8))
    dt_beijing = dt_utc.astimezone(beijing_tz)
    
    # 格式化为可读字符串
    return dt_beijing.strftime("%Y-%m-%d %H:%M:%S")

# 测试
if __name__ == "__main__":
    # 当前时间戳
    current_unix = time.time()
    print(f"当前Unix时间戳: {current_unix}")
    print(f"北京时间: {unix_to_beijing_readable(current_unix)}")
    
    # 毫秒时间戳
    current_unix_ms = int(time.time() * 1000)
    print(f"当前Unix毫秒时间戳: {current_unix_ms}")
    print(f"北京时间: {unix_to_beijing_readable(current_unix_ms)}")
    
    # 测试特定时间戳 (例如2026-04-06)
    test_timestamp = 1775463131  # 2026-04-06左右的时间戳
    print(f"测试时间戳: {test_timestamp}")
    print(f"北京时间: {unix_to_beijing_readable(test_timestamp)}")