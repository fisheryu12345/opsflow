from celery import shared_task

@shared_task
def example_task(x, y):
    """
    一个简单的Celery任务示例：返回两个数的和
    """
    return x + y