"""Mock Service URL Configuration — 提供模拟数据接口路由"""

from django.urls import path

from .views import (
    cmdb_esxi_hosts,
    cmdb_servers,
    cmdb_netapp_clusters,
    cmdb_servicenow_instances,
    servicenow_change_requests,
    cmdb_pmax_arrays,
    cmdb_ip_pools,
    cmdb_resources,
    cmdb_categories,
)

urlpatterns = [
    path('esxi-hosts/', cmdb_esxi_hosts, name='mock-cmdb-esxi-hosts'),
    path('servers/', cmdb_servers, name='mock-cmdb-servers'),
    path('netapp-clusters/', cmdb_netapp_clusters, name='mock-cmdb-netapp-clusters'),
    path('servicenow-instances/', cmdb_servicenow_instances, name='mock-cmdb-servicenow-instances'),
    path('servicenow-change-requests/', servicenow_change_requests, name='mock-servicenow-change-requests'),
    path('pmax-arrays/', cmdb_pmax_arrays, name='mock-cmdb-pmax-arrays'),
    path('ip-pools/', cmdb_ip_pools, name='mock-cmdb-ip-pools'),
    path('resources/', cmdb_resources, name='mock-cmdb-resources'),
    path('categories/', cmdb_categories, name='mock-cmdb-categories'),
]
