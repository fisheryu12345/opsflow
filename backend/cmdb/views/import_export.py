# -*- coding: utf-8 -*-
"""ImportExportViewSet — CMDB Excel 导入导出 API

提供模型实例的 Excel(.xlsx) 导出导入功能。
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action

from common.utils.json_response import DetailResponse, ErrorResponse

from ..services.import_service import ImportService

logger = logging.getLogger(__name__)

FSM = 'import_export'


class ImportExportViewSet(viewsets.GenericViewSet):
    """
    CMDB Excel 导入导出

    export: POST /api/cmdb/instances/{model_code}/export/ — 导出为 Excel
    import_data: POST /api/cmdb/instances/{model_code}/import/ — 从 Excel 导入
    """
    serializer_class = None  # 无需序列化器

    def get_model_code(self):
        return self.kwargs.get('model_code')

    @action(detail=False, methods=['post'], url_path='export')
    def export(self, request, **kwargs):
        """导出实例到 Excel

        POST /api/cmdb/instances/{model_code}/export/
        Body: {filters: {field: value, ...}} (可选)
        Returns: .xlsx 文件
        """
        model_code = self.get_model_code()
        filters = request.data.get('filters', {})

        svc = ImportService()
        try:
            excel_data = svc.export_to_excel(model_code, filters)
            from django.http import HttpResponse
            response = HttpResponse(
                excel_data.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            response['Content-Disposition'] = f'attachment; filename="{model_code}_export.xlsx"'
            return response
        except ImportError as e:
            return ErrorResponse(msg=str(e), code=4000)
        except Exception as e:
            logger.error(f"{FSM} 导出失败: {e}")
            return ErrorResponse(msg=f'导出失败: {str(e)}', code=4000)

    @action(detail=False, methods=['post'], url_path='import')
    def import_data(self, request, **kwargs):
        """从 Excel 导入实例

        POST /api/cmdb/instances/{model_code}/import/
        Body: multipart/form-data with file=@file.xlsx
        """
        model_code = self.get_model_code()

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return ErrorResponse(msg='请上传 Excel 文件', code=4000)

        # 校验文件类型
        if not uploaded_file.name.endswith(('.xlsx', '.xls')):
            return ErrorResponse(msg='仅支持 .xlsx 格式文件', code=4000)

        svc = ImportService()
        try:
            result = svc.import_from_excel(model_code, uploaded_file.read())
            return DetailResponse(data=result, msg='导入完成')
        except ImportError as e:
            return ErrorResponse(msg=str(e), code=4000)
        except Exception as e:
            logger.error(f"{FSM} 导入失败: {e}")
            return ErrorResponse(msg=f'导入失败: {str(e)}', code=4000)
