"""主机资源 Mock — 供资源选择器使用，含集群/机房/型号信息"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

MOCK_CLUSTERS = {
    "生产-Web集群": [
        {"value": "web-prod-01", "label": "web-prod-01", "ip": "10.0.1.1",  "rack": "A01", "model": "R750"},
        {"value": "web-prod-02", "label": "web-prod-02", "ip": "10.0.1.2",  "rack": "A01", "model": "R750"},
        {"value": "web-prod-03", "label": "web-prod-03", "ip": "10.0.1.3",  "rack": "A02", "model": "R650"},
    ],
    "生产-DB集群": [
        {"value": "db-prod-01", "label": "db-prod-01", "ip": "10.0.2.1",   "rack": "B01", "model": "R7525"},
        {"value": "db-prod-02", "label": "db-prod-02", "ip": "10.0.2.2",   "rack": "B01", "model": "R7525"},
    ],
    "生产-LB集群": [
        {"value": "lb-prod-01", "label": "lb-prod-01", "ip": "10.0.3.1",   "rack": "A03", "model": "R450"},
        {"value": "lb-prod-02", "label": "lb-prod-02", "ip": "10.0.3.2",   "rack": "A03", "model": "R450"},
    ],
    "开发集群": [
        {"value": "web-dev-01",  "label": "web-dev-01",  "ip": "192.168.1.10", "rack": "D01", "model": "R450"},
        {"value": "db-dev-01",   "label": "db-dev-01",   "ip": "192.168.1.11", "rack": "D01", "model": "R450"},
    ],
    "灾备集群": [
        {"value": "dr-node-01", "label": "dr-node-01", "ip": "172.16.0.1",   "rack": "E05", "model": "R650"},
        {"value": "dr-node-02", "label": "dr-node-02", "ip": "172.16.0.2",   "rack": "E05", "model": "R650"},
    ],
}


def _flatten_resources():
    """将集群分组数据打平为列表，每条携带 cluster 信息"""
    result = []
    for cluster, hosts in MOCK_CLUSTERS.items():
        for h in hosts:
            result.append({**h, "cluster": cluster})
    return result


ALL_RESOURCES = _flatten_resources()


@api_view(['GET'])
@permission_classes([AllowAny])
def cmdb_resources(request):
    """模拟 CMDB — 主机资源列表，支持按集群分组和 q/ cluster 过滤"""
    q = request.query_params.get('q', '').strip().lower()
    cluster = request.query_params.get('cluster', '').strip()

    results = ALL_RESOURCES
    if q:
        results = [r for r in results if q in r['label'].lower() or q in r['ip']]
    if cluster:
        results = [r for r in results if r['cluster'] == cluster]

    # 如果请求 group_by=cluster，返回分组格式
    if request.query_params.get('group_by') == 'cluster':
        groups = {}
        for r in results:
            groups.setdefault(r['cluster'], []).append(r)
        grouped = [{"label": k, "value": k, "children": v} for k, v in groups.items()]
        return Response({"code": 2000, "msg": "success", "data": grouped})

    return Response({"code": 2000, "msg": "success", "data": results})
