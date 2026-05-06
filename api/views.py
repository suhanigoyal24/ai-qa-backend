import os
from django.conf import settings
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
MEDIA_ROOT = os.path.join(settings.BASE_DIR, 'media')
os.makedirs(MEDIA_ROOT, exist_ok=True)

class UploadFileView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        title = serializer.validated_data['title']
        uploaded_file = serializer.validated_data['file']

        # Determine type
        ext = uploaded_file.name.split('.')[-1].lower()
        if ext == 'pdf': file_type = 'pdf'
        elif ext in ['mp3', 'wav', 'm4a', 'ogg']: file_type = 'audio'
        elif ext in ['mp4', 'mov', 'avi', 'webm']: file_type = 'video'
        else: return Response({'error': 'Unsupported file type'}, status=status.HTTP_400_BAD_REQUEST)

        # Save locally
        file_path = os.path.join(MEDIA_ROOT, uploaded_file.name)
        with open(file_path, 'wb+') as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

        try:
            # Process
            text = upload_service.extract_text_from_pdf(file_path) if file_type == 'pdf' else upload_service.transcribe_audio(file_path)
            chunks = upload_service.chunk_text(text)

            # DB Save
            db_file = UploadedFile.objects.create(title=title, file_type=file_type, file_path=file_path, is_processed=False)
            DocumentChunk.objects.bulk_create([
                DocumentChunk(file=db_file, chunk_index=i, text=chunk) for i, chunk in enumerate(chunks)
            ])

            # FAISS Index
            rag_service.create_faiss_index(chunks, str(db_file.id))

            db_file.is_processed = True
            db_file.save()

            return Response({'message': 'Processed successfully', 'file_id': str(db_file.id), 'chunks': len(chunks)}, status=status.HTTP_201_CREATED)
        except Exception as e:
            if os.path.exists(file_path): os.remove(file_path)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ListFilesView(APIView):
    def get(self, request):
        files = UploadedFile.objects.all().order_by('-created_at')
        return Response(UploadedFileSerializer(files, many=True).data)

class SummarizeView(APIView):
    def post(self, request, file_id):
        try:
            file_obj = UploadedFile.objects.get(id=file_id)
            if not file_obj.is_processed:
                return Response({'error': 'Processing pending'}, status=status.HTTP_400_BAD_REQUEST)
            
            full_text = " ".join([c.text for c in DocumentChunk.objects.filter(file=file_obj).order_by('chunk_index')])
            summary = llm_service.get_summary(full_text)
            file_obj.summary = summary
            file_obj.save()
            return Response({'summary': summary})
        except UploadedFile.DoesNotExist:
            return Response({'error': 'File not found'}, status=404)

class ChatView(APIView):
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid(): return Response(serializer.errors, status=400)

        file_id, question = serializer.validated_data['file_id'], serializer.validated_data['question']
        try:
            file_obj = UploadedFile.objects.get(id=file_id)
            if not file_obj.is_processed: return Response({'error': 'Processing pending'}, status=400)

            results = rag_service.search_similar(question, str(file_id), top_k=3)
            context = rag_service.get_context_from_results(results)
            answer = llm_service.get_chat_response(question, context)

            msg = ChatMessage.objects.create(file=file_obj, question=question, answer=answer, source_chunks=[r['chunk_index'] for r in results])
            return Response(ChatResponseSerializer(msg).data)
        except UploadedFile.DoesNotExist:
            return Response({'error': 'File not found'}, status=404)