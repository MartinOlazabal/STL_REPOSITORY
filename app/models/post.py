# =============================================================================
# models/post.py
# =============================================================================
# Este archivo define el MODELO ORM para las publicaciones (posts).
#
# Cada "post" representa un modelo 3D publicado en la plataforma:
# incluye el título, descripción, y las RUTAS (no el contenido binario)
# de los archivos STL e imágenes asociados.
#
# REGLA FUNDAMENTAL DE ARQUITECTURA:
# Los archivos físicos (.stl, .jpg, .png) NUNCA se guardan en la base de datos.
# La DB solo almacena la ruta o URL donde están almacenados en disco o en la nube.
# Esto es una práctica universal en la industria: las DBs no están diseñadas
# para guardar binarios grandes; eso degrada el rendimiento gravemente.
# =============================================================================

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base


class Post(Base):
    """
    Modelo ORM para la tabla 'posts' en PostgreSQL.
    Cada fila de esta tabla representa un modelo 3D publicado por un usuario.
    """

    __tablename__ = "posts"

    # -------------------------------------------------------------------------
    # COLUMNAS BÁSICAS
    # -------------------------------------------------------------------------

    # Clave primaria autoincremental
    id = Column(Integer, primary_key=True, index=True)

    # Título del modelo 3D (ej: "Vaso con hexágonos", "Soporte de pared")
    title = Column(String(255), nullable=False)

    # Descripción larga: instrucciones de impresión, materiales recomendados,
    # configuración de slicer, etc. Usamos Text en lugar de String porque
    # puede ser muy largo y Text no tiene límite fijo de caracteres en PostgreSQL.
    description = Column(Text, nullable=True)

    # -------------------------------------------------------------------------
    # RUTAS DE ARCHIVOS
    # -------------------------------------------------------------------------
    # Estas columnas guardan únicamente la RUTA o URL del archivo, no el archivo.
    # Ejemplo de stl_file_url: "uploads/stl/vaso_hexagonos_user1.stl"
    # Ejemplo de image_url:    "uploads/images/vaso_hexagonos_preview.jpg"
    # En el futuro, cuando integremos S3, estas columnas guardarán URLs de la nube.

    stl_file_url = Column(String, nullable=True)   # Ruta al archivo .stl
    image_url = Column(String, nullable=True)       # Ruta a la imagen de muestra

    # -------------------------------------------------------------------------
    # CLAVE FORÁNEA (Foreign Key)
    # -------------------------------------------------------------------------
    # ForeignKey("users.id") crea la relación a nivel de BASE DE DATOS.
    # Le dice a PostgreSQL: "el valor de owner_id DEBE existir en la columna
    # id de la tabla users". Esto garantiza integridad referencial:
    # no puede existir un post cuyo autor no exista en la tabla de usuarios.
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Fecha de publicación del post
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # -------------------------------------------------------------------------
    # RELACIÓN CON EL MODELO USER
    # -------------------------------------------------------------------------
    # Esto es el complemento de la relación definida en User.
    # back_populates="posts" le dice a SQLAlchemy que el atributo "posts"
    # del modelo User es el "otro lado" de esta relación.
    # Con esto podemos hacer: post.owner para obtener el objeto User completo.
    owner = relationship("User", back_populates="posts")
