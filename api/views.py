"""API views for AI Q&A application"""
import os
import logging
from pathlib import Path
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
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

logger = logging.getLogger(__name__)

# Media folder setup
MEDIA_ROOT = Path(settings.BASE_DIR) / 'media'
MEDIA_ROOT.mkdir(exist_ok=True)


class UploadFileView(APIView):
    """Handle file upload: PDF, audio, or video"""
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        try:
            serializer = FileUploadSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Upload validation error: {serializer.errors}")
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

            # Save file safely using Django storage
            file_name = f"{title}_{uploaded_file.name}"
            file_path = default_storage.save(file_name, ContentFile(uploaded_file.read()))
            full_path = default_storage.path(file_path)
            logger.info(f"Saved file to: {full_path}")

            try:
                # Process based on file type
                if file_type == 'pdf':
                    text = upload_service.extract_text_from_pdf(full_path)
                    chunks = upload_service.chunk_text(text)
                    duration = None
                else:  # audio or video - Whisper with timestamps
                    result = upload_service.transcribe_audio_with_timestamps(full_path)
                    text = result['text']
                    duration = result['duration']
                    chunks = upload_service.chunk_text_with_timestamps(
                        text, result['segments'], chunk_size=1000, overlap=200
                    )
                    logger.info(f"Transcribed {file_type}: {len(result['segments'])} segments, duration: {duration}s")

                # Save to database
                db_file = UploadedFile.objects.create(
                    title=title,
                    file_type=file_type,
                    file_path=full_path,
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
                logger.info(f"Created {len(chunk_objects)} chunks for file {db_file.id}")

                # Create FAISS index for semantic search
                rag_service.create_faiss_index(chunks, str(db_file.id))

                # Mark as processed
                db_file.is_processed = True
                db_file.save()

                logger.info(f"✅ Successfully processed file: {db_file.id}")
                return Response({
                    'message': 'Processed successfully',
                    'file_id': str(db_file.id),
                    'chunks': len(chunks),
                    'duration': duration,
                    'file_type': file_type
                }, status=status.HTTP_201_CREATED)

            except Exception as process_error:
                logger.error(f"❌ Processing error: {process_error}", exc_info=True)
                # Cleanup on processing failure
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
                return Response(
                    {'error': f'Processing failed: {str(process_error)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"❌ Upload view error: {e}", exc_info=True)
            return Response(
                {'error': f'Upload failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListFilesView(APIView):
    """List all uploaded files with metadata"""
    def get(self, request):
        try:
            files = UploadedFile.objects.all().order_by('-created_at')
            serializer = UploadedFileSerializer(files, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"List files error: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            logger.info(f"Generating summary for {file_id} ({len(chunks)} chunks)")
            
            # Generate summary via Gemini
            summary = llm_service.get_summary(full_text)
            
            file_obj.summary = summary
            file_obj.save()
            
            return Response({'summary': summary})
            
        except UploadedFile.DoesNotExist:
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Summarize error: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatView(APIView):
    """Ask questions about an uploaded file"""
    def post(self, request):
        try:
            serializer = ChatRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            file_id = serializer.validated_data['file_id']
            question = serializer.validated_data['question']

            file_obj = UploadedFile.objects.get(id=file_id)
            if not file_obj.is_processed:
                return Response(
                    {'error': 'File is still processing'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Chat request for file {file_id}: '{question}'")

            # Semantic search for relevant chunks
            results = rag_service.search_similar(question, str(file_id), top_k=3)
            logger.info(f"Found {len(results)} relevant chunks")
            
            context = rag_service.get_context_from_results(results)
            
            # Get AI answer
            answer = llm_service.get_chat_response(question, context)
            
            # Extract best timestamp for playback (if audio/video)
            referenced_timestamp = None
            if file_obj.file_type in ['audio', 'video'] and results:
                referenced_timestamp = rag_service.extract_best_timestamp(results)
                if referenced_timestamp is not None:
                    logger.info(f"Extracted timestamp: {referenced_timestamp}s")
                else:
                    logger.info("No valid timestamp found in results")

            # Save chat message
            msg = ChatMessage.objects.create(
                file=file_obj,
                question=question,
                answer=answer,
                source_chunks=[r['chunk_index'] for r in results],
                referenced_timestamp=referenced_timestamp
            )
            
            # Build response data
            response_data = ChatResponseSerializer(msg).data
            
            # Only include timestamp if it's a VALID number > 0
            if referenced_timestamp is not None and isinstance(referenced_timestamp, (int, float)) and referenced_timestamp > 0:
                response_data['referenced_timestamp'] = float(referenced_timestamp)
                response_data['file_type'] = file_obj.file_type
                logger.info(f"Returning timestamp {referenced_timestamp}s in response")
            else:
                # Remove timestamp field if invalid to avoid frontend confusion
                response_data.pop('referenced_timestamp', None)
                logger.info("No valid timestamp to return")
            
            return Response(response_data)
            
        except UploadedFile.DoesNotExist:
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)