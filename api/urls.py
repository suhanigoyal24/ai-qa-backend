"""API URL configuration"""
from django.urls import path
from .views import UploadFileView, ListFilesView, SummarizeView, ChatView
from .auth_views import RegisterView, LoginView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('upload/', UploadFileView.as_view(), name='upload'),
    path('files/', ListFilesView.as_view(), name='list-files'),
    path('summarize/<uuid:file_id>/', SummarizeView.as_view(), name='summarize'),
    path('chat/', ChatView.as_view(), name='chat'),
]