# =============================================================================
# models/user.py
# =============================================================================
# Este archivo define el MODELO ORM del usuario.
#
# ¿Qué es un modelo ORM?
# Es una clase de Python que SQLAlchemy mapea directamente a una tabla de
# PostgreSQL. Cada instancia de esta clase representa una fila en esa tabla.
# Cada atributo de clase (Column) representa una columna.
#
# En la industria, separar los modelos ORM de los schemas de validación
# (Pydantic) es una práctica fundamental. Los modelos definen la ESTRUCTURA
# de la DB; los schemas definen la FORMA de los datos en la API.
# =============================================================================

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

# Importamos Base desde database.py — esta es la clase padre de todos los modelos
from app.database import Base


class User(Base):
    """
    Modelo ORM para la tabla 'users' en PostgreSQL.
    Hereda de Base para que SQLAlchemy lo registre y pueda crear la tabla.
    """

    # -------------------------------------------------------------------------
    # __tablename__: Le dice a SQLAlchemy cuál es el nombre real de la
    # tabla en PostgreSQL. Por convención se usa plural y snake_case.
    # -------------------------------------------------------------------------
    __tablename__ = "users"

    # -------------------------------------------------------------------------
    # COLUMNAS DE LA TABLA
    # Cada Column() define una columna con su tipo de dato y restricciones.
    # -------------------------------------------------------------------------

    # Clave primaria: identificador único autoincremental para cada usuario.
    # index=True crea un índice en la DB, acelerando las búsquedas por id.
    id = Column(Integer, primary_key=True, index=True)

    # Nombre de usuario público. unique=True garantiza que no haya dos
    # usuarios con el mismo username a nivel de base de datos (segunda
    # línea de defensa, la primera la hacemos en el código).
    username = Column(String, unique=True, index=True, nullable=False)

    # Email del usuario. También único e indexado para búsquedas rápidas.
    email = Column(String, unique=True, index=True, nullable=False)

    # Contraseña hasheada. NUNCA almacenamos contraseñas en texto plano.
    # El valor aquí es el resultado de pasar la contraseña por bcrypt.
    # nullable=False significa que esta columna NO puede quedar vacía.
    hashed_password = Column(String, nullable=False)

    # Indica si la cuenta está activa. Útil para "banear" o "desactivar"
    # usuarios sin eliminarlos de la DB (soft delete pattern).
    is_active = Column(Boolean, default=True)

    # Rol del usuario en la plataforma.
    # Valores posibles: "user" (usuario regular) o "admin" (administrador).
    role = Column(String, default="user")

    # Fecha y hora en que se creó el registro.
    # datetime.now(timezone.utc) captura el momento exacto de la inserción
    # usando UTC, que es el estándar en APIs para evitar confusiones de zona horaria.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # -------------------------------------------------------------------------
    # RELACIONES (Relationships)
    # -------------------------------------------------------------------------
    # relationship() define la relación lógica entre tablas A NIVEL DE PYTHON.
    # No crea columnas en la DB, pero permite acceder a los posts de un usuario
    # haciendo simplemente: usuario.posts (SQLAlchemy hace el JOIN internamente).
    #
    # back_populates="owner" indica que en el modelo Post existe un atributo
    # llamado "owner" que apunta de vuelta a este User. Esto crea la
    # relación bidireccional: user.posts y post.owner.
    posts = relationship("Post", back_populates="owner")
