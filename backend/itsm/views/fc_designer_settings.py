"""GET/PUT FcDesigner settings by business (resolved from ?project_id=)"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from itsm.models import FcDesignerSettings
from common.utils.json_response import DetailResponse


class FcDesignerSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def _resolve_business(self, project_id: str):
        if not project_id:
            return None
        try:
            from iam.models import Project
            p = Project.objects.only('business_id').get(id=project_id)
            return str(p.business_id) if p.business_id else None
        except Exception:
            return None

    def get(self, request):
        pid = request.query_params.get("project_id", "")
        bid = self._resolve_business(pid)
        if not bid:
            return DetailResponse(data={})
        obj, _ = FcDesignerSettings.objects.get_or_create(
            business_id=bid, defaults={"value": {}}
        )
        return DetailResponse(data=obj.value)

    def put(self, request):
        pid = request.query_params.get("project_id", "")
        bid = self._resolve_business(pid)
        if not bid:
            return DetailResponse(msg="project_id is required")
        obj, _ = FcDesignerSettings.objects.update_or_create(
            business_id=bid,
            defaults={"value": request.data or {}}
        )
        return DetailResponse(msg="保存成功")
