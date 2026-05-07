"""Unit tests for models - covers __str__ methods and edge cases"""
import pytest
from api.models import UploadedFile, DocumentChunk, ChatMessage
import uuid


@pytest.mark.django_db
class TestUploadedFileModel:
    """Tests for UploadedFile model"""

    def test_str_pdf(self):
        """Test __str__ for PDF file type"""
        file = UploadedFile(title="Resume", file_type="pdf", file_path="/tmp/resume.pdf")
        assert str(file) == "Resume (PDF Document)"

    def test_str_audio(self):
        """Test __str__ for audio file type"""
        file = UploadedFile(title="Lecture", file_type="audio", file_path="/tmp/lec.mp3")
        assert str(file) == "Lecture (Audio File)"

    def test_str_video(self):
        """Test __str__ for video file type"""
        file = UploadedFile(title="Demo", file_type="video", file_path="/tmp/demo.mp4")
        assert str(file) == "Demo (Video File)"

    def test_duration_field_optional(self):
        """Test that duration field is optional"""
        file = UploadedFile.objects.create(
            title="Test", file_type="pdf", file_path="/tmp/t.pdf"
        )
        assert file.duration is None
        
        file.duration = 125.5
        file.save()
        assert file.duration == 125.5


@pytest.mark.django_db
class TestDocumentChunkModel:
    """Tests for DocumentChunk model"""

    def test_str_without_timestamps(self):
        """Test __str__ when no timestamps set"""
        file = UploadedFile.objects.create(title="Test", file_type="pdf", file_path="/tmp/t.pdf")
        chunk = DocumentChunk.objects.create(file=file, chunk_index=0, text="Hello")
        assert str(chunk) == "Chunk 0 of Test"

    def test_str_with_timestamps(self):
        """Test __str__ includes timestamps when set"""
        file = UploadedFile.objects.create(title="Audio", file_type="audio", file_path="/tmp/a.mp3")
        chunk = DocumentChunk.objects.create(
            file=file, chunk_index=1, text="Hi there", start_time=10.5, end_time=15.2
        )
        assert "10.5s-15.2s" in str(chunk)

    def test_embedding_dimensions_default(self):
        """Test embedding_dimensions has default value"""
        file = UploadedFile.objects.create(title="Test", file_type="pdf", file_path="/tmp/t.pdf")
        chunk = DocumentChunk.objects.create(file=file, chunk_index=0, text="Text")
        assert chunk.embedding_dimensions == 1536


@pytest.mark.django_db
class TestChatMessageModel:
    """Tests for ChatMessage model"""

    def test_str_truncates_long_question(self):
        """Test __str__ truncates long questions"""
        file = UploadedFile.objects.create(title="Test", file_type="pdf", file_path="/tmp/t.pdf")
        long_q = "A" * 100
        msg = ChatMessage.objects.create(file=file, question=long_q, answer="Response")
        assert str(msg).startswith("Q: AAAAA")
        assert len(str(msg)) <= 60  # "Q: " + 50 chars + "..."

    def test_referenced_timestamp_optional(self):
        """Test referenced_timestamp field is optional"""
        file = UploadedFile.objects.create(title="Test", file_type="pdf", file_path="/tmp/t.pdf")
        msg = ChatMessage.objects.create(file=file, question="Hi", answer="Hello")
        assert msg.referenced_timestamp is None
        
        msg.referenced_timestamp = 45.3
        msg.save()
        assert msg.referenced_timestamp == 45.3

    def test_source_chunks_default_empty_list(self):
        """Test source_chunks defaults to empty list"""
        file = UploadedFile.objects.create(title="Test", file_type="pdf", file_path="/tmp/t.pdf")
        msg = ChatMessage.objects.create(file=file, question="Q", answer="A")
        assert msg.source_chunks == []