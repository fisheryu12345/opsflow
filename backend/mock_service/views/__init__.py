"""Mock views — 模拟 CMDB / IT服务管理 / 基础设施等外部系统 API"""

from .esxi import cmdb_esxi_hosts
from .servers import cmdb_servers
from .netapp import cmdb_netapp_clusters
from .servicenow import cmdb_servicenow_instances, servicenow_change_requests
from .pmax import cmdb_pmax_arrays
from .ip_pools import cmdb_ip_pools
from .resources import cmdb_resources
from .categories import cmdb_categories

__all__ = [
    'cmdb_esxi_hosts',
    'cmdb_servers',
    'cmdb_netapp_clusters',
    'cmdb_servicenow_instances',
    'servicenow_change_requests',
    'cmdb_pmax_arrays',
    'cmdb_ip_pools',
    'cmdb_resources',
    'cmdb_categories',
]
