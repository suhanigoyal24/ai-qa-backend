"""Database models for AI Q&A application"""
import uuid
from django.db import models


class UploadedFile(models.Model):
    """Stores metadata for uploaded PDF, audio, or video files"""
    FILE_TYPES = [
        ('pdf', 'PDF Document'),
        ('audio', 'Audio File'),
        ('video', 'Video File'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    file_path = models.CharField(max_length=500, help_text="Local path or cloud URL")
    summary = models.TextField(blank=True, null=True, help_text="AI-generated summary")
    
    # NEW: Duration for audio/video files
    duration = models.FloatField(null=True, blank=True, help_text="Duration in seconds (for audio/video)")
    
    is_processed = models.BooleanField(default=False, help_text="True when chunks & embeddings are ready")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_file_type_display()})"


class DocumentChunk(models.Model):
    """Stores text chunks + vector embeddings for AI semantic search"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField(help_text="Order of chunk in document")
    text = models.TextField()
    
    # NEW: Timestamps for audio/video chunks
    start_time = models.FloatField(null=True, blank=True, help_text="Start time in seconds")
    end_time = models.FloatField(null=True, blank=True, help_text="End time in seconds")
    
    # FAISS embeddings stored externally; this field kept for reference
    embedding_dimensions = models.IntegerField(default=1536, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['file', 'chunk_index']),
            # NEW: Index for timestamp queries
            models.Index(fields=['file', 'start_time'], name='api_documen_file_id_start_idx'),
        ]

    def __str__(self):
        time_str = f" ({self.start_time}s-{self.end_time}s)" if self.start_time is not None else ""
        return f"Chunk {self.chunk_index} of {self.file.title}{time_str}"


class ChatMessage(models.Model):
    """Stores user questions & AI answers linked to a file"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    question = models.TextField()
    answer = models.TextField()
    # Track which chunks were used for this answer (for timestamp playback)
    source_chunks = models.JSONField(default=list, blank=True, help_text="List of chunk IDs used for context")
    
    # NEW: If answer references a specific timestamp, store it
    referenced_timestamp = models.FloatField(null=True, blank=True, help_text="Suggested playback time in seconds")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Q: {self.question[:50]}..."