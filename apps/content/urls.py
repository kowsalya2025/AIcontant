from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.generate_content_view, name='generate-content'),
    path('history/', views.content_history_view, name='content-history'),
    path('<int:pk>/', views.content_detail_view, name='content-detail'),
    path('<int:pk>/bookmark/', views.bookmark_content_view, name='bookmark-content'),
]
