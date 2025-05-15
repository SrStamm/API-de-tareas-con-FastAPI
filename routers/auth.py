from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from db.database import get_session, Session, select
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError
from models import db_models, schemas, exceptions
import os
from core.logger import logger
from core.limiter import limiter

router = APIRouter(tags=['Login'])

# Duracion de los tokens
ACCESS_TOKEN_DURATION = int(os.environ.get('ACCESS_TOKEN_DURATION'))
REFRESH_TOKEN_DURATION = int(os.environ.get('REFRESH_TOKEN_DURATION'))

ALGORITHM = os.environ.get('ALGORITHM')

SECRET = os.environ.get('SECRET_KEY')

crypt = CryptContext(schemes=["bcrypt"])

oauth2 = OAuth2PasswordBearer(tokenUrl='token', scheme_name='Bearer')

# Encriptacion de la contraseña
def encrypt_password(password: str):
    password = password.encode()
    return crypt.hash(password)

# Proceso de validacion de Token encriptado
async def auth_user(token: str = Depends(oauth2), session : Session = Depends(get_session)):
    try:
        # Decodifica el jwt
        payload = jwt.decode(token, SECRET, algorithms=ALGORITHM)
        
        # Verifica que sea un token de acceso
        scope = payload.get("scope")

        if not scope or scope != 'api_access':
            logger.error('No es un token de acceso')
            raise exceptions.InvalidToken()
        
        # Obtiene los datos necesarios
        user_id = payload.get("sub")
        
        if not user_id:
            logger.error('Token invalido')
            raise exceptions.InvalidToken()
    
        user = session.get(db_models.User, user_id)

        if not user:
            logger.error(f'No se encontro el user {user_id}')
            raise exceptions.UserNotFoundError(user_id)

        exp = payload.get("exp")

        if exp is None:
            logger.error('No tiene expiracion')
            raise exceptions.InvalidToken()

        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)

        if exp_datetime < datetime.now(timezone.utc):
            logger.error('Token expirado')
            raise exceptions.InvalidToken() 

        return user
    
    except JWTError:
        logger.error('Token invalido')
        raise exceptions.InvalidToken()
# @limiter.limit("5/minute")
async def auth_user_ws(token: str, session: Session):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        
        user_id: str = payload.get("sub")
        
        if user_id is None:
            return None
        
        user = session.get(db_models.User, int(user_id))
        
        if user is None:
            return None
        
        return user
    
    except JWTError as e:
        
        return None

@router.post("/login", description='Endpoint para logearse. Se necesita username y password.')
# @limiter.limit("5/minute")
async def login(form: OAuth2PasswordRequestForm = Depends(),
                session : Session = Depends(get_session)) -> schemas.Token:
    
    try:
        statement = select(db_models.User).where(db_models.User.username == form.username)
        user_found = session.exec(statement).first()

        if not user_found:
            logger.error('NO se encontro el usuario')
            raise exceptions.UserNotFoundInLogin()
        
        if not crypt.verify(form.password, user_found.password):
            logger.error('Contraseña incorrecta')
            raise exceptions.LoginError(user_id=user_found.user_id)

        # Tiempo de expiración de access y refresh
        access_expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_DURATION)

        refresh_expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DURATION)

        access_token = {
            "sub": str(user_found.user_id),
            "exp": access_expires.timestamp(),
            "scope": "api_access"
        }

        refresh_token = {
            "jti":'4864856',
            "sub":str(user_found.user_id),
            "exp":refresh_expires.timestamp(),
            "scope":'token_refresh'
        }
        
        encoded_access_token = jwt.encode(access_token, SECRET, algorithm=ALGORITHM)

        encoded_refresh_token = jwt.encode(refresh_token, SECRET, algorithm=ALGORITHM)

        return {"access_token" : encoded_access_token, "token_type" : "bearer", 'refresh_token': encoded_refresh_token}
    
    except SQLAlchemyError as e:
        logger.error('Error al iniciar sesion {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='login')


@router.post("/refresh", description='Endpoint para obtener un nuevo token. Se necesita refresh token.')
# @limiter.limit("5/minute")
async def refresh(
        refresh: str,
        session : Session = Depends(get_session)) -> schemas.Access_Token:
    try:
        # Desencripta el token
        payload = jwt.decode(refresh, SECRET, algorithms=ALGORITHM)

        # Obtiene el scope, caso sea incorrecto lanza error
        scope = payload.get("scope")

        if scope != 'token_refresh':
            logger.error('No es un token de refresco')
            raise exceptions.InvalidToken()

        # Obtiene user_id,  si no existe o no encuentra usuario, lanza error
        user_id = payload.get("sub")

        if not user_id:
            logger.error('Token invalido. No contiene id')
            raise exceptions.InvalidToken()

        user = session.get(db_models.User, user_id)

        if not user:
            logger.error(f'No se encontro el user {user_id}')
            raise exceptions.UserNotFoundError(user_id)

        # Obtiene la expiracion, si no tiene o ya expiro, lanza error 
        exp = payload.get("exp")

        if exp is None:
            logger.error('No tiene expiracion')
            raise exceptions.InvalidToken()

        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)

        if exp_datetime < datetime.now(timezone.utc):
            logger.error('Token expirado')
            raise exceptions.InvalidToken() 

        access_expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_DURATION)

        access_token = {
            "sub": str(user.user_id),
            "exp": access_expires.timestamp(),
            "scope": "api_access"
        }

        encoded_access_token = jwt.encode(access_token, SECRET, algorithm=ALGORITHM)

        return {"access_token" : encoded_access_token, "token_type" : "bearer"}
    
    except JWTError:
        logger.error('Token invalido')
        raise exceptions.InvalidToken()
    
    except SQLAlchemyError as e:
        logger.error('Error al iniciar sesion {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='login')