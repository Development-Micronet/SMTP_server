from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("admin_panel/", include("admin_panel.urls")),
    path("", include("webmail.urls")),
]
