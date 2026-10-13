from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_document_view, name='upload-document'),
    path('documents/', views.list_documents_view, name='list-documents'),
]
