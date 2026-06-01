"""NetApp ONTAP 集群 CMDB Mock"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

MOCK_NETAPP_CLUSTERS = [
    {"value": "10.0.200.10", "label": "NetApp-PROD-01 (10.0.200.10)", "model": "AFF A800", "svm": "svm_prod_01"},
    {"value": "10.0.200.11", "label": "NetApp-PROD-02 (10.0.200.11)", "model": "AFF A800", "svm": "svm_prod_02"},
    {"value": "10.0.200.20", "label": "NetApp-STAG-01 (10.0.200.20)", "model": "FAS 8300", "svm": "svm_stag_01"},
    {"value": "10.0.200.30", "label": "NetApp-DEV-01 (10.0.200.30)",  "model": "FAS 2750", "svm": "svm_dev_01"},
    {"value": "10.0.200.40", "label": "NetApp-DR-01 (10.0.200.40)",   "model": "AFF A250", "svm": "svm_dr_01"},
]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cmdb_netapp_clusters(request):
    """模拟 CMDB — NetApp ONTAP 集群列表"""
    q = request.query_params.get('q', '').strip().lower()
    clusters = MOCK_NETAPP_CLUSTERS
    if q:
        clusters = [c for c in clusters if q in c['label'].lower() or q in c['value']]
    return Response({"code": 2000, "msg": "success", "data": clusters})
