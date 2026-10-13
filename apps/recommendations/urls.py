from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_recommendations_view, name='recommendations'),
]
