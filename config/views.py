"""config/views.py - Project-level views"""
from django.http import JsonResponse


def home(request):
    """
    Root endpoint for the project.
    Returns API status and available endpoints.
    """
    return JsonResponse({
        "message": "🤖 AI Document Q&A API is running!",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "admin": "/admin/",
            "api_root": "/api/",
            "files": "/api/files/",
            "upload": "/api/upload/ (POST, multipart/form-data)",
            "chat": "/api/chat/ (POST, JSON: {file_id, question})",
            "summarize": "/api/summarize/<uuid:file_id>/ (POST)"
        },
        "documentation": "See README.md for full API documentation",
        "github": "https://github.com/suhanigoyal24/ai-qa-backend"
    })