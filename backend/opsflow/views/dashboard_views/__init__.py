"""Dashboard API endpoints — 为 urls.py 向后兼容重新导出"""

from opsflow.views.dashboard_views.stats import dashboard_stats, dashboard_schedule_stats
from opsflow.views.dashboard_views.trends import dashboard_trend, dashboard_success_rate_trend
from opsflow.views.dashboard_views.analytics import (
    dashboard_top_templates,
    dashboard_user_activity,
    dashboard_status_distribution,
    dashboard_node_type_distribution,
    dashboard_duration_distribution,
    dashboard_node_duration_top,
    dashboard_template_stats,
)

__all__ = [
    'dashboard_stats',
    'dashboard_trend',
    'dashboard_schedule_stats',
    'dashboard_top_templates',
    'dashboard_user_activity',
    'dashboard_status_distribution',
    'dashboard_node_type_distribution',
    'dashboard_duration_distribution',
    'dashboard_node_duration_top',
    'dashboard_success_rate_trend',
    'dashboard_template_stats',
]
