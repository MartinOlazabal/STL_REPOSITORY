# =============================================================================
# crud/user.py
# =============================================================================
# CRUD = Create, Read, Update, Delete
#
# Este archivo contiene las FUNCIONES DE ACCESO A LA BASE DE DATOS para
# la entidad Usuario. Es la capa de "repositorio" o "data access layer".
#
# ¿Por qué separar la lógica de DB en una carpeta crud/?
# Principio de Responsabilidad Única (SRP de SOLID):
#   - Los ROUTERS (endpoints) solo deben manejar HTTP: recibir requests,
#     llamar a la lógica correspondiente y devolver responses.
#   - Las funciones CRUD solo se preocupan de hablar con la base de datos.
#
# Beneficio práctico: Si mañana cambiamos de PostgreSQL a MongoDB, solo
# tocamos este archivo — los routers no se enteran del cambio.
#
# DEPENDENCIAS:
#   - passlib: Librería para el manejo seguro de contraseñas.
#              Implementa bcrypt, el algoritmo estándar de la industria
#              para hashear contraseñas. Bcrypt es resistente a ataques
#              de fuerza bruta por su diseño deliberadamente lento.
# =============================================================================

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User
from app.schemas.user import UserCreate


# -----------------------------------------------------------------------------
# CONFIGURACIÓN DEL HASHING DE CONTRASEÑAS
# -----------------------------------------------------------------------------
# CryptContext es la fachada de passlib. Le indicamos:
#   - schemes=["bcrypt"]: Usar el algoritmo bcrypt para hashear.
#   - deprecated="auto": Si en el futuro cambiamos de algoritmo, passlib
#     puede re-hashear automáticamente los passwords viejos al login.
#
# ¿Por qué bcrypt y no MD5 o SHA256?
# MD5 y SHA256 son funciones de hash RÁPIDAS. Los atacantes pueden probar
# millones de contraseñas por segundo contra estos hashes. Bcrypt tiene un
# "factor de costo" ajustable que lo hace deliberadamente lento, haciendo
# los ataques de fuerza bruta prácticamente inviables.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -----------------------------------------------------------------------------
# FUNCIONES DE UTILIDAD DE CONTRASEÑAS
# -----------------------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su versión hasheada.
    
    Bcrypt es un hash UNIDIRECCIONAL: no se puede "desencriptar".
    Para verificar, bcrypt aplica el mismo proceso de hash al password ingresado
    y compara el resultado con el hash almacenado.
    
    Args:
        plain_password: La contraseña que escribió el usuario al hacer login.
        hashed_password: El hash almacenado en la DB para ese usuario.
    
    Returns:
        True si coinciden, False si no.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Toma una contraseña en texto plano y devuelve su hash bcrypt.
    
    El hash resultante incluye automáticamente el "salt" (un valor aleatorio
    que bcrypt agrega internamente). Esto garantiza que dos usuarios con la
    misma contraseña tengan hashes DISTINTOS en la DB, protegiéndonos contra
    ataques de "rainbow table".
    
    Args:
        password: La contraseña en texto plano que eligió el usuario.
    
    Returns:
        El hash bcrypt listo para guardar en la DB.
    """
    return pwd_context.hash(password)


# -----------------------------------------------------------------------------
# FUNCIONES DE CONSULTA (Read)
# -----------------------------------------------------------------------------

def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Busca un usuario en la DB por su email.
    
    La función recibe una sesión de DB (db) como parámetro en lugar de
    crearla internamente. Esto es el patrón de inyección de dependencias:
    quien llama a esta función es responsable de gestionar la sesión.
    Esto hace las funciones más fáciles de testear (podemos inyectar una
    sesión de DB de prueba en los tests unitarios).
    
    Args:
        db: La sesión activa de SQLAlchemy (viene del endpoint via get_db()).
        email: El email a buscar.
    
    Returns:
        El objeto User si existe, None si no se encontró.
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """
    Busca un usuario en la DB por su username.
    
    db.query(User): Inicia una query SELECT sobre la tabla 'users'.
    .filter(...):   Agrega una cláusula WHERE (equivalente SQL: WHERE username = 'valor').
    .first():       Ejecuta la query y devuelve la primera fila encontrada,
                    o None si no hay resultados (en lugar de lanzar una excepción).
    
    Args:
        db: La sesión activa de SQLAlchemy.
        username: El nombre de usuario a buscar.
    
    Returns:
        El objeto User si existe, None si no se encontró.
    """
    return db.query(User).filter(User.username == username).first()


# -----------------------------------------------------------------------------
# FUNCIONES DE ESCRITURA (Create)
# -----------------------------------------------------------------------------

def create_user(db: Session, user: UserCreate) -> User:
    """
    Crea un nuevo usuario en la base de datos.
    
    El flujo es:
    1. Hashear la contraseña (nunca guardar texto plano).
    2. Crear una instancia del modelo ORM User con los datos.
    3. Agregar la instancia a la sesión (esto no toca la DB todavía).
    4. Hacer commit (esto SÍ escribe en la DB de forma permanente).
    5. Refrescar el objeto para que SQLAlchemy lea los valores generados
       por la DB (como el id autoincremental y el created_at).
    
    Args:
        db: La sesión activa de SQLAlchemy.
        user: El schema UserCreate con los datos validados por Pydantic.
    
    Returns:
        El objeto User recién creado, con el id y created_at ya poblados.
    """
    # Paso 1: Hashear la contraseña antes de guardarla
    hashed_password = get_password_hash(user.password)

    # Paso 2: Crear la instancia del modelo ORM
    # Notamos que usamos user.username y user.email (del schema Pydantic),
    # pero en hashed_password usamos el hash, nunca user.password.
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
        # role e is_active toman sus valores default del modelo
    )

    # Paso 3: "Añadir" el objeto a la sesión (staged para el commit)
    db.add(db_user)

    # Paso 4: Confirmar la transacción — ESCRIBE en la DB
    db.commit()

    # Paso 5: Refrescar para obtener los valores generados por la DB
    # (principalmente el id autoincremental y el created_at)
    db.refresh(db_user)

    return db_user
