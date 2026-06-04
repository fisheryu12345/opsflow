"""分类树 Mock — 供级联选择器使用（数据中心→机柜→设备类型→实例）"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

MOCK_CATEGORIES = [
    {
        "value": "dc-beijing",
        "label": "北京数据中心",
        "children": [
            {
                "value": "dc-bj-rack-a",
                "label": "A列机柜",
                "children": [
                    {"value": "dc-bj-a-web", "label": "Web服务器",
                     "children": [
                         {"value": "web-bj-a-01", "label": "web-bj-a-01"},
                         {"value": "web-bj-a-02", "label": "web-bj-a-02"},
                     ]},
                    {"value": "dc-bj-a-db", "label": "数据库服务器",
                     "children": [
                         {"value": "db-bj-a-01", "label": "db-bj-a-01"},
                     ]},
                ],
            },
            {
                "value": "dc-bj-rack-b",
                "label": "B列机柜",
                "children": [
                    {"value": "dc-bj-b-lb", "label": "负载均衡",
                     "children": [
                         {"value": "lb-bj-b-01", "label": "lb-bj-b-01"},
                         {"value": "lb-bj-b-02", "label": "lb-bj-b-02"},
                     ]},
                ],
            },
        ],
    },
    {
        "value": "dc-shanghai",
        "label": "上海数据中心",
        "children": [
            {
                "value": "dc-sh-rack-c",
                "label": "C列机柜",
                "children": [
                    {"value": "dc-sh-c-web", "label": "Web服务器",
                     "children": [
                         {"value": "web-sh-c-01", "label": "web-sh-c-01"},
                     ]},
                ],
            },
        ],
    },
    {
        "value": "dc-dr",
        "label": "灾备数据中心",
        "children": [
            {
                "value": "dc-dr-rack-e",
                "label": "E列机柜",
                "children": [
                    {"value": "dc-dr-e-node", "label": "灾备节点",
                     "children": [
                         {"value": "dr-e-01", "label": "dr-e-01"},
                         {"value": "dr-e-02", "label": "dr-e-02"},
                     ]},
                ],
            },
        ],
    },
]


@api_view(['GET'])
@permission_classes([AllowAny])
def cmdb_categories(request):
    """模拟 CMDB — 资源分类树（级联选择器用）"""
    return Response({"code": 2000, "msg": "success", "data": MOCK_CATEGORIES})
