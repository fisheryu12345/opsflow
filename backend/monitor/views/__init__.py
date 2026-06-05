# -*- coding: utf-8 -*-
"""Views package for monitor app"""

from .strategy_views import MonitorStrategyViewSet, MonitorItemViewSet
from .alert_views import AlertEventViewSet, AlertViewSet
from .notification_views import NotifyGroupViewSet, DutyPlanViewSet, DutyArrangeViewSet
from .action_views import AlertAssignGroupViewSet, ActionPluginViewSet
from .shield_views import ShieldPlanViewSet
from .collect_views import CollectConfigViewSet
from .dashboard_views import DashboardViewSet

__all__ = [
    'MonitorStrategyViewSet', 'MonitorItemViewSet',
    'AlertEventViewSet', 'AlertViewSet',
    'NotifyGroupViewSet', 'DutyPlanViewSet', 'DutyArrangeViewSet',
    'AlertAssignGroupViewSet', 'ActionPluginViewSet',
    'ShieldPlanViewSet', 'CollectConfigViewSet',
    'DashboardViewSet',
]
