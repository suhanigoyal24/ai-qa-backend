"""API views for the multimodal AI Q&A application."""

import logging
import os
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatMessage, DocumentChunk, UploadedFile
from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    FileUploadSerializer,
    UploadedFileSerializer,
)
from .services import image as image_service
from .services import llm as llm_service
from .services import rag as rag_service
from .services import upload as upload_service
from .services import video as video_service

logger = logging.getLogger(__name__)

MEDIA_ROOT = Path(settings.BASE_DIR) / "media"
MEDIA_ROOT.mkdir(exist_ok=True)

TEXT_EXTENSIONS = {"txt", "md", "csv", "json"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac", "aac"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "heic", "heif"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "webm", "mkv", "m4v"}

TIME_KEYWORDS = {
    "when",
    "where",
    "timestamp",
    "time",
    "jump",
    "minute",
    "second",
    "moment",
    "part",
    "clip",
    "scene",
    "appear",
    "start",
}


def _detect_file_type(extension: str):
    """Map an allowed extension to the application's media type."""
    if extension == "pdf":
        return "pdf"
    if extension in TEXT_EXTENSIONS:
        return "text"
    if extension in AUDIO_EXTENSIONS:
        return "audio"
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in VIDEO_EXTENSIONS:
        return "video"
    return None


def _build_chunks(file_type: str, full_path: str):
    """Extract or analyze a file and return chunks plus its duration."""
    if file_type == "pdf":
        text = upload_service.extract_text_from_pdf(full_path)
        return upload_service.chunk_text(text), None

    if file_type == "text":
        text = upload_service.extract_text_file(full_path)
        return upload_service.chunk_text(text), None

    if file_type == "image":
        text = image_service.analyze_image(full_path)
        return upload_service.chunk_text(text), None

    if file_type == "audio":
        result = upload_service.transcribe_audio_with_timestamps(full_path)
        chunks = upload_service.chunk_text_with_timestamps(
            result["text"],
            result["segments"],
            chunk_size=1000,
            overlap=200,
        )
        logger.info(
            "Transcribed audio: segments=%s duration=%.2f",
            len(result["segments"]),
            result["duration"],
        )
        return chunks, result["duration"]

    if file_type == "video":
        result = video_service.analyze_video_with_timestamps(full_path)
        chunks = upload_service.chunk_text_with_timestamps(
            result["text"],
            result["segments"],
            chunk_size=1000,
            overlap=200,
        )
        logger.info(
            "Analyzed video: segments=%s duration=%.2f",
            len(result["segments"]),
            result["duration"],
        )
        return chunks, result["duration"]

    raise ValueError(f"Unsupported file type: {file_type}")


class UploadFileView(APIView):
    """Upload and process a PDF, text, audio, image, or video file."""

    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        saved_path = None

        try:
            serializer = FileUploadSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(
                    "Upload validation error: %s",
                    serializer.errors,
                )
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            title = serializer.validated_data["title"]
            uploaded_file = serializer.validated_data["file"]
            extension = uploaded_file.name.rsplit(".", 1)[-1].lower()
            file_type = _detect_file_type(extension)

            if file_type is None:
                return Response(
                    {
                        "error": (
                            f"Unsupported file type: .{extension}. "
                            "Upload PDF, text, audio, image, or video."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            file_name = f"{title}_{uploaded_file.name}"
            saved_path = default_storage.save(
                file_name,
                ContentFile(uploaded_file.read()),
            )
            full_path = default_storage.path(saved_path)
            logger.info("Saved uploaded file to %s", full_path)

            try:
                chunks, duration = _build_chunks(file_type, full_path)

                if not chunks:
                    raise RuntimeError(
                        "No usable content was found in the uploaded file."
                    )

                with transaction.atomic():
                    database_file = UploadedFile.objects.create(
                        title=title,
                        file_type=file_type,
                        file_path=full_path,
                        duration=duration,
                        is_processed=False,
                        uploaded_by=request.user,
                    )

                    chunk_objects = []
                    for index, chunk in enumerate(chunks):
                        if isinstance(chunk, dict):
                            chunk_objects.append(
                                DocumentChunk(
                                    file=database_file,
                                    chunk_index=index,
                                    text=chunk["text"],
                                    start_time=chunk.get("start_time"),
                                    end_time=chunk.get("end_time"),
                                )
                            )
                        else:
                            chunk_objects.append(
                                DocumentChunk(
                                    file=database_file,
                                    chunk_index=index,
                                    text=chunk,
                                )
                            )

                    DocumentChunk.objects.bulk_create(chunk_objects)
                    rag_service.create_faiss_index(
                        chunks,
                        str(database_file.id),
                    )

                    database_file.is_processed = True
                    database_file.save(update_fields=["is_processed"])

                logger.info(
                    "Successfully processed file %s as %s with %s chunks",
                    database_file.id,
                    file_type,
                    len(chunks),
                )
                return Response(
                    {
                        "message": "Processed successfully",
                        "file_id": str(database_file.id),
                        "title": title,
                        "chunks": len(chunks),
                        "duration": duration,
                        "file_type": file_type,
                    },
                    status=status.HTTP_201_CREATED,
                )

            except upload_service.NoUsableSpeechError as process_error:
                logger.info(
                    "Audio upload contains no usable speech: %s",
                    process_error,
                )
                if saved_path and default_storage.exists(saved_path):
                    default_storage.delete(saved_path)
                return Response(
                    {"error": str(process_error)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as process_error:
                logger.error(
                    "File processing error: %s",
                    process_error,
                    exc_info=True,
                )
                if saved_path and default_storage.exists(saved_path):
                    default_storage.delete(saved_path)
                return Response(
                    {"error": f"Processing failed: {process_error}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as exc:
            logger.error("Upload view error: %s", exc, exc_info=True)
            if saved_path and default_storage.exists(saved_path):
                default_storage.delete(saved_path)
            return Response(
                {"error": f"Upload failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ListFilesView(APIView):
    """List files belonging only to the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            files = UploadedFile.objects.filter(
                uploaded_by=request.user
            ).order_by("-created_at")
            serializer = UploadedFileSerializer(files, many=True)
            return Response(serializer.data)
        except Exception as exc:
            logger.error("List files error: %s", exc, exc_info=True)
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SummarizeView(APIView):
    """Generate a summary for one of the authenticated user's files."""

    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        try:
            file_object = UploadedFile.objects.get(
                id=file_id,
                uploaded_by=request.user,
            )
            if not file_object.is_processed:
                return Response(
                    {"error": "File is still processing"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            chunks = DocumentChunk.objects.filter(
                file=file_object
            ).order_by("chunk_index")
            full_text = " ".join(chunk.text for chunk in chunks)
            logger.info(
                "Generating summary for %s from %s chunks",
                file_id,
                len(chunks),
            )

            summary = llm_service.get_summary(full_text)
            file_object.summary = summary
            file_object.save(update_fields=["summary"])
            return Response({"summary": summary})

        except UploadedFile.DoesNotExist:
            return Response(
                {"error": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            logger.error("Summarize error: %s", exc, exc_info=True)
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChatView(APIView):
    """Answer questions about one of the authenticated user's files."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = ChatRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            file_id = serializer.validated_data["file_id"]
            question = serializer.validated_data["question"]
            file_object = UploadedFile.objects.get(
                id=file_id,
                uploaded_by=request.user,
            )

            if not file_object.is_processed:
                return Response(
                    {"error": "File is still processing"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info("Chat request for file %s", file_id)
            results = rag_service.search_similar(
                question,
                str(file_id),
                top_k=3,
            )
            context = rag_service.get_context_from_results(results)

            if context:
                answer = llm_service.get_chat_response(question, context)
            else:
                answer = (
                    "I could not retrieve usable content for this file. "
                    "Please re-upload it or try again."
                )

            referenced_timestamp = None
            if file_object.file_type in {"audio", "video"} and results:
                question_lower = question.lower()
                question_wants_time = any(
                    keyword in question_lower
                    for keyword in TIME_KEYWORDS
                )
                top_score = results[0].get("score")
                is_strong_match = (
                    top_score is not None and top_score < 0.6
                )

                if question_wants_time and is_strong_match:
                    referenced_timestamp = (
                        rag_service.extract_best_timestamp(results)
                    )

            message = ChatMessage.objects.create(
                file=file_object,
                question=question,
                answer=answer,
                source_chunks=[
                    result["chunk_index"] for result in results
                ],
                referenced_timestamp=referenced_timestamp,
            )
            response_data = ChatResponseSerializer(message).data

            if (
                referenced_timestamp is not None
                and isinstance(referenced_timestamp, (int, float))
                and referenced_timestamp >= 0
            ):
                response_data["referenced_timestamp"] = float(
                    referenced_timestamp
                )
                response_data["file_type"] = file_object.file_type

            return Response(response_data)

        except UploadedFile.DoesNotExist:
            return Response(
                {"error": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            logger.error("Chat error: %s", exc, exc_info=True)
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeleteFileView(APIView):
    """Delete a user's uploaded file and all associated data."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, file_id):
        try:
            file_object = UploadedFile.objects.get(
                id=file_id,
                uploaded_by=request.user,
            )

            if file_object.file_path and os.path.exists(
                file_object.file_path
            ):
                try:
                    os.remove(file_object.file_path)
                except OSError as exc:
                    logger.warning(
                        "Could not delete uploaded file: %s",
                        exc,
                    )

            faiss_dir = Path(settings.BASE_DIR) / "faiss_indexes"
            for suffix in (".faiss", "_meta.pkl"):
                index_path = faiss_dir / f"{file_id}{suffix}"
                if index_path.exists():
                    try:
                        index_path.unlink()
                    except OSError as exc:
                        logger.warning(
                            "Could not delete FAISS file %s: %s",
                            index_path,
                            exc,
                        )

            file_object.delete()
            logger.info("Deleted file %s and associated data", file_id)
            return Response(
                {"message": "File deleted successfully"},
                status=status.HTTP_200_OK,
            )

        except UploadedFile.DoesNotExist:
            return Response(
                {"error": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            logger.error("Delete file error: %s", exc, exc_info=True)
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        