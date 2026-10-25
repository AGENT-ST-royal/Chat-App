
"""
URL configuration for newWork project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from work.api_views import (
    HealthCheckView,
    CurrentUserProfileView,
    MobileLoginView,
    MobileLogoutView,
    ConversationListView,
    ConversationMessageHistoryView,
    SendMessageView,
)


urlpatterns = [
    path("admin/", admin.site.urls),

    # Version 1 API
    path(
        "api/v1/health/",
        HealthCheckView.as_view(),
        name="api_health",
    ),
    path(
        "api/v1/auth/login/",
        MobileLoginView.as_view(),
        name="api_login",
    ),
    path(
        "api/v1/auth/logout/",
        MobileLogoutView.as_view(),
        name="api_logout",
    ),
    path(
        "api/v1/me/",
        CurrentUserProfileView.as_view(),
        name="api_current_user",
    ),
    path(
        "api/v1/conversations/",
        ConversationListView.as_view(),
        name="api_conversations",
    ),
    path(
        "api/v1/conversations/<int:conversation_id>/messages/",
        ConversationMessageHistoryView.as_view(),
        name="api_conversation_messages",
    ),
    path(
        "api/v1/conversations/<int:conversation_id>/messages/send/",
        SendMessageView.as_view(),
        name="api_send_message",
    ),

    # Existing website routes
    path("", include("work.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
