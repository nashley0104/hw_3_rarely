from django.contrib import admin
from django.urls import include, path

from app import views

urlpatterns = [
    path("", views.index, name="site_home"),
    path("index.html", views.index, name="site_index_html"),
    path("admin/", admin.site.urls),
    path("app/", include("app.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
]
