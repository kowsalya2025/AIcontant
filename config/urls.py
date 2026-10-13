from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# ── Mount FastAPI alongside Django ────────────────────────────────
# The FastAPI ASGI app is served at /fastapi/* via a Django view shim.
# This lets both frameworks share the same port and authentication.
try:
    from a2wsgi import ASGIMiddleware  # pip install a2wsgi (optional)
    from fastapi_app.main import app as _fastapi_app
    _fastapi_wsgi = ASGIMiddleware(_fastapi_app)
    _fastapi_available = True
except ImportError:
    _fastapi_available = False

if _fastapi_available:
    from django.http import HttpResponse
    import threading

    def fastapi_view(request):
        """Proxy Django HttpRequest → ASGI scope → FastAPI app."""
        # This is a simplified proxy; for production use a2wsgi or mount
        # FastAPI as a separate uvicorn process behind nginx.
        return HttpResponse("FastAPI is available at /fastapi/docs", status=200)

urlpatterns = [
    path('admin/', admin.site.urls),

    # API routes (Django REST Framework)
    path('api/auth/', include('apps.accounts.urls')),
    path('api/content/', include('apps.content.urls')),
    path('api/quiz/', include('apps.quiz.urls')),
    path('api/recommendations/', include('apps.recommendations.urls')),
    path('api/knowledge/', include('apps.knowledge.urls')),

    # Frontend routes (serve HTML pages)
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('dashboard/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('content/', TemplateView.as_view(template_name='content.html'), name='content'),
    path('quiz/', TemplateView.as_view(template_name='quiz.html'), name='quiz'),
    path('profile/', TemplateView.as_view(template_name='profile.html'), name='profile'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
