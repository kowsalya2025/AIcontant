from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.generate_quiz_view, name='generate-quiz'),
    path('submit/', views.submit_quiz_view, name='submit-quiz'),
    path('history/', views.quiz_history_view, name='quiz-history'),
]
