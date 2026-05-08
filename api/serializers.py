from rest_framework import serializers
from .models import UploadedFile, ChatMessage

class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = ['id', 'title', 'file_type', 'file_path', 'summary', 'is_processed', 'created_at']
        read_only_fields = ['id', 'is_processed', 'created_at']

class FileUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    file = serializers.FileField()

class ChatRequestSerializer(serializers.Serializer):
    file_id = serializers.UUIDField()
    question = serializers.CharField()

class ChatResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'question', 'answer', 'source_chunks', 'created_at']