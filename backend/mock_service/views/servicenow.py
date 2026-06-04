"""ServiceNow 实例 & Change Request Mock"""

from datetime import datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

MOCK_SERVICENOW_INSTANCES = [
    {"value": "https://prod.service-now.com",   "label": "ServiceNow PROD (prod.service-now.com)",   "env": "production"},
    {"value": "https://stag.service-now.com",   "label": "ServiceNow STAG (stag.service-now.com)",   "env": "staging"},
    {"value": "https://dev.service-now.com",     "label": "ServiceNow DEV (dev.service-now.com)",     "env": "development"},
    {"value": "https://sandbox.service-now.com", "label": "ServiceNow Sandbox (sandbox.service-now.com)", "env": "sandbox"},
]

MOCK_CHANGE_REQUESTS = [
    {
        "cr_number": "CHG0012345",
        "title": "Upgrade ESXi 8.0 - Production Cluster A",
        "description": "对生产环境 A 集群执行 ESXi 8.0 升级，涉及 8 台物理主机。包含预检查、VM 迁移、固件升级、重启、验证恢复。",
        "status": "approved",
        "change_window_start": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
        "change_window_end": (datetime.now() + timedelta(days=1, hours=8)).strftime("%Y-%m-%d %H:%M"),
        "requester": "zhangsan",
    },
    {
        "cr_number": "CHG0012346",
        "title": "NetApp Storage Expansion - DR Site",
        "description": "对灾备站点的 NetApp 存储进行扩容，新增 4 个卷，总容量 20TB。",
        "status": "pending",
        "change_window_start": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
        "change_window_end": (datetime.now() + timedelta(days=3, hours=4)).strftime("%Y-%m-%d %H:%M"),
        "requester": "lisi",
    },
    {
        "cr_number": "CHG0012347",
        "title": "PowerMax Firmware Update",
        "description": "对生产存储阵列 PowerMax 执行固件升级，版本 5978 → 6079。",
        "status": "approved",
        "change_window_start": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d %H:%M"),
        "change_window_end": (datetime.now() + timedelta(days=4, hours=6)).strftime("%Y-%m-%d %H:%M"),
        "requester": "wangwu",
    },
    {
        "cr_number": "CHG0012348",
        "title": "Network Switch Replace - Core 01",
        "description": "更换核心交换机 Core-01，涉及全网路由收敛，影响所有业务系统。",
        "status": "approved",
        "change_window_start": (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d %H:%M"),
        "change_window_end": (datetime.now() + timedelta(days=6, hours=10)).strftime("%Y-%m-%d %H:%M"),
        "requester": "zhangsan",
    },
    {
        "cr_number": "CHG0012349",
        "title": "Database Security Patch - MySQL 8.0",
        "description": "对生产 MySQL 8.0 集群应用季度安全补丁，涉及 3 组主从复制。",
        "status": "pending",
        "change_window_start": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
        "change_window_end": (datetime.now() + timedelta(days=2, hours=3)).strftime("%Y-%m-%d %H:%M"),
        "requester": "zhaoliu",
    },
    {
        "cr_number": "CHG0012350",
        "title": "SSL Certificate Rotation - *.example.com",
        "description": "轮换泛域名 SSL 证书，涉及 Nginx 网关、K8s Ingress、CDN 配置更新。",
        "status": "approved",
        "change_window_start": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
        "change_window_end": (datetime.now() + timedelta(days=5, hours=2)).strftime("%Y-%m-%d %H:%M"),
        "requester": "lisi",
    },
]


@api_view(['GET'])
@permission_classes([AllowAny])
def cmdb_servicenow_instances(request):
    """模拟 CMDB — ServiceNow 实例列表"""
    q = request.query_params.get('q', '').strip().lower()
    instances = MOCK_SERVICENOW_INSTANCES
    if q:
        instances = [i for i in instances if q in i['label'].lower() or q in i['value']]
    return Response({"code": 2000, "msg": "success", "data": instances})


@api_view(['GET'])
@permission_classes([AllowAny])
def servicenow_change_requests(request):
    """模拟 ServiceNow — 变更申请(CR)列表"""
    q = request.query_params.get('q', '').strip().lower()
    status_filter = request.query_params.get('status', '').strip().lower()
    items = MOCK_CHANGE_REQUESTS
    if q:
        items = [c for c in items if q in c['cr_number'].lower() or q in c['title'].lower()]
    if status_filter:
        items = [c for c in items if c['status'] == status_filter]
    return Response({"code": 2000, "msg": "success", "data": items})
