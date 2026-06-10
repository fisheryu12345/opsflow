# -*- coding: utf-8 -*-

"""
@author: opsflow
@Remark: 语言偏好 API — 获取/设置用户语言

GET  /api/system/language/     → 返回当前语言
POST /api/system/language/    → 设置语言 {"language": "en" | "zh-hans"}
"""

from django.utils.translation import check_for_language, activate
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework import serializers

from dvadmin.utils.json_response import DetailResponse, ErrorResponse


class LanguageSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=['zh-hans', 'en'], label="语言代码")


class LanguageView(APIView):
    """语言偏好 — 获取/设置当前用户语言"""

    @extend_schema(summary="获取当前语言")
    def get(self, request: Request):
        lang = request.session.get('django_language', 'zh-hans')
        if request.user.is_authenticated and hasattr(request.user, 'language') and request.user.language:
            lang = request.user.language
        return DetailResponse(data={'language': lang})

    @extend_schema(
        summary="设置语言",
        request=LanguageSerializer,
        responses={200: DetailResponse},
    )
    def post(self, request: Request):
        serializer = LanguageSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(msg="无效的语言代码")
        lang = serializer.validated_data['language']
        if not check_for_language(lang):
            return ErrorResponse(msg=f"不支持的语言: {lang}")

        request.session['django_language'] = lang
        activate(lang)

        if request.user.is_authenticated:
            request.user.language = lang
            request.user.save(update_fields=['language'])

        return DetailResponse(msg="语言已切换", data={'language': lang})
