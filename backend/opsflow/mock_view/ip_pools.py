"""IP 地址池 Mock — 供 IP 选择器动态模式使用"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

MOCK_IP_POOLS = [
    {"value": "10.0.1.1",   "label": "web-01 (10.0.1.1)",   "tag": "web",   "subnet": "10.0.1.0/24"},
    {"value": "10.0.1.2",   "label": "web-02 (10.0.1.2)",   "tag": "web",   "subnet": "10.0.1.0/24"},
    {"value": "10.0.1.3",   "label": "web-03 (10.0.1.3)",   "tag": "web",   "subnet": "10.0.1.0/24"},
    {"value": "10.0.2.1",   "label": "db-01 (10.0.2.1)",    "tag": "db",    "subnet": "10.0.2.0/24"},
    {"value": "10.0.2.2",   "label": "db-02 (10.0.2.2)",    "tag": "db",    "subnet": "10.0.2.0/24"},
    {"value": "10.0.3.1",   "label": "lb-01 (10.0.3.1)",    "tag": "lb",    "subnet": "10.0.3.0/24"},
    {"value": "10.0.3.2",   "label": "lb-02 (10.0.3.2)",    "tag": "lb",    "subnet": "10.0.3.0/24"},
    {"value": "10.0.10.10", "label": "monitor-01 (10.0.10.10)", "tag": "mon", "subnet": "10.0.10.0/24"},
    {"value": "10.0.10.11", "label": "backup-01 (10.0.10.11)",  "tag": "bak", "subnet": "10.0.10.0/24"},
    {"value": "192.168.1.10", "label": "dev-01 (192.168.1.10)", "tag": "dev", "subnet": "192.168.1.0/24"},
    {"value": "192.168.1.11", "label": "dev-02 (192.168.1.11)", "tag": "dev", "subnet": "192.168.1.0/24"},
    {"value": "172.16.0.1",   "label": "dr-01 (172.16.0.1)",   "tag": "dr",  "subnet": "172.16.0.0/16"},
]


@api_view(['GET'])
@permission_classes([AllowAny])
def cmdb_ip_pools(request):
    """模拟 CMDB — IP 地址池（供 IP 选择器动态搜索使用）"""
    q = request.query_params.get('q', '').strip().lower()
    tag = request.query_params.get('tag', '').strip().lower()
    results = MOCK_IP_POOLS
    if q:
        results = [r for r in results if q in r['label'].lower() or q in r['value']]
    if tag:
        results = [r for r in results if r['tag'] == tag]
    return Response({"code": 2000, "msg": "success", "data": results})
