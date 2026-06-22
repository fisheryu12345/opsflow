# -*- coding: utf-8 -*-
"""阿里云 ECS 资源查询 API — 供表单 async_select 动态加载数据"""

import json
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def _get_client(region):
    """获取 Aliyun ECS 客户端"""
    from opsflow.plugins.aliyun_ecs._client import get_ecs_client
    return get_ecs_client(region)


def _describe_all_types(client) -> dict:
    from aliyunsdkecs.request.v20140526.DescribeInstanceTypesRequest import DescribeInstanceTypesRequest
    req = DescribeInstanceTypesRequest()
    body = client.do_action_with_exception(req)
    data = json.loads(body)
    type_map = {}
    for t in data.get('InstanceTypes', {}).get('InstanceType', []):
        tid = t.get('InstanceTypeId', '')
        if tid:
            type_map[tid] = t
    return type_map


@api_view(['GET'])
@permission_classes([AllowAny])
def describe_images(request):
    region = request.GET.get('region', '')
    if not region:
        return Response({"code": 2000, "data": []})
    try:
        client = _get_client(region)
        from aliyunsdkecs.request.v20140526.DescribeImagesRequest import DescribeImagesRequest
        req = DescribeImagesRequest()
        req.set_ImageOwnerAlias('self')
        req.set_Status('Available')
        req.set_PageSize(100)
        body = client.do_action_with_exception(req)
        data = json.loads(body)
        req2 = DescribeImagesRequest()
        req2.set_ImageOwnerAlias('system')
        req2.set_Status('Available')
        req2.set_PageSize(100)
        body2 = client.do_action_with_exception(req2)
        data2 = json.loads(body2)
        images = (data.get('Images', {}).get('Image', []) + data2.get('Images', {}).get('Image', []))
        seen = set()
        result = []
        for img in images:
            iid = img.get('ImageId', '')
            if iid and iid not in seen:
                seen.add(iid)
                result.append({"label": f"{img.get('ImageName', '')} ({iid})", "value": iid})
        return Response({"code": 2000, "data": result})
    except Exception as e:
        logger.exception("describe_images failed")
        return Response({"code": 4000, "data": [], "msg": str(e)})


@api_view(['GET'])
@permission_classes([AllowAny])
def describe_instance_types(request):
    region = request.GET.get('region', '')
    zone_id = request.GET.get('zone_id', '')
    if not region:
        return Response({"code": 2000, "data": []})
    try:
        client = _get_client(region)
        if zone_id:
            from aliyunsdkecs.request.v20140526.DescribeAvailableResourceRequest import DescribeAvailableResourceRequest
            req = DescribeAvailableResourceRequest()
            req.set_DestinationResource('InstanceType')
            req.set_ZoneId(zone_id)
            body = client.do_action_with_exception(req)
            data = json.loads(body)
            seen = set()
            available_ids = []
            for zone in data.get('AvailableZones', {}).get('AvailableZone', []) or []:
                for res in zone.get('AvailableResources', {}).get('AvailableResource', []) or []:
                    for sr in res.get('SupportedResources', {}).get('SupportedResource', []) or []:
                        val = sr.get('Value', '')
                        if val and val not in seen and sr.get('Status', '') == 'Available':
                            seen.add(val)
                            available_ids.append(val)
            type_map = _describe_all_types(client)
            result = []
            for tid in available_ids:
                t = type_map.get(tid)
                if t:
                    result.append({"label": f"{tid} ({t.get('CpuCoreCount', '?')}vCPU {t.get('MemorySize', '?')}GB)", "value": tid})
                else:
                    result.append({"label": tid, "value": tid})
        else:
            types_data = _describe_all_types(client)
            result = [{"label": f"{tid} ({t.get('CpuCoreCount', 0)}vCPU {t.get('MemorySize', 0)}GB)", "value": tid} for tid, t in types_data.items()]
        return Response({"code": 2000, "data": result})
    except Exception as e:
        logger.exception("describe_instance_types failed")
        return Response({"code": 4000, "data": [], "msg": str(e)})


@api_view(['GET'])
@permission_classes([AllowAny])
def describe_security_groups(request):
    region = request.GET.get('region', '')
    if not region:
        return Response({"code": 2000, "data": []})
    try:
        client = _get_client(region)
        from aliyunsdkecs.request.v20140526.DescribeSecurityGroupsRequest import DescribeSecurityGroupsRequest
        req = DescribeSecurityGroupsRequest()
        req.set_PageSize(100)
        body = client.do_action_with_exception(req)
        data = json.loads(body)
        groups = data.get('SecurityGroups', {}).get('SecurityGroup', [])
        result = [{"label": f"{g.get('SecurityGroupName', '')} ({g.get('SecurityGroupId', '')})", "value": g.get('SecurityGroupId', '')} for g in groups if g.get('SecurityGroupId')]
        return Response({"code": 2000, "data": result})
    except Exception as e:
        logger.exception("describe_security_groups failed")
        return Response({"code": 4000, "data": [], "msg": str(e)})


@api_view(['GET'])
@permission_classes([AllowAny])
def describe_vswitches(request):
    region = request.GET.get('region', '')
    zone_id = request.GET.get('zone_id', '')
    if not region:
        return Response({"code": 2000, "data": []})
    try:
        client = _get_client(region)
        from aliyunsdkecs.request.v20140526.DescribeVSwitchesRequest import DescribeVSwitchesRequest
        req = DescribeVSwitchesRequest()
        if zone_id:
            req.set_ZoneId(zone_id)
        body = client.do_action_with_exception(req)
        data = json.loads(body)
        switches = data.get('VSwitches', {}).get('VSwitch', [])
        result = [{"label": f"{s.get('VSwitchName', '')} ({s.get('VSwitchId', '')}) {s.get('ZoneId', '')}", "value": s.get('VSwitchId', '')} for s in switches if s.get('VSwitchId')]
        return Response({"code": 2000, "data": result})
    except Exception as e:
        logger.exception("describe_vswitches failed")
        return Response({"code": 4000, "data": [], "msg": str(e)})


@api_view(['GET'])
@permission_classes([AllowAny])
def describe_regions(request):
    try:
        client = _get_client('cn-hangzhou')
        from aliyunsdkecs.request.v20140526.DescribeRegionsRequest import DescribeRegionsRequest
        req = DescribeRegionsRequest()
        body = client.do_action_with_exception(req)
        data = json.loads(body)
        regions = data.get('Regions', {}).get('Region', [])
        result = [{"label": f"{r.get('LocalName', '')} ({r.get('RegionId', '')})", "value": r.get('RegionId', '')} for r in regions if r.get('RegionId')]
        return Response({"code": 2000, "data": result})
    except Exception as e:
        logger.exception("describe_regions failed")
        return Response({"code": 4000, "data": [], "msg": str(e)})


@api_view(['GET'])
@permission_classes([AllowAny])
def describe_zones(request):
    region = request.GET.get('region', '')
    if not region:
        return Response({"code": 2000, "data": []})
    try:
        client = _get_client(region)
        from aliyunsdkecs.request.v20140526.DescribeZonesRequest import DescribeZonesRequest
        req = DescribeZonesRequest()
        body = client.do_action_with_exception(req)
        data = json.loads(body)
        zones = data.get('Zones', {}).get('Zone', [])
        result = [{"label": f"{z.get('LocalName', '')} ({z.get('ZoneId', '')})", "value": z.get('ZoneId', '')} for z in zones if z.get('ZoneId')]
        return Response({"code": 2000, "data": result})
    except Exception as e:
        logger.exception("describe_zones failed")
        return Response({"code": 4000, "data": [], "msg": str(e)})


@api_view(['GET'])
@permission_classes([AllowAny])
def describe_disk_categories(request):
    region = request.GET.get('region', '')
    instance_type = request.GET.get('instance_type', '')
    if not region or not instance_type:
        return Response({"code": 2000, "data": []})
    try:
        client = _get_client(region)
        from aliyunsdkecs.request.v20140526.DescribeAvailableResourceRequest import DescribeAvailableResourceRequest
        req = DescribeAvailableResourceRequest()
        req.set_DestinationResource('SystemDisk')
        req.set_InstanceType(instance_type)
        body = client.do_action_with_exception(req)
        data = json.loads(body)
        zones = data.get('AvailableZones', {}).get('AvailableZone', []) or []
        seen = set()
        result = []
        label_map = {'cloud': '普通云盘', 'cloud_ssd': 'SSD 云盘', 'cloud_efficiency': '高效云盘', 'cloud_essd': 'ESSD 云盘', 'cloud_essd_entry': 'ESSD Entry'}
        for zone in zones:
            for res in (zone.get('AvailableResources', {}).get('AvailableResource', []) or []):
                for cat in (res.get('SupportedResources', {}).get('SupportedResource', []) or []):
                    val = cat.get('Value', '')
                    if val and val not in seen and cat.get('Status', '') == 'Available':
                        seen.add(val)
                        result.append({"label": f"{val} - {label_map.get(val, val)}", "value": val})
        if not result:
            result = [{"label": "cloud_essd - ESSD 云盘", "value": "cloud_essd"}, {"label": "cloud_ssd - SSD 云盘", "value": "cloud_ssd"}, {"label": "cloud_efficiency - 高效云盘", "value": "cloud_efficiency"}]
        return Response({"code": 2000, "data": result})
    except Exception as e:
        logger.exception("describe_disk_categories failed")
        return Response({"code": 2000, "data": [{"label": "cloud_essd - ESSD 云盘", "value": "cloud_essd"}, {"label": "cloud_ssd - SSD 云盘", "value": "cloud_ssd"}, {"label": "cloud_efficiency - 高效云盘", "value": "cloud_efficiency"}]})


@api_view(['GET'])
@permission_classes([AllowAny])
def describe_cmdb_instances(request):
    """从 CMDB 查询阿里云实例列表 — 供 delete/start/stop 等原子选择"""
    try:
        from cmdb.services.neo4j_client import graph_driver
        with graph_driver.session() as session:
            result = session.run(
                "MATCH (h:Host {cloud_type: 'aliyun'}) "
                "RETURN h.cloud_instance_id AS cid, h.hostname, h.ip, h.status "
                "ORDER BY h.hostname"
            )
            items = []
            for rec in result:
                cid = rec.get('cid', '')
                hostname = rec.get('hostname', '') or ''
                ip = rec.get('ip', '') or ''
                status = rec.get('status', '')
                label = f"{hostname} ({ip}, {status})" if ip else f"{hostname} ({cid})"
                if cid:
                    items.append({"label": label, "value": cid})
            return Response({"code": 2000, "data": items})
    except Exception as e:
        logger.exception("describe_cmdb_instances failed")
        return Response({"code": 4000, "data": [], "msg": str(e)})
