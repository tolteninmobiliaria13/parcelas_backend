from ninja import NinjaAPI
from django.conf import settings
from .routers.dashboard import router as dashboard_router
from .routers.parcelas import router as parcelas_router
from .routers.vencimientos import router as vencimientos_router
from .routers.auth import router as auth_router

# Instanciamos la API central
api = NinjaAPI(
    title="API Sistema de Parcelas",
    description="Endpoints modulares para la gestión del proyecto inmobiliario",
    docs_url="/docs" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)

# Conectamos los enrutadores modulares
api.add_router("/dashboard", dashboard_router, tags=["Dashboard"])
api.add_router("/parcelas", parcelas_router, tags=["Parcelas"])
api.add_router("/vencimientos", vencimientos_router, tags=["Vencimientos"])
api.add_router("/auth", auth_router, tags=["Autenticación y Usuarios"])