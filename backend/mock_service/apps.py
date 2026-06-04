from django.apps import AppConfig


class MockServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mock_service'
    verbose_name = '模拟数据服务'
