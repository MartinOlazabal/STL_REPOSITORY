# =============================================================================
# routers/auth.py
# =============================================================================
# Este archivo define los ENDPOINTS de autenticación de la API.
#
# Un "router" en FastAPI es un módulo que agrupa endpoints relacionados.
# Funciona igual que app.get() / app.post(), pero permite organizar la API
# en módulos separados y luego "montar" cada router en la app principal.
#
# ¿Qué es un JWT (JSON Web Token)?
# Es un estándar (RFC 7519) para transmitir información de forma segura
# entre dos partes como un string firmado digitalmente.
# Estructura: header.payload.signature (tres partes separadas por puntos)
#   - Header:    algoritmo de firma + tipo de token
#   - Payload:   los datos que queremos transmitir (email, rol, expiración)
#   - Signature: garantiza que el token no fue alterado
#
# Flujo de autenticación:
# 1. Usuario se registra → se guarda en DB → recibe un JWT
# 2. Usuario hace login → credenciales verificadas → recibe un JWT
# 3. En peticiones futuras, el usuario envía el JWT en el header
# 4. El servidor verifica la firma del JWT → no necesita consultar la DB
#    para saber quién es el usuario (eso es la ventaja de los JWT stateless)
# =============================================================================

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session

from app.crud.user import create_user, get_user_by_email, get_user_by_username, verify_password
from app.database import get_db
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse

# Cargamos las variables de entorno para acceder a las claves secretas
load_dotenv()

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE JWT
# -----------------------------------------------------------------------------

# SECRET_KEY: La clave secreta que se usa para FIRMAR los tokens.
# Si alguien altera el payload del JWT, la firma ya no coincidirá y el
# servidor lo rechazará. Esta clave NUNCA debe ir en el código ni en Git.
# En producción debe ser una cadena larga y aleatoria (256 bits mínimo).
SECRET_KEY = os.getenv("SECRET_KEY", "CAMBIA_ESTA_CLAVE_EN_PRODUCCION_es_muy_insegura")

# ALGORITHM: El algoritmo criptográfico para firmar el JWT.
# HS256 = HMAC con SHA-256. Es simétrico: la misma clave firma y verifica.
# Para APIs con múltiples servicios, RS256 (asimétrico) es más seguro.
ALGORITHM = "HS256"

# ACCESS_TOKEN_EXPIRE_MINUTES: Cuántos minutos es válido el token.
# Después de este tiempo, el token expira y el usuario debe re-autenticarse.
# 30 minutos es un balance razonable entre UX y seguridad.
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# -----------------------------------------------------------------------------
# INSTANCIA DEL ROUTER
# -----------------------------------------------------------------------------
# APIRouter actúa como una "mini aplicación" FastAPI.
# prefix="/auth": Todos los endpoints de este router tendrán el prefijo /auth
#                 Ej: /auth/register, /auth/login
# tags=["auth"]: Agrupa estos endpoints bajo la etiqueta "auth" en /docs
router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)


# -----------------------------------------------------------------------------
# FUNCIÓN AUXILIAR: Crear un Access Token (JWT)
# -----------------------------------------------------------------------------

def create_access_token(data: dict) -> str:
    """
    Crea y firma un JWT con los datos del usuario.
    
    Args:
        data: Diccionario con los datos a incluir en el payload del token.
              Típicamente: {"sub": email_del_usuario}
              "sub" (subject) es un campo estándar del estándar JWT.
    
    Returns:
        El JWT como string (listo para enviar al cliente).
    """
    # Copiamos el dict para no mutar el original (buena práctica)
    to_encode = data.copy()

    # Calculamos la fecha/hora de expiración
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Añadimos el campo "exp" (expiration) al payload.
    # La librería jose verificará automáticamente este campo al decodificar.
    to_encode.update({"exp": expire})

    # jwt.encode() firma el payload con nuestra SECRET_KEY usando HS256
    # y devuelve el token completo como string: "header.payload.signature"
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


# =============================================================================
# ENDPOINT 1: POST /auth/register
# =============================================================================

@router.post(
    "/register",
    response_model=UserResponse,       # Schema que define la forma de la respuesta
    status_code=status.HTTP_201_CREATED  # 201 Created: recurso creado exitosamente
)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario en la plataforma.
    
    Flujo:
    1. FastAPI valida automáticamente el body de la petición contra UserCreate.
    2. Verificamos que el email no esté ya registrado.
    3. Verificamos que el username no esté ya en uso.
    4. Creamos el usuario en la DB (con la contraseña hasheada).
    5. Devolvemos los datos del usuario creado (sin contraseña).
    
    Args:
        user: Body de la petición, validado por Pydantic contra UserCreate.
        db: Sesión de DB inyectada automáticamente por FastAPI usando get_db().
            Depends(get_db) es el sistema de "Dependency Injection" de FastAPI.
    
    Raises:
        HTTPException 400: Si el email o username ya están en uso.
    
    Returns:
        El usuario recién creado, serializado según UserResponse.
    """
    # --- Verificación 1: ¿El email ya existe? ---
    existing_email = get_user_by_email(db, email=user.email)
    if existing_email:
        # HTTPException interrumpe la ejecución y devuelve una respuesta de error.
        # status_code=400: Bad Request — el cliente envió datos inválidos.
        # detail: El mensaje de error que verá el cliente en el JSON de respuesta.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este email ya está registrado."
        )

    # --- Verificación 2: ¿El username ya existe? ---
    existing_username = get_user_by_username(db, username=user.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este nombre de usuario ya está en uso."
        )

    # --- Crear el usuario en la DB ---
    # La función create_user maneja el hashing de la contraseña internamente.
    new_user = create_user(db=db, user=user)

    # Devolvemos el usuario creado. FastAPI lo serializa usando UserResponse,
    # que excluye el hashed_password automáticamente.
    return new_user


# =============================================================================
# ENDPOINT 2: POST /auth/login
# =============================================================================

@router.post(
    "/login",
    response_model=Token  # La respuesta será un objeto con access_token y token_type
)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Autentica un usuario y devuelve un JWT de acceso.
    
    Flujo:
    1. Buscamos al usuario por email en la DB.
    2. Verificamos la contraseña contra el hash almacenado.
    3. Si todo es correcto, generamos y devolvemos un JWT.
    
    NOTA DE SEGURIDAD: Los mensajes de error son GENÉRICOS intencionalmente.
    Si dijéramos "email no existe" vs "contraseña incorrecta", un atacante
    podría enumerar emails válidos en nuestra plataforma. Al decir siempre
    "credenciales inválidas" no le damos información útil al atacante.
    
    Args:
        credentials: Body de la petición con email y password.
        db: Sesión de DB inyectada por FastAPI.
    
    Returns:
        Un objeto Token con el access_token JWT y token_type "bearer".
    """
    # --- Buscar usuario por email ---
    user = get_user_by_email(db, email=credentials.email)

    # --- Verificar existencia y contraseña ---
    # Hacemos AMBAS verificaciones en un solo bloque if para no revelar
    # si el email existe o no (ver nota de seguridad arriba).
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,  # 401: No autenticado
            detail="Credenciales inválidas.",
            # WWW-Authenticate es un header estándar HTTP para indicar
            # al cliente qué esquema de autenticación debe usar.
            headers={"WWW-Authenticate": "Bearer"}
        )

    # --- Verificar que la cuenta esté activa ---
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,  # 403: Prohibido (autenticado pero sin acceso)
            detail="Cuenta desactivada. Contacta al administrador."
        )

    # --- Generar el JWT ---
    # El payload del token incluye el email del usuario como "sub" (subject).
    # Esto nos permite identificar al usuario cuando verifiquemos el token
    # en peticiones futuras, sin consultar la DB.
    access_token = create_access_token(data={"sub": user.email})

    # Devolvemos el token. FastAPI serializa esto usando el schema Token.
    return {"access_token": access_token, "token_type": "bearer"}
