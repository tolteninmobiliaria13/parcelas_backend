from django.contrib import admin
from django.urls import path
from api.api import api  # Importamos la instancia de Ninja que acabas de crear
from django.views.generic.base import RedirectView
    
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls), # Conectamos Ninja al endpoint raíz /api/
    # Agregamos esta línea para redirigir la ruta vacía hacia la documentación
    path('', RedirectView.as_view(url='/api/docs', permanent=False)),
]