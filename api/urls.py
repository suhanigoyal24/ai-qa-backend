"""API URL configuration"""
from django.urls import path
from .views import home, UploadFileView, ListFilesView, SummarizeView, ChatView

urlpatterns = [
    # Root endpoint for this app (mounted at /api/ in config/urls.py)
    path('', home, name='home'),
    
    # API endpoints
    path('upload/', UploadFileView.as_view(), name='upload'),
    path('files/', ListFilesView.as_view(), name='list-files'),
    path('summarize/<uuid:file_id>/', SummarizeView.as_view(), name='summarize'),
    path('chat/', ChatView.as_view(), name='chat'),
]