
from django.contrib import admin
from django.urls import path, include
from django.conf import settings

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from drf_spectacular.renderers import JSONRenderer
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('app/', include("app.urls")),
]


if settings.DEBUG:
    urlpatterns += [
        path('schema/', SpectacularAPIView.as_view(renderer_classes=[JSONRenderer]), name='schema'),
        path('docs/test/', SpectacularSwaggerView.as_view(), name='swagger-ui'),
        path('docs/', SpectacularRedocView.as_view(), name='swagger-ui'),

    ]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
