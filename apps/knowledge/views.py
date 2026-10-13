import os
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings

from .models import KnowledgeDocument
from ai_services.rag_service import RAGService

rag_service = RAGService()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_document_view(request):
    """Upload a PDF/TXT file to be indexed into the RAG knowledge base."""
    file = request.FILES.get('file')
    title = request.data.get('title', '')
    subject = request.data.get('subject', 'general')

    if not file:
        return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ['.pdf', '.txt', '.docx']:
        return Response(
            {'error': 'Only PDF, TXT, and DOCX files are supported.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    doc = KnowledgeDocument.objects.create(
        uploaded_by=request.user,
        title=title or file.name,
        subject=subject,
        file=file,
        file_type=ext.lstrip('.')
    )

    # Index into FAISS
    try:
        file_path = os.path.join(settings.MEDIA_ROOT, str(doc.file))
        chunk_count = rag_service.add_document(file_path)
        doc.chunk_count = chunk_count
        doc.is_indexed = True
        doc.save(update_fields=['chunk_count', 'is_indexed'])
        return Response({
            'document': {
                'id': doc.id,
                'title': doc.title,
                'subject': doc.subject,
                'chunk_count': chunk_count,
                'is_indexed': True
            },
            'message': f'Document indexed with {chunk_count} chunks!'
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({
            'document': {'id': doc.id, 'title': doc.title},
            'message': 'Document uploaded but indexing failed. Will retry.',
            'error': str(e)
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_documents_view(request):
    """List all uploaded knowledge base documents."""
    docs = KnowledgeDocument.objects.filter(uploaded_by=request.user)
    return Response({
        'documents': [
            {
                'id': d.id,
                'title': d.title,
                'subject': d.subject,
                'file_type': d.file_type,
                'chunk_count': d.chunk_count,
                'is_indexed': d.is_indexed,
                'uploaded_at': d.uploaded_at
            }
            for d in docs
        ]
    })
