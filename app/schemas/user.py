# =============================================================================
# schemas/user.py
# =============================================================================
# Este archivo define los SCHEMAS PYDANTIC para los usuarios.
#
# ¿Qué es un schema Pydantic y para qué sirve?
# Pydantic es una librería de validación de datos. Un "schema" es una clase
# que describe la FORMA ESPERADA de los datos que entran o salen de la API.
#
# ¿Por qué separar los schemas ORM (models/) de los schemas Pydantic (schemas/)?
# - Los MODELOS ORM (SQLAlchemy) definen la estructura de la BASE DE DATOS.
# - Los SCHEMAS PYDANTIC definen la estructura de los datos de la API (request/response).
#
# Esta separación es crítica porque:
# 1. SEGURIDAD: Podemos excluir campos sensibles (ej: hashed_password) de
#    las respuestas de la API sin necesidad de lógica extra.
# 2. FLEXIBILIDAD: El schema de entrada puede tener campos distintos al modelo DB.
# 3. DOCUMENTACIÓN AUTOMÁTICA: FastAPI usa estos schemas para generar la
#    documentación interactiva en /docs (Swagger UI).
# 4. VALIDACIÓN AUTOMÁTICA: Si un campo llega con el tipo incorrecto,
#    FastAPI rechaza la petición automáticamente con un error 422.
# =============================================================================

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


# =============================================================================
# SCHEMAS DE ENTRADA (Request Body)
# Lo que la API espera RECIBIR del cliente (quien hace la petición HTTP)
# =============================================================================

class UserCreate(BaseModel):
    """
    Schema para el endpoint POST /auth/register.
    Define exactamente qué campos DEBE enviar el cliente para crear un usuario.
    Si falta algún campo requerido o el tipo no coincide, FastAPI devuelve
    automáticamente un error 422 Unprocessable Entity.

    EmailStr: tipo especial de Pydantic que valida que el string sea un
    email con formato válido (contiene @, dominio, etc.).
    """
    username: str
    email: EmailStr       # Pydantic valida automáticamente el formato del email
    password: str         # Contraseña en texto plano — se hasheará en el CRUD


class UserLogin(BaseModel):
    """
    Schema para el endpoint POST /auth/login.
    El usuario solo necesita email y contraseña para autenticarse.
    """
    email: EmailStr
    password: str         # Se comparará contra el hash almacenado en la DB


# =============================================================================
# SCHEMAS DE SALIDA (Response Model)
# Lo que la API devuelve AL cliente. Nunca debe contener datos sensibles.
# =============================================================================

class UserResponse(BaseModel):
    """
    Schema para las respuestas de la API cuando devolvemos datos de un usuario.
    
    IMPORTANTE: hashed_password NO está incluido aquí intencionalmente.
    Aunque el objeto User de la DB tenga ese campo, Pydantic solo incluirá
    en la respuesta JSON los campos definidos en este schema.
    Esto es la "serialización controlada" — una capa de seguridad fundamental.
    """
    id: int
    username: str
    email: str
    is_active: bool
    role: str
    created_at: datetime

    class Config:
        """
        La clase Config interna le dice a Pydantic cómo comportarse.
        
        from_attributes = True (antes llamado orm_mode = True en Pydantic v1):
        Le permite a Pydantic leer los datos directamente desde los atributos
        de un objeto ORM de SQLAlchemy, en lugar de solo desde diccionarios.
        Sin esto, si le pasamos un objeto User (SQLAlchemy) a este schema,
        Pydantic lanzaría un error porque no sabe leer objetos, solo dicts.
        """
        from_attributes = True


# =============================================================================
# SCHEMAS DE AUTENTICACIÓN (JWT)
# =============================================================================

class Token(BaseModel):
    """
    Schema para la respuesta del endpoint POST /auth/login.
    Cuando las credenciales son válidas, la API devuelve este objeto.
    
    access_token: El JWT (JSON Web Token) que el cliente debe guardar y
                  enviar en el header Authorization de cada petición futura.
    token_type:   Por convención HTTP/OAuth2, siempre es "bearer".
                  El cliente lo usa así: Authorization: Bearer <token>
    """
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Schema que representa el PAYLOAD decodificado de un JWT.
    Cuando recibimos un token en una petición, lo decodificamos y
    extraemos los datos del usuario que viajan dentro de él.
    
    Optional[str]: El email puede ser None si el token es inválido o
    no contiene el campo esperado.
    """
    email: Optional[str] = None
