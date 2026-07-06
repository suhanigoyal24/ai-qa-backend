"""Root-level views for the config project (e.g. health check / home)"""
from django.http import JsonResponse


def home(request):
    return JsonResponse({
        "status": "ok",
        "message": "AI Q&A backend is running"
    })