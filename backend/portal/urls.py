"""URL configuration for portal app

路由前缀: /api/portal/
"""

from django.urls import path

from .views.dashboard import (
    dashboard_summary, my_tasks, quick_stats,
    recent_activity, favorites, health,
)

urlpatterns = [
    path('dashboard/', dashboard_summary, name='portal-dashboard'),
    path('my-tasks/', my_tasks, name='portal-my-tasks'),
    path('quick-stats/', quick_stats, name='portal-quick-stats'),
    path('recent-activity/', recent_activity, name='portal-recent-activity'),
    path('favorites/', favorites, name='portal-favorites'),
    path('health/', health, name='portal-health'),
]
