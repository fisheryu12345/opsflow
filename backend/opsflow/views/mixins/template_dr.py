"""Template DR — AI 生成 DR 切换 Pipeline 端点

入口: CreateTemplateWizard Step 2 新增「DR 切换」选项
流程:
  1. 接收 dr_group_id
  2. 查询 Neo4j → DrGroup + 关联的 Process + CALLS 拓扑
  3. 构建拓扑描述 → 调用 LLM → 生成 DR pipeline
  4. 保存为草稿模板 → 返回

Service 层: opsflow.services.dr_service
"""
import json
import logging
import re

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from opsflow.services.dr_service import (
    DR_SYSTEM_PROMPT,
    get_dr_group_topology,
    build_topology_description,
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preview_dr_topology(request):
    """预览 DR 组拓扑 — 返回结构化的主站/备站进程 + CALLS 关系

    输入: {"dr_group_id": "xxx"}
    输出: {primary: [{name, host, id}], standby: [...], calls: [{from, to}]}
    """
    dr_group_id = request.data.get("dr_group_id", "")
    if not dr_group_id:
        return ErrorResponse(msg="dr_group_id is required", code=4000)

    topology = get_dr_group_topology(dr_group_id)
    applications = topology.get("applications", [])
    calls = topology.get("calls", [])

    # 去重
    seen = set()
    unique_apps = []
    for a in applications:
        aid = a.get("instance_id", "")
        if aid and aid not in seen:
            seen.add(aid)
            unique_apps.append(a)

    primary = []
    standby = []
    for a in unique_apps:
        aname = str(a.get("name", "unknown"))
        host_ip = str(a.get("host_ip", "") or "")
        entry = {
            "id": a.get("instance_id", "")[:12],
            "name": aname,
            "host": host_ip,
            "status": a.get("status", ""),
        }
        if aname.endswith("_cont"):
            standby.append(entry)
        elif "dr" in host_ip.lower():
            standby.append(entry)
        else:
            primary.append(entry)

    # 建立 app_id → app 查找表（含 listen 端口信息）
    app_map = {}
    for a in unique_apps:
        aid = a.get("instance_id", "")
        aname = a.get("name", "unknown")
        addrs = a.get("listen_addrs", [])
        ports = ",".join(str(addr.get("port", "")) for addr in addrs if addr.get("port"))
        port_str = f":{ports}" if ports else ""
        host_ip = a.get("host_ip", "") or ""
        host_tag = host_ip.split(".")[-1] if host_ip else ""
        app_map[aid] = f"{aname}{port_str}({host_tag})"

    # 去重 CALLS
    dr_group_ids = {a.get("instance_id", "") for a in unique_apps}
    seen_calls = set()
    unique_calls = []
    for c in calls:
        src = c.get("from", "")
        dst = c.get("to", "")
        if src not in dr_group_ids or dst not in dr_group_ids:
            continue
        key = (src, dst)
        if key not in seen_calls:
            seen_calls.add(key)
            unique_calls.append({
                "from": app_map.get(src, src[:12]),
                "to": app_map.get(dst, dst[:12]),
            })

    return DetailResponse(data={
        "primary": primary,
        "standby": standby,
        "calls": unique_calls,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_dr_pipeline(request):
    """AI 生成 DR 切换 Pipeline

    输入: {"dr_group_id": "xxx"}
    输出: {pipeline_tree, name, description}
    """
    dr_group_id = request.data.get("dr_group_id", "")
    if not dr_group_id:
        return ErrorResponse(msg="dr_group_id is required", code=4000)

    # resolve project from request
    from opsflow.views.base import ProjectFilteredViewSet
    project_kwargs = ProjectFilteredViewSet.resolve_project_kwargs(request)

    # 1. 查询 Neo4j 拓扑
    topology = get_dr_group_topology(dr_group_id)
    applications = topology.get("applications", [])
    if not topology or not applications:
        logger.warning("[DR] No applications found for DrGroup=%s, topology=%s", dr_group_id, topology)
        return ErrorResponse(msg=f"DR 组未找到或未关联应用（共 {len(applications)} 个应用）", code=4000)

    topology_desc = build_topology_description(topology)
    logger.info("[DR] Topology for DrGroup=%s: %d applications, topology_desc length=%d",
                dr_group_id, len(applications), len(topology_desc))

    # 2. 调用 LLM 生成 DR pipeline
    try:
        from opsflow.core.llm_service import _get_llm_client
        connector = _get_llm_client()

        messages = [
            {"role": "system", "content": DR_SYSTEM_PROMPT},
            {"role": "user", "content": f"请为以下 DR 组生成切换 Pipeline：\n\n{topology_desc}"},
        ]
        result = connector.chat(
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        text = result.get('content') or "{}"
        text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
        pipeline = json.loads(text)

        # 兼容 AI 的 pipeline.stages 格式 → 转为标准 nodes/edges
        raw_nodes = pipeline.get("nodes") or []
        raw_edges = pipeline.get("edges") or []
        if not raw_nodes and "pipeline" in pipeline:
            pipeline_inner = pipeline["pipeline"]
            stages = pipeline_inner.get("stages") or []
            prev_id = None
            for stage in stages:
                for node in stage.get("nodes", []):
                    nid = node.get("id") or node.get("node_id", "")
                    ntype = node.get("type", "")
                    label = node.get("label") or stage.get("name", "")
                    params = node.get("params", {})
                    raw_nodes.append({
                        "id": nid, "label": label,
                        "node_type": "", "atom_type": ntype,
                        "params": params,
                    })
                    if prev_id:
                        raw_edges.append({"from": prev_id, "to": nid, "label": "success"})
                    prev_id = nid
                if stage.get("next"):
                    for next_nid in stage["next"]:
                        raw_edges.append({"from": prev_id, "to": next_nid, "label": "success"})
            pipeline = {"nodes": raw_nodes, "edges": raw_edges}

        # 3. enrich + validate pipeline（与 create_from_ai 一致）
        from opsflow.views.mixins.template_ai import _enrich_atom_nodes
        from opsflow.core.safety_guard import validate_pipeline
        from opsflow.core.bamboo_validator import validate_bamboo_compatibility

        _enrich_atom_nodes(pipeline)
        validation = validate_pipeline(pipeline)
        bamboo_check = validate_bamboo_compatibility(pipeline)

        # 4. 创建草稿模板
        from opsflow.models import FlowTemplate
        from opsflow.serializers import FlowTemplateSerializer

        group_name = topology.get("dr_group", {}).get("name", "unknown")
        template = FlowTemplate.objects.create(
            name=f"DR切换: {group_name}",
            pipeline_tree=pipeline,
            description=topology_desc[:200],
            ai_original_tree=pipeline.copy(),
            is_draft=True,
            created_by=request.user,
            **project_kwargs,
        )

        logger.info("[DR] Pipeline created for DrGroup=%s template=%s", dr_group_id, template.id)
        return DetailResponse(data={
            "template": FlowTemplateSerializer(template).data,
            "pipeline_tree": pipeline,
            "topology": topology_desc,
            "bamboo_check": bamboo_check,
        })

    except json.JSONDecodeError as e:
        return ErrorResponse(msg=f"AI 返回格式错误: {e}", code=4000)
    except Exception as e:
        logger.exception("[DR] create_dr_pipeline failed")
        return ErrorResponse(msg=str(e), code=4000, status=400)
