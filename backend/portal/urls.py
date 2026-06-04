"""URL configuration for portal app

路由前缀: /api/portal/
"""

from django.urls import path

from .views.dashboard import dashboard_summary, my_tasks, quick_stats

urlpatterns = [
    path('dashboard/', dashboard_summary, name='dashboard'),
    path('my-tasks/', my_tasks, name='my-tasks'),
    path('quick-stats/', quick_stats, name='quick-stats'),
]
