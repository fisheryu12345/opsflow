from rest_framework.views import APIView
from django.shortcuts import render


class PrivacyView(APIView):
    """
    OpsFlow Privacy Policy (隐私政策)
    """
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return render(request, 'privacy.html')


class TermsServiceView(APIView):
    """
    OpsFlow Terms of Service (服务条款)
    """
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return render(request, 'terms_service.html')
