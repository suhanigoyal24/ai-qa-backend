"""API views for AI Q&A application"""
import os
from pathlib import Path
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from .models import UploadedFile, DocumentChunk, ChatMessage
from .serializers import (
    UploadedFileSerializer, FileUploadSerializer,
    ChatRequestSerializer, ChatResponseSerializer
)
from .services import upload as upload_service
from .services import rag as rag_service
from .services import llm as llm_service


# Media folder setup
MEDIA_ROOT = Path(settings.BASE_DIR) / 'media'
MEDIA_ROOT.mkdir(exist_ok=True)

# config/views.py
from django.http import JsonResponse

def home(request):
    """Root endpoint for the project"""
    return JsonResponse({
        "message": "🤖 AI Document Q&A API is running!",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "admin": "/admin/",
            "api_root": "/api/",
            "files": "/api/files/",
            "upload": "/api/upload/ (POST)",
            "chat": "/api/chat/ (POST)", 
            "summarize": "/api/summarize/<file_id>/ (POST)"
        },
        "docs": "See README.md for full API documentation",
        "github": "https://github.com/suhanigoyal24/ai-qa-backend"
    })

def _has_field(model, field_name):
    """Check if a model has a field (safe for migrations)"""
    return field_name in [f.name for f in model._meta.get_fields()]


class UploadFileView(APIView):
    """Handle file upload: PDF, audio, or video"""
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        title = serializer.validated_data['title']
        uploaded_file = serializer.validated_data['file']

        # Determine file type
        ext = uploaded_file.name.split('.')[-1].lower()
        if ext == 'pdf':
            file_type = 'pdf'
        elif ext in ['mp3', 'wav', 'm4a', 'ogg', 'flac']:
            file_type = 'audio'
        elif ext in ['mp4', 'mov', 'avi', 'webm', 'mkv']:
            file_type = 'video'
        else:
            return Response(
                {'error': f'Unsupported file type: .{ext}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save file locally
        file_path = MEDIA_ROOT / uploaded_file.name
        with open(file_path, 'wb+') as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

        try:
            # Process based on file type
            if file_type == 'pdf':
                text = upload_service.extract_text_from_pdf(str(file_path))
                chunks = upload_service.chunk_text(text)
                duration = None
            else:  # audio or video
                result = upload_service.transcribe_audio_with_timestamps(str(file_path))
                text = result['text']
                duration = result['duration']
                # Use timestamp-aware chunking
                chunks = upload_service.chunk_text_with_timestamps(
                    text, result['segments'], chunk_size=1000, overlap=200
                )

            # Save to database
            db_file = UploadedFile.objects.create(
                title=title,
                file_type=file_type,
                file_path=str(file_path),
                duration=duration,
                is_processed=False
            )
            
            # Save chunks with timestamp metadata
            chunk_objects = []
            for i, chunk in enumerate(chunks):
                if isinstance(chunk, dict):
                    chunk_objects.append(DocumentChunk(
                        file=db_file,
                        chunk_index=i,
                        text=chunk['text'],
                        start_time=chunk.get('start_time'),
                        end_time=chunk.get('end_time')
                    ))
                else:
                    chunk_objects.append(DocumentChunk(
                        file=db_file,
                        chunk_index=i,
                        text=chunk
                    ))
            
            DocumentChunk.objects.bulk_create(chunk_objects)

            # Create FAISS index for semantic search
            rag_service.create_faiss_index(chunks, str(db_file.id))

            # Mark as processed
            db_file.is_processed = True
            db_file.save()

            return Response({
                'message': 'Processed successfully',
                'file_id': str(db_file.id),
                'chunks': len(chunks),
                'duration': duration,
                'file_type': file_type
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Cleanup on failure
            if file_path.exists():
                file_path.unlink()
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListFilesView(APIView):
    """List all uploaded files with metadata"""
    def get(self, request):
        files = UploadedFile.objects.all().order_by('-created_at')
        serializer = UploadedFileSerializer(files, many=True)
        return Response(serializer.data)


class SummarizeView(APIView):
    """Generate AI summary for a processed file"""
    def post(self, request, file_id):
        try:
            file_obj = UploadedFile.objects.get(id=file_id)
            if not file_obj.is_processed:
                return Response(
                    {'error': 'File is still processing'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reconstruct full text from chunks
            chunks = DocumentChunk.objects.filter(file=file_obj).order_by('chunk_index')
            full_text = " ".join(c.text for c in chunks)
            
            # Generate summary via Gemini
            summary = llm_service.get_summary(full_text)
            
            file_obj.summary = summary
            file_obj.save()
            
            return Response({'summary': summary})
            
        except UploadedFile.DoesNotExist:
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)


class ChatView(APIView):
    """Ask questions about an uploaded file"""
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file_id = serializer.validated_data['file_id']
        question = serializer.validated_data['question']

        try:
            file_obj = UploadedFile.objects.get(id=file_id)
            if not file_obj.is_processed:
                return Response(
                    {'error': 'File is still processing'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Semantic search for relevant chunks
            results = rag_service.search_similar(question, str(file_id), top_k=3)
            context = rag_service.get_context_from_results(results)
            
            # Get AI answer
            answer = llm_service.get_chat_response(question, context)
            
            # Extract best timestamp for playback (if audio/video)
            referenced_timestamp = None
            if file_obj.file_type in ['audio', 'video'] and results:
                referenced_timestamp = rag_service.extract_best_timestamp(results)

            # Save chat message - safely handle referenced_timestamp field
            create_kwargs = {
                'file': file_obj,
                'question': question,
                'answer': answer,
                'source_chunks': [r['chunk_index'] for r in results]
            }
            # Only add referenced_timestamp if field exists (migration applied)
            if _has_field(ChatMessage, 'referenced_timestamp') and referenced_timestamp is not None:
                create_kwargs['referenced_timestamp'] = referenced_timestamp
            
            msg = ChatMessage.objects.create(**create_kwargs)
            
            response_data = ChatResponseSerializer(msg).data
            # Add timestamp info for frontend if available
            if referenced_timestamp is not None:
                response_data['referenced_timestamp'] = referenced_timestamp
                response_data['file_type'] = file_obj.file_type
            
            return Response(response_data)
            
        except UploadedFile.DoesNotExist:
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)