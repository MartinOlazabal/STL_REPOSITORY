# =============================================================================
# database.py
# =============================================================================
# Este archivo es el "puente" entre FastAPI y PostgreSQL.
# Toda la configuración de SQLAlchemy vive aquí.
# SQLAlchemy es un ORM (Object Relational Mapper): nos permite trabajar con
# las tablas de la base de datos como si fueran clases de Python, sin
# necesidad de escribir SQL crudo para la mayoría de las operaciones.
# =============================================================================

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# -----------------------------------------------------------------------------
# PASO 1: Cargar la variable DATABASE_URL desde el archivo .env
# -----------------------------------------------------------------------------
# python-dotenv busca el archivo .env en el directorio raíz y carga sus
# variables como variables de entorno del sistema operativo.
# Esto es una buena práctica de seguridad: las credenciales nunca van
# hardcodeadas en el código fuente, no se suben a Git.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# DATABASE_URL tendrá el valor: "postgresql://usuario:password@host:puerto/nombre_db"
# Ejemplo: "postgresql://postgres:o98591394@localhost:5432/stl_db"

# -----------------------------------------------------------------------------
# PASO 2: Crear el Engine
# -----------------------------------------------------------------------------
# El "engine" es el objeto central de SQLAlchemy. Es el encargado de:
#   - Gestionar el pool de conexiones a la base de datos (un pool es un
#     conjunto de conexiones reutilizables para no abrir/cerrar una nueva
#     conexión en cada petición HTTP, lo cual sería muy lento).
#   - Traducir las operaciones Python a comandos SQL del dialecto correcto
#     (en este caso, PostgreSQL).
#
# El parámetro echo=False significa que SQLAlchemy NO imprimirá en consola
# todo el SQL que genera. Ponlo en True si quieres depurar las queries.
engine = create_engine(DATABASE_URL, echo=False)

# -----------------------------------------------------------------------------
# PASO 3: Crear la SessionLocal (Fábrica de Sesiones)
# -----------------------------------------------------------------------------
# Una "sesión" en SQLAlchemy es la unidad de trabajo con la base de datos.
# Piénsala como una transacción abierta: agrupa una serie de operaciones
# (consultas, inserciones, actualizaciones) y las confirma (commit) o
# deshace (rollback) juntas como una unidad atómica.
#
# sessionmaker() crea una "fábrica" — una clase que, al ser instanciada,
# produce sesiones con la configuración que le indicamos:
#   - autocommit=False: Los cambios NO se guardan automáticamente.
#                       Nosotros controlamos cuándo hacer commit().
#   - autoflush=False:  Los cambios no se envían a la DB antes del commit.
#   - bind=engine:      Le dice a qué motor de DB conectarse.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# -----------------------------------------------------------------------------
# PASO 4: Crear la clase Base
# -----------------------------------------------------------------------------
# Base es la clase padre de la que heredarán todos nuestros modelos ORM.
# SQLAlchemy usa esta herencia para saber qué clases representan tablas
# en la base de datos y gestionar su metadata (nombres de columnas, tipos, etc.).
Base = declarative_base()

# -----------------------------------------------------------------------------
# PASO 5: Función get_db() — La Dependencia de Base de Datos
# -----------------------------------------------------------------------------
# Esta función es un "generador" (usa yield) que FastAPI utiliza como
# "dependencia" (Dependency Injection).
#
# ¿Cómo funciona?
# 1. FastAPI llama a get_db() antes de ejecutar cada endpoint que la necesite.
# 2. get_db() abre una sesión de DB nueva.
# 3. Entrega esa sesión al endpoint con "yield" (el código PAUSA aquí).
# 4. El endpoint ejecuta su lógica usando la sesión.
# 5. Al terminar el endpoint, el control vuelve a get_db() y ejecuta el
#    bloque "finally", que SIEMPRE cierra la sesión, haya habido error o no.
#
# Esto garantiza que nunca tengamos "fugas de conexiones" a la base de datos.
def get_db():
    db = SessionLocal()  # Abre una nueva sesión
    try:
        yield db          # Entrega la sesión al endpoint
    finally:
        db.close()        # Cierra la sesión SIEMPRE, pase lo que pase
