"""PowerMax 存储阵列 CMDB Mock"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

MOCK_PMAX_ARRAYS = [
    {"value": "000197000001", "label": "PowerMax-PROD-01 (000197000001)", "model": "PowerMax 8000", "srp": "SRP_1"},
    {"value": "000197000002", "label": "PowerMax-PROD-02 (000197000002)", "model": "PowerMax 8000", "srp": "SRP_1"},
    {"value": "000197000003", "label": "PowerMax-DR-01 (000197000003)",   "model": "PowerMax 2000", "srp": "SRP_DR"},
    {"value": "000197000010", "label": "PowerMax-DEV-01 (000197000010)",  "model": "PowerMax 2000", "srp": "SRP_DEV"},
]


@api_view(['GET'])
@permission_classes([AllowAny])
def cmdb_pmax_arrays(request):
    """模拟 CMDB — PowerMax 存储阵列列表"""
    q = request.query_params.get('q', '').strip().lower()
    arrays = MOCK_PMAX_ARRAYS
    if q:
        arrays = [a for a in arrays if q in a['label'].lower() or q in a['value']]
    return Response({"code": 2000, "msg": "success", "data": arrays})
