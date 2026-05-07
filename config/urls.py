"""config/urls.py - Project-level URL configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from config.views import home  # ← Absolute import

urlpatterns = [
    # Root endpoint (must come BEFORE static() catch-all)
    path('', home, name='home'),
    
    # Admin and API
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

# Serve media files in development (catch-all - must be LAST)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)