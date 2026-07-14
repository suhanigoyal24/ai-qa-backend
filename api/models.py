"""Database models for the AI Q&A application."""

import uuid

from django.contrib.auth.models import User
from django.db import models


class UploadedFile(models.Model):
    """Store metadata for a user's supported uploaded media."""

    FILE_TYPES = [
        ("pdf", "PDF Document"),
        ("text", "Text Document"),
        ("audio", "Audio File"),
        ("image", "Image File"),
        ("video", "Video File"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    title = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    file_path = models.CharField(
        max_length=500,
        help_text="Local path or cloud URL",
    )
    summary = models.TextField(
        blank=True,
        null=True,
        help_text="AI-generated summary",
    )
    duration = models.FloatField(
        null=True,
        blank=True,
        help_text="Duration in seconds for audio or video",
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="uploaded_files",
        null=True,
        blank=True,
    )
    is_processed = models.BooleanField(
        default=False,
        help_text="True when chunks and embeddings are ready",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_file_type_display()})"


class DocumentChunk(models.Model):
    """Store searchable text chunks and optional media timestamps."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    file = models.ForeignKey(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.IntegerField(
        help_text="Order of chunk in document",
    )
    text = models.TextField()
    start_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Start time in seconds",
    )
    end_time = models.FloatField(
        null=True,
        blank=True,
        help_text="End time in seconds",
    )
    embedding_dimensions = models.IntegerField(
        default=1536,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["file", "chunk_index"]),
            models.Index(
                fields=["file", "start_time"],
                name="api_documen_file_id_start_idx",
            ),
        ]

    def __str__(self):
        time_text = ""
        if self.start_time is not None:
            time_text = f" ({self.start_time}s-{self.end_time}s)"
        return f"Chunk {self.chunk_index} of {self.file.title}{time_text}"


class ChatMessage(models.Model):
    """Store questions and answers linked to an uploaded file."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    file = models.ForeignKey(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )
    question = models.TextField()
    answer = models.TextField()
    source_chunks = models.JSONField(
        default=list,
        blank=True,
        help_text="List of chunk indexes used for context",
    )
    referenced_timestamp = models.FloatField(
        null=True,
        blank=True,
        help_text="Suggested playback time in seconds",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Q: {self.question[:50]}..."
