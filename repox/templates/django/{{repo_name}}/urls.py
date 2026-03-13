from django.contrib import admin
from django.urls import path
from django.http import JsonResponse


def healthcheck(_request):
    return JsonResponse({"status": "ok", "repo": "{{repo_name}}", "author": "{{author}}"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", healthcheck),
]
