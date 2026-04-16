from django.apps import AppConfig
import socket


class StockConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stock'
    
    def ready(self):
        # 检查本机IP地址，只有特定IP才启动定时器
        try:
            # 获取本机所有IP地址
            hostname = socket.gethostname()
            ip_addresses = socket.gethostbyname_ex(hostname)[2]
            
            # 检查是否包含目标IP
            target_ip = '172.25.21.215'
            if target_ip not in ip_addresses:
                print(f"[INFO] 当前IP地址 {ip_addresses} 不是目标IP {target_ip}，跳过启动定时器")
                return
            
            print(f"[INFO] 检测到目标IP {target_ip}，准备启动定时任务调度器...")
        except Exception as e:
            print(f"[ERROR] 获取IP地址失败: {e}，跳过启动定时器")
            return
        
        # 导入调度器和任务
        from django_redis import get_redis_connection
        # from . import tasks # 确保任务函数被导入
        redis = get_redis_connection('default')
        lock_key = 'lock:scheduler'
        lock_timeout = 10
        if redis.set(lock_key, 'true', nx=True, ex=lock_timeout):
            from stock.scheduler.scheduler import scheduler
            try:
                # 添加你的定时任务
                # 这里演示每10秒执行一次任务
                # 启动调度器
                if not scheduler.running:
                    scheduler.start()
                    print("启动定时任务成功！")
            finally:
                redis.delete(lock_key)