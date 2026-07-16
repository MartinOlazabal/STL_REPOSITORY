# =============================================================================
# main.py
# =============================================================================
# Este es el PUNTO DE ENTRADA de la aplicación FastAPI.
# Es el primer archivo que ejecuta Uvicorn cuando arrancamos el servidor.
#
# Responsabilidades de este archivo:
# 1. Crear la instancia central de la aplicación FastAPI.
# 2. Crear las tablas en la base de datos (en desarrollo).
# 3. Registrar todos los routers (módulos de endpoints).
# 4. Configurar middlewares globales (CORS, logging, etc.) cuando sea necesario.
#
# Analogía: Si la aplicación fuera una empresa, main.py sería la recepción
# principal que redirige cada petición al departamento correcto (router).
# =============================================================================

from fastapi import FastAPI

# Importamos Base y engine para poder crear las tablas en la DB al arrancar
from app.database import Base, engine

# Importamos los modelos para que SQLAlchemy los "conozca" antes de crear tablas.
# IMPORTANTE: Si no importamos los modelos aquí, Base.metadata no sabrá de ellos
# y no creará sus tablas. El import es necesario aunque parezca que no se usa.
from app.models import user, post  # noqa: F401 — importados por sus side effects

# Importamos los routers que contienen los endpoints de la API
from app.routers import auth


# =============================================================================
# CREACIÓN DE TABLAS EN LA BASE DE DATOS
# =============================================================================
# Base.metadata.create_all() le dice a SQLAlchemy que cree en PostgreSQL
# todas las tablas que aún no existen, basándose en los modelos ORM que
# importamos arriba (User, Post).
#
# IMPORTANTE — Solo para DESARROLLO:
# Esta línea es práctica para empezar rápido, pero en un proyecto de producción
# real, las migraciones se manejan con Alembic. Alembic lleva un historial
# de cambios a la DB (como Git pero para el esquema de la DB), lo que permite
# hacer rollbacks y actualizaciones controladas sin perder datos.
# En la próxima fase integraremos Alembic para reemplazar esta línea.
#
# checkfirst=True: SQLAlchemy verifica si la tabla ya existe antes de crearla.
# Esto evita errores si volvemos a arrancar el servidor con tablas ya creadas.
Base.metadata.create_all(bind=engine)


# =============================================================================
# INSTANCIA DE LA APLICACIÓN FASTAPI
# =============================================================================
# FastAPI() crea la aplicación principal. Los parámetros que le pasamos
# se usan principalmente para generar la documentación interactiva en /docs.
app = FastAPI(
    title="STL Repository API",
    description=(
        "API RESTful para una plataforma de modelos 3D para impresión. "
        "Permite a los creadores compartir archivos STL y a la comunidad explorarlos."
    ),
    version="0.1.0",
    # docs_url: URL donde estará la documentación Swagger UI (interfaz gráfica)
    docs_url="/docs",
    # redoc_url: URL para la documentación alternativa ReDoc (más legible)
    redoc_url="/redoc"
)


# =============================================================================
# REGISTRO DE ROUTERS
# =============================================================================
# app.include_router() "monta" un router en la aplicación principal.
# Todos los endpoints definidos en auth.router estarán disponibles en la app.
#
# El prefix="/auth" ya está definido dentro del router, pero si quisiéramos
# añadir un prefijo global de versión (ej: /api/v1), lo haríamos aquí:
# app.include_router(auth.router, prefix="/api/v1")
app.include_router(auth.router)


# =============================================================================
# ENDPOINT RAÍZ — Health Check
# =============================================================================
# Un endpoint en "/" es una convención común en APIs para verificar
# rápidamente que el servidor está levantado y respondiendo.
# Los sistemas de monitoreo (como Kubernetes, AWS ELB) suelen llamar a
# este endpoint periódicamente para verificar la "salud" del servicio.
@app.get("/", tags=["Health Check"])
def health_check():
    """
    Endpoint de verificación de estado del servidor.
    Devuelve un mensaje simple para confirmar que la API está funcionando.
    """
    return {
        "status": "ok",
        "message": "STL Repository API está funcionando correctamente.",
        "version": "0.1.0",
        "docs": "/docs"
    }
