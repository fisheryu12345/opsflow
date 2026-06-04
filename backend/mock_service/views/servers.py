"""服务器/BMC CMDB Mock — 供 Redfish 和 Monitor 插件使用"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

MOCK_SERVERS = [
    {"value": "bmc-prod-01.example.com", "label": "Server-PROD-01 (bmc-prod-01.example.com)", "rack": "A01", "model": "PowerEdge R750"},
    {"value": "bmc-prod-02.example.com", "label": "Server-PROD-02 (bmc-prod-02.example.com)", "rack": "A01", "model": "PowerEdge R750"},
    {"value": "bmc-prod-03.example.com", "label": "Server-PROD-03 (bmc-prod-03.example.com)", "rack": "A02", "model": "PowerEdge R650"},
    {"value": "10.0.100.10",            "label": "Server-DB-01 (10.0.100.10)",                "rack": "B01", "model": "PowerEdge R7525"},
    {"value": "10.0.100.11",            "label": "Server-DB-02 (10.0.100.11)",                "rack": "B01", "model": "PowerEdge R7525"},
    {"value": "bmc-stag-01.example.com", "label": "Server-STAG-01 (bmc-stag-01.example.com)", "rack": "C03", "model": "PowerEdge R650"},
    {"value": "bmc-dev-01.example.com",  "label": "Server-DEV-01 (bmc-dev-01.example.com)",   "rack": "D01", "model": "PowerEdge R450"},
    {"value": "bmc-dev-02.example.com",  "label": "Server-DEV-02 (bmc-dev-02.example.com)",   "rack": "D01", "model": "PowerEdge R450"},
    {"value": "172.16.0.100",           "label": "Server-DR-01 (172.16.0.100)",               "rack": "E05", "model": "PowerEdge R650"},
]


@api_view(['GET'])
@permission_classes([AllowAny])
def cmdb_servers(request):
    """模拟 CMDB — 物理服务器列表（含 BMC 地址）"""
    q = request.query_params.get('q', '').strip().lower()
    servers = MOCK_SERVERS
    if q:
        servers = [s for s in servers if q in s['label'].lower() or q in s['value']]
    return Response({"code": 2000, "msg": "success", "data": servers})
