"""ServiceNow 实例 CMDB Mock"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

MOCK_SERVICENOW_INSTANCES = [
    {"value": "https://prod.service-now.com",   "label": "ServiceNow PROD (prod.service-now.com)",   "env": "production"},
    {"value": "https://stag.service-now.com",   "label": "ServiceNow STAG (stag.service-now.com)",   "env": "staging"},
    {"value": "https://dev.service-now.com",     "label": "ServiceNow DEV (dev.service-now.com)",     "env": "development"},
    {"value": "https://sandbox.service-now.com", "label": "ServiceNow Sandbox (sandbox.service-now.com)", "env": "sandbox"},
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
