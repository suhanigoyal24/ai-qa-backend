"""Unit tests for service layer functions"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os
from api.services import upload, rag, llm


class TestUploadService:
    """Tests for upload.py functions"""

    @patch('api.services.upload.PyPDF2.PdfReader')
    @patch('builtins.open', new_callable=mock_open, read_data=b'%PDF-1.4 fake pdf content')
    def test_extract_text_from_pdf(self, mock_file, mock_pdf_reader):
        """Test PDF text extraction with file open mocked"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Sample PDF content"
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [mock_page, mock_page]
        mock_pdf_reader.return_value = mock_reader_instance

        result = upload.extract_text_from_pdf("/fake/path.pdf")
        
        assert "Sample PDF content" in result
        assert mock_pdf_reader.called
        mock_file.assert_called_once_with("/fake/path.pdf", 'rb')

    def test_chunk_text_basic(self):
        """Test text chunking with overlap"""
        text = "word " * 200
        chunks = upload.chunk_text(text, chunk_size=100, overlap=20)
        
        assert len(chunks) >= 2
        assert all(len(c.split()) <= 100 for c in chunks)

    def test_chunk_text_small_input(self):
        """Test chunking with text smaller than chunk_size"""
        text = "short text"
        chunks = upload.chunk_text(text, chunk_size=100, overlap=20)
        
        assert len(chunks) == 1
        assert chunks[0] == text


class TestUploadServiceTimestamps:
    """Tests for timestamp-aware upload functions"""

    @patch('api.services.upload.whisper.load_model')
    def test_transcribe_audio_with_timestamps(self, mock_load_model):
        """Test Whisper transcription with timestamp extraction"""
        mock_model = MagicMock()
        mock_result = {
            'text': 'Hello world this is a test',
            'duration': 5.5,
            'segments': [
                {'start': 0.0, 'end': 1.2, 'text': 'Hello world'},
                {'start': 1.5, 'end': 3.0, 'text': 'this is a'},
                {'start': 3.2, 'end': 5.5, 'text': 'test'}
            ]
        }
        mock_model.transcribe.return_value = mock_result
        mock_load_model.return_value = mock_model

        result = upload.transcribe_audio_with_timestamps("/fake/audio.mp3")
        
        assert result['text'] == 'Hello world this is a test'
        assert result['duration'] == 5.5
        assert len(result['segments']) == 3
        mock_load_model.assert_called_once_with("base")

    def test_chunk_text_with_timestamps_basic(self):
        """Test chunking that preserves timestamp metadata"""
        segments = [
            {'start': 0.0, 'end': 1.0, 'text': 'A' * 100},
            {'start': 1.0, 'end': 2.0, 'text': 'B' * 100},
        ]
        text = " ".join(s['text'] for s in segments)
        
        chunks = upload.chunk_text_with_timestamps(
            text, segments, chunk_size=150, overlap=20
        )
        
        assert len(chunks) >= 1
        assert 'start_time' in chunks[0]
        assert 'end_time' in chunks[0]

    def test_chunk_text_with_timestamps_empty_segments(self):
        """Test fallback when no segments provided"""
        text = "short text"
        chunks = upload.chunk_text_with_timestamps(text, [], chunk_size=100)
        
        assert len(chunks) == 1
        assert chunks[0]['text'] == text


class TestRAGService:
    """Tests for rag.py functions"""

    @patch('api.services.rag.get_embeddings')
    @patch('api.services.rag.faiss.IndexFlatL2')
    @patch('api.services.rag.faiss.normalize_L2')
    @patch('api.services.rag.faiss.write_index')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_create_faiss_index(self, mock_mkdir, mock_open_file, mock_write, mock_normalize, mock_index_cls, mock_get_emb):
        """Test FAISS index creation"""
        mock_emb = MagicMock()
        mock_emb.embed_documents.return_value = [[0.1] * 1536, [0.2] * 1536]
        mock_get_emb.return_value = mock_emb
        
        mock_index = MagicMock()
        mock_index_cls.return_value = mock_index

        chunks = [
            {'text': 'chunk 1', 'start_time': 0.0, 'end_time': 5.0},
            {'text': 'chunk 2', 'start_time': 5.1, 'end_time': 10.0}
        ]
        file_id = "test-123"
        
        result = rag.create_faiss_index(chunks, file_id)
        
        assert mock_get_emb.return_value.embed_documents.called
        assert mock_index.add.called
        assert "faiss_indexes" in result

    @patch('api.services.rag.get_embeddings')
    @patch('api.services.rag.faiss.read_index')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    def test_search_similar(self, mock_exists, mock_open_file, mock_read_index, mock_get_emb):
        """Test similarity search"""
        mock_exists.return_value = True
        mock_emb = MagicMock()
        mock_emb.embed_query.return_value = [0.15] * 1536
        mock_get_emb.return_value = mock_emb
        
        mock_index = MagicMock()
        mock_index.search.return_value = ([[0.1, 0.2]], [[0, 1]])
        mock_read_index.return_value = mock_index
        
        import pickle
        metadata = {
            'chunks': [
                {'index': 0, 'text': 'chunk A', 'start_time': 10.0, 'end_time': 15.0},
                {'index': 1, 'text': 'chunk B', 'start_time': None, 'end_time': None}
            ],
            'count': 2
        }
        with patch('pickle.load', return_value=metadata):
            results = rag.search_similar("test query", "test-123", top_k=2)
        
        assert len(results) <= 2
        if results:
            assert 'text' in results[0]

    def test_get_context_from_results_empty(self):
        """Test context generation with empty results"""
        context = rag.get_context_from_results([])
        assert context == ""

    def test_get_context_from_results_with_data(self):
        """Test context generation with results"""
        results = [
            {'chunk_index': 0, 'text': 'First chunk', 'start_time': 10.5, 'end_time': 15.2},
            {'chunk_index': 2, 'text': 'Third chunk', 'start_time': None, 'end_time': None}
        ]
        context = rag.get_context_from_results(results)
        
        assert '[Timestamp: 10.5s-15.2s]' in context
        assert 'First chunk' in context

    def test_extract_best_timestamp(self):
        """Test timestamp extraction from search results"""
        results = [
            {'start_time': None},
            {'start_time': 45.3, 'end_time': 52.1},
        ]
        timestamp = rag.extract_best_timestamp(results)
        assert timestamp == 45.3

    def test_extract_best_timestamp_none(self):
        """Test when no results have timestamps"""
        results = [{'start_time': None}, {'start_time': None}]
        assert rag.extract_best_timestamp(results) is None

    def test_extract_best_timestamp_empty(self):
        """Test with empty results list"""
        assert rag.extract_best_timestamp([]) is None


class TestLLMService:
    """Tests for llm.py functions"""

    @patch('api.services.llm.ChatGoogleGenerativeAI')
    def test_get_llm(self, mock_chat_cls):
        """Test LLM initialization"""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            llm.get_llm()
            mock_chat_cls.assert_called_once()

    @patch('api.services.llm.get_llm')
    def test_get_chat_response(self, mock_get_llm):
        """Test chat response generation"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "AI answer based on context"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = llm.get_chat_response("What is this?", "context here")
        
        assert "AI answer" in result
        mock_llm.invoke.assert_called_once()

    @patch('api.services.llm.get_llm')
    def test_get_summary(self, mock_get_llm):
        """Test summary generation"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "• Point 1\n• Point 2"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = llm.get_summary("long document text" * 100)
        
        assert "Point" in result
        mock_llm.invoke.assert_called_once()