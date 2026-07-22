from ninja import NinjaAPI
from .routers.dashboard import router as dashboard_router
from .routers.parcelas import router as parcelas_router
from .routers.vencimientos import router as vencimientos_router

# Instanciamos la API central
api = NinjaAPI(
    title="API Sistema de Parcelas",
    description="Endpoints modulares para la gestión del proyecto inmobiliario"
)

# Conectamos los enrutadores modulares
api.add_router("/dashboard", dashboard_router, tags=["Dashboard"])
api.add_router("/parcelas", parcelas_router, tags=["Parcelas"])
api.add_router("/vencimientos", vencimientos_router, tags=["Vencimientos"])