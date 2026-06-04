# -*- coding: utf-8 -*-
"""Host management views (Neo4j)

主机 CRUD，操作 Neo4j 图数据库。
"""

from rest_framework.decorators import action
from rest_framework import status

from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from .base import Neo4jViewSet
from ..models.node_types import Host
from ..serializers import HostSerializer


class HostViewSet(Neo4jViewSet):
    """
    主机管理

    list: 查询主机列表
    create: 创建主机(自动关联到指定模块)
    update: 修改主机信息
    retrieve: 主机详情
    destroy: 删除主机
    batch_import: 批量导入主机
    """
    model_class = Host
    serializer_class = HostSerializer
    search_fields = ['hostname', 'ip']
    ordering = ['-created_at']

    def get_queryset(self):
        """支持按模块、状态过滤"""
        qs = Host.nodes.all()
        module_id = self.request.query_params.get('module_id')
        status_filter = self.request.query_params.get('status')
        os_filter = self.request.query_params.get('os_type')

        if module_id:
            from ..models.node_types import Module
            try:
                module = Module.nodes.get(module_id=module_id)
                host_ids = [h.host_id for h in module.hosts.all()]
                qs = [h for h in qs if h.host_id in host_ids]
            except Module.DoesNotExist:
                qs = []
        if status_filter:
            qs = [h for h in qs if h.status == status_filter]
        if os_filter:
            qs = [h for h in qs if h.os_type == os_filter]
        return qs

    @action(methods=['POST'], detail=False)
    def batch_import(self, request):
        """批量导入主机"""
        data = request.data
        if not isinstance(data, list):
            return ErrorResponse(msg='请传入主机列表')

        results = {'created': 0, 'errors': []}
        for item in data:
            try:
                host = Host(**{
                    'ip': item.get('ip'),
                    'hostname': item.get('hostname', ''),
                    'os_type': item.get('os_type', 'linux'),
                    'cpu_cores': item.get('cpu_cores', 0),
                    'memory_mb': item.get('memory_mb', 0),
                    'disk_gb': item.get('disk_gb', 0),
                }).save()
                results['created'] += 1
            except Exception as e:
                results['errors'].append({'ip': item.get('ip'), 'error': str(e)})

        return DetailResponse(data=results, msg=f"导入完成，成功 {results['created']} 台")
