# -*- coding: utf-8 -*-
"""Topology views — 拓扑查询、影响分析、全局搜索、AI 布局"""

import json
import logging
import re

from rest_framework import status
from rest_framework.decorators import action
from rest_framework import viewsets

from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..services.topology_service import TopologyService

logger = logging.getLogger(__name__)

# ── AI DR 布局 Prompt ────────────────────────────────────────

DR_LAYOUT_PROMPT = """你是拓扑图结构分析师。分析给定的 DR 拓扑数据，按以下规则输出行列布局：

布局结构（行号从 0 开始）：
- Row 0: DrSite 节点。主站 col=0，备站 col=5
- Row 1~N: 主备进程对。每行格式：[主站Host(col=1)] → [主站Process(col=2)]  [备站Process(col=3)] → [备站Host(col=4)]
- 每行放一个相同名称的进程对（同名进程主站和备站各一个）
- 主站 Host 和备站 Host 放在所在行的两端
- DrGroup 节点独占一行（独立于进程行），col=0~5 横跨整行居中。DrGroup 的行号用负数 -1 表示（后端自动计算中间位置）

行分配规则：
- 同名进程放在同一行（如主站 nginx 和备站 nginx 在同一行）
- 同行中主站 Process(col=2) 通过 RUNS_ON 边关联到主站 Host(col=1)
- 同行中备站 Process(col=3) 通过 RUNS_ON 边关联到备站 Host(col=4)

输出 JSON：
{
  "layout": [
    {"id": "节点ID", "col": 0-5, "row": 行号}
  ]
}

只输出 JSON。"""


class TopologyViewSet(viewsets.GenericViewSet):
    """
    拓扑视图（只读查询）

    list (graph): 全局力导向图数据
    tree: 业务拓扑树
    impact: 影响分析
    search: 全局搜索
    """
    serializer_class = None

    def list(self, request):
        """全局力导向图数据 — 所有节点+关系"""
        service = TopologyService()
        data = service.full_topology()
        return DetailResponse(data=data)

    @action(methods=['GET'], detail=False)
    def tree(self, request):
        """业务拓扑树"""
        root_id = request.query_params.get('root_id')
        if not root_id:
            return ErrorResponse(msg='请提供 root_id')
        depth = int(request.query_params.get('depth', 5))
        rel_types = request.query_params.getlist('rel_types') or None

        service = TopologyService()
        data = service.get_tree(root_id, rel_types=rel_types, max_depth=depth)
        return DetailResponse(data=data)

    @action(methods=['GET'], detail=False)
    def impact(self, request):
        """影响分析"""
        node_id = request.query_params.get('node_id')
        if not node_id:
            return ErrorResponse(msg='请提供 node_id')

        direction = request.query_params.get('direction', 'downstream')
        depth = int(request.query_params.get('depth', 5))

        service = TopologyService()
        data = service.get_impact(node_id, direction=direction, max_depth=depth)
        return DetailResponse(data=data)

    @action(methods=['POST'], detail=False)
    def dr_layout(self, request):
        """AI 计算 DR 拓扑节点位置 — 基于拓扑关系和布局规则"""
        nodes = request.data.get('nodes', [])
        edges = request.data.get('edges', [])
        if not nodes:
            return ErrorResponse(msg='nodes is required', code=4000)

        try:
            from integration.services.connector_service import get_ai_connector_or_raise
            connector = get_ai_connector_or_raise()

            topology = {
                "nodes": [{"id": n["id"], "type": n.get("type", ""), "label": n.get("label", "")} for n in nodes],
                "edges": [{"from": e.get("from", e.get("source", "")), "to": e.get("to", e.get("target", "")), "type": e.get("type", "")} for e in edges],
            }

            result = connector.chat(
                messages=[
                    {"role": "system", "content": DR_LAYOUT_PROMPT},
                    {"role": "user", "content": json.dumps(topology, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            text = result.get("content", "{}") or "{}"
            text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
            result = json.loads(text)
            raw = result.get("layout") or result.get("positions", [])
            # Convert col/row grid to pixel coordinates
            COL_X = {0: 40, 1: 280, 2: 520, 3: 760, 4: 1000, 5: 1240}
            ROW_H = 70
            DRGROUP_ROW_GAP = 60  # extra gap around DrGroup

            # Separate DrGroup (row=-1) from other nodes
            normal = [i for i in raw if i.get("row", 0) >= 0]
            drgroup = [i for i in raw if i.get("row", -1) < 0]

            # Find middle row index for DrGroup
            max_row = max((i.get("row", 0) for i in normal), default=0)
            mid_row = max_row // 2 + 1  # insert after middle

            positions = []
            for item in normal:
                col = item.get("col", 1)
                row = item.get("row", 0)
                # Shift rows after mid_row to make room for DrGroup
                y_offset = DRGROUP_ROW_GAP if row >= mid_row else 0
                x = COL_X.get(col, 80 + col * 150)
                y = 60 + row * ROW_H + y_offset
                positions.append({"id": item["id"], "x": x, "y": y})

            # Place DrGroup at mid_row, horizontally centered across full width
            for item in drgroup:
                x = (COL_X[0] + COL_X[5]) // 2  # center across entire layout
                y = 60 + mid_row * ROW_H
                positions.append({"id": item["id"], "x": x, "y": y})
            return DetailResponse(data={"positions": positions})
        except Exception as e:
            logger.exception("AI DR layout failed")
            return ErrorResponse(msg=str(e), code=4000, status=400)

    @action(methods=['GET'], detail=False)
    def search(self, request):
        """全局搜索"""
        query = request.query_params.get('q', '')
        if not query:
            return ErrorResponse(msg='请提供搜索关键词 q')

        model_codes = request.query_params.getlist('model_codes') or None
        limit = int(request.query_params.get('limit', 50))

        service = TopologyService()
        results = service.global_search(query, model_codes=model_codes, limit=limit)
        return DetailResponse(data=results)
