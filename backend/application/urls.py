"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from application import dispatch
from application import settings
# from dvadmin.system import admin
from dvadmin.system.views.login import (
    LoginView,
    CaptchaView,
    ApiLogin,
    LogoutView,
    LoginTokenView
)
from dvadmin.system.views.system_config import InitSettingsViewSet
# =========== 初始化系统配置 =================
dispatch.init_system_config()
# =========== 初始化系统配置 =================

urlpatterns = (
        [
            path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
            path("", SpectacularSwaggerView.as_view(url_name="schema"), name="schema-swagger-ui"),
            path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="schema-redoc"),
            path("api/system/", include("dvadmin.system.urls")),
            path("api/login/", LoginView.as_view(), name="token_obtain_pair"),
            path("api/logout/", LogoutView.as_view(), name="token_obtain_pair"),
            path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
            re_path(
                r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")
            ),
            path("api/captcha/", CaptchaView.as_view()),
            path("api/init/settings/", InitSettingsViewSet.as_view()),
            path("apiLogin/", ApiLogin.as_view()),

            # 仅用于开发，上线需关闭
            path("api/token/", LoginTokenView.as_view()),
            
            # Mock Service URLs (模拟数据服务)
            path("api/mock_service/", include("mock_service.urls")),
            # OpsAgent URLs
            path("api/ops/", include("opsagent.urls")),
            # OpsFlow URLs
            path("api/opsflow/", include("opsflow.urls")),
            # IAM URLs
            path("api/iam/", include("iam.urls")),
            # IAM Identity Sync URLs
            path("api/iam/sync/", include("iam.sync.urls")),
            # Integration Hub URLs
            path("api/integration/", include("integration.urls")),
            # CMDB URLs
            path("api/cmdb/", include("cmdb.urls")),
            # ITSM URLs
            path("api/itsm/", include("itsm.urls")),
            # Monitor URLs
            path("api/monitor/", include("monitor.urls")),
            # Job Platform URLs
            path("api/job-platform/", include("job_platform.urls")),
            # Portal URLs
            path("api/portal/", include("portal.urls")),
            # Open API management URLs
            path("api/open-api/", include("open_api.urls")),
            # Open API external URLs (third-party facing) - separate urlconf
            path("api/v2/open/", include("open_api.external_urls")),
            # Agent URLs
            path("api/agent/", include("agent_app.urls")),
            # OAuth2/SSO URLs
            path("api/system/oauth/", include("dvadmin.system.views.oauth")),
            re_path(r'^admin/', admin.site.urls),  # Django admin route
        ]
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        + static(settings.STATIC_URL, document_root=settings.STATIC_URL)
        + [re_path(ele.get('re_path'), include(ele.get('include'))) for ele in settings.PLUGINS_URL_PATTERNS]
)