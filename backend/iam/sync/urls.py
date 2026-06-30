# -*- coding: utf-8 -*-
"""URL configuration for iam sync module — /api/iam/sync/

Registers:
  - Identity sync trigger and status
  - SAML ACS and metadata endpoints
"""

from django.urls import path

from iam.sync import views

urlpatterns = [
    # Sync management
    path('status/', views.sync_status, name='iam-sync-status'),
    path('<int:instance_id>/trigger/', views.trigger_sync, name='iam-sync-trigger'),
    path('<int:instance_id>/test-connect/', views.test_connection, name='iam-sync-test-connect'),
    path('<int:instance_id>/history/', views.sync_history, name='iam-sync-history'),

    # SAML endpoints
    path('saml/login/<int:instance_id>/', views.saml_login, name='iam-saml-login'),
    path('saml/acs/<int:instance_id>/', views.saml_acs, name='iam-saml-acs'),
    path('saml/metadata/<int:instance_id>/', views.saml_metadata, name='iam-saml-metadata'),
]
