"""ESXi 主机 CMDB Mock"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

MOCK_ESXI_HOSTS = [
    {"value": "192.168.1.10", "label": "esxi-prod-01 (192.168.1.10)", "datacenter": "BJ-IDC", "cluster": "PROD"},
    {"value": "192.168.1.11", "label": "esxi-prod-02 (192.168.1.11)", "datacenter": "BJ-IDC", "cluster": "PROD"},
    {"value": "192.168.1.12", "label": "esxi-prod-03 (192.168.1.12)", "datacenter": "BJ-IDC", "cluster": "PROD"},
    {"value": "192.168.2.10", "label": "esxi-stag-01 (192.168.2.10)", "datacenter": "BJ-IDC", "cluster": "STAGING"},
    {"value": "192.168.2.11", "label": "esxi-stag-02 (192.168.2.11)", "datacenter": "BJ-IDC", "cluster": "STAGING"},
    {"value": "10.0.1.20",    "label": "esxi-dev-01 (10.0.1.20)",      "datacenter": "SH-IDC", "cluster": "DEV"},
    {"value": "10.0.1.21",    "label": "esxi-dev-02 (10.0.1.21)",      "datacenter": "SH-IDC", "cluster": "DEV"},
    {"value": "172.16.0.50",  "label": "esxi-dr-01 (172.16.0.50)",     "datacenter": "SZ-IDC", "cluster": "DR"},
    {"value": "172.16.0.51",  "label": "esxi-dr-02 (172.16.0.51)",     "datacenter": "SZ-IDC", "cluster": "DR"},
]


@api_view(['GET'])
@permission_classes([AllowAny])
def cmdb_esxi_hosts(request):
    """模拟 CMDB — ESXi 主机列表"""
    q = request.query_params.get('q', '').strip().lower()
    hosts = MOCK_ESXI_HOSTS
    if q:
        hosts = [h for h in hosts if q in h['label'].lower() or q in h['value']]
    return Response({"code": 2000, "msg": "success", "data": hosts})
