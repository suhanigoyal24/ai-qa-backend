from django.urls import path
from .views import UploadFileView, ListFilesView, SummarizeView, ChatView

urlpatterns = [
    path('upload/', UploadFileView.as_view(), name='upload'),
    path('files/', ListFilesView.as_view(), name='list-files'),
    path('summarize/<uuid:file_id>/', SummarizeView.as_view(), name='summarize'),
    path('chat/', ChatView.as_view(), name='chat'),
]