from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app_alejandra.urls')),  # Redirige las rutas raíz a app_alejandra
]

# Sirve los archivos de MEDIA (lo que uses como ImageField/FileField con MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Sirve también la carpeta /imagenes/ que estás usando para insumos
    urlpatterns += [
        re_path(
            r'^imagenes/(?P<path>.*)$',
            serve,
            {'document_root': os.path.join(settings.BASE_DIR, 'imagenes')},
        ),
    ]
