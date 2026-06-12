# mock_service — 模块索引

> 上次自动更新: 2026-06-12

---

## `mock_service/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Mock Service — 提供模拟数据接口（CMDB / IT服务管理 / 基础设施等） |
| `apps.py` | 123 | `MockServiceConfig` |
| `urls.py` |  | Mock Service URL Configuration — 提供模拟数据接口路由 |

## `mock_service\views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Mock views — 模拟 CMDB / IT服务管理 / 基础设施等外部系统 API |
| `categories.py` | 分类树 Mock — 供级联选择器使用（数据中心→机柜→设备类型→实例） | `cmdb_categories()` — 模拟 CMDB — 资源分类树（级联选择器用） |
| `esxi.py` | ESXi 主机 CMDB Mock | `cmdb_esxi_hosts()` — 模拟 CMDB — ESXi 主机列表 |
| `ip_pools.py` | IP 地址池 Mock — 供 IP 选择器动态模式使用 | `cmdb_ip_pools()` — 模拟 CMDB — IP 地址池（供 IP 选择器动态搜索使用） |
| `netapp.py` | NetApp ONTAP 集群 CMDB Mock | `cmdb_netapp_clusters()` — 模拟 CMDB — NetApp ONTAP 集群列表 |
| `pmax.py` | PowerMax 存储阵列 CMDB Mock | `cmdb_pmax_arrays()` — 模拟 CMDB — PowerMax 存储阵列列表 |
| `resources.py` | 主机资源 Mock — 供资源选择器使用，含集群/机房/型号信息 | `cmdb_resources()` — 模拟 CMDB — 主机资源列表，支持按集群分组和 q/ cluster 过滤 |
| `servers.py` | 服务器/BMC CMDB Mock — 供 Redfish 和 Monitor 插件使用 | `cmdb_servers()` — 模拟 CMDB — 物理服务器列表（含 BMC 地址） |
| `servicenow.py` | ServiceNow 实例 & Change Request Mock | `cmdb_servicenow_instances()` — 模拟 CMDB — ServiceNow 实例列表<br>`servicenow_change_requests()` — 模拟 ServiceNow — 变更申请(CR)列表 |
