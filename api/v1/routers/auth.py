from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from db.database import get_session, Session, select, or_
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError
from models import db_models, schemas, exceptions, responses
import os
from core.logger import logger
from core.limiter import limiter
import uuid

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

@router.post("/login", description='Login path. You need a username and password. First need to create a user')
# @limiter.limit("5/minute")
async def login(form: OAuth2PasswordRequestForm = Depends(),
                session : Session = Depends(get_session)) -> schemas.Token:
    
    try:
        stmt = select(db_models.User).where(db_models.User.username == form.username)
        user_found = session.exec(stmt).first()

        if not user_found:
            logger.error('NO se encontro el usuario')
            raise exceptions.UserNotFoundInLogin()

        if not crypt.verify(form.password, user_found.password):
            logger.error('Contraseña incorrecta')
            raise exceptions.LoginError(user_id=user_found.user_id)

        # Tiempo de expiración de access
        access_expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_DURATION)

        access_token = {
            "sub": str(user_found.user_id),
            "exp": int(access_expires.timestamp()),
            "scope": "api_access"
        }

        encoded_access_token = jwt.encode(access_token, SECRET, algorithm=ALGORITHM)

        # Tiempo de expiración de refresh
        new_session = db_models.Session(
            jti= str(uuid.uuid4()),
            sub= str(user_found.user_id),
            expires_at= datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DURATION),
        )

        session.add(new_session)
        session.commit()
        session.refresh(new_session)

        refresh_token = {
            "jti":new_session.jti,
            "sub":new_session.sub,
            "exp":int(new_session.expires_at.timestamp()),
            "scope":'token_refresh'}

        encoded_refresh_token = jwt.encode(refresh_token, SECRET, algorithm=ALGORITHM)

        return {"access_token" : encoded_access_token, "token_type" : "bearer", 'refresh_token': encoded_refresh_token}

    except SQLAlchemyError as e:
        logger.error('Error al iniciar sesion {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='login')

@router.post(
            "/refresh",
            description='Refresh path for obtain a new token. You need a refresh token.',
            responses={
                200:{'detail':'New access_token and refresh_token obtained', 'model':schemas.Token},
                401:{'detail':'Token incorrect', 'model':responses.InvalidToken},
                404:{'detail':'User not found', 'model':responses.NotFound},
                500:{'detail':'Internal error', 'model': responses.DatabaseErrorResponse}
            })
@limiter.limit("5/minute")
async def refresh(
        refresh: schemas.RefreshTokenRequest,
        request: Request,
        session : Session = Depends(get_session)) -> schemas.Token:
    try:
        # Desencripta el token
        unverified_payload = jwt.get_unverified_claims(refresh)
        jti = unverified_payload.get("jti")
        
        # Verifica que exista la sesion y este activa
        stmt = ( select(db_models.Session).where(
                db_models.Session.jti == jti,
                db_models.Session.is_active == True))       
        actual_session = session.exec(stmt).first()

        if not actual_session:
            logger.error(f'No se encontró sesión activa para jti={jti}')
            raise exceptions.InvalidToken()
        
        payload = jwt.decode(refresh, SECRET, algorithms=ALGORITHM)

        # Obtiene el scope, caso sea incorrecto lanza error
        scope = payload.get("scope")

        if not scope:
            logger.error('No tiene Scope')
            raise exceptions.InvalidToken()

        if scope != 'token_refresh':
            logger.error(f'Scope inválido: {scope}')
            raise exceptions.InvalidToken()

        # Obtiene user_id,  si no existe o no encuentra usuario, lanza error
        user_id = payload.get("sub")
        
        if not user_id:
            logger.error('No tiene ID de Usuario')
            raise exceptions.InvalidToken()

        user = session.get(db_models.User, user_id)

        if not user:
            logger.error(f'Usuario con ID {user_id} no encontrado')
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

        # Invalidar la sesion actual
        session.delete(actual_session)

        # Creación del nuevo token
        access_expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_DURATION)

        access_token = {
            "sub": str(user.user_id),
            "exp": access_expires.timestamp(),
            "scope": "api_access"
        }
        encoded_access_token = jwt.encode(access_token, SECRET, algorithm=ALGORITHM)

        # Creacion de la nueva sesion
        new_session = db_models.Session(
            jti= str(uuid.uuid4()),
            sub= str(user.user_id),
            expires_at= datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DURATION),
        )

        session.add(new_session)
        session.commit()
        session.refresh(new_session)
        
        refresh_token = {
            "jti":new_session.jti,
            "sub":new_session.sub,
            "exp":new_session.expires_at.timestamp(),
            "scope":'token_refresh'}

        encoded_refresh_token = jwt.encode(refresh_token, SECRET, algorithm=ALGORITHM)
        token_data = {"access_token" : encoded_access_token, "token_type" : "bearer", "refresh_token": encoded_refresh_token}
        return schemas.Token(**token_data)
    
    except JWTError as e:
        logger.error(f'Token invalido durante refresh: Error message: {str(e)}')
        if hasattr(e, 'claims'):
            logger.error(f'Problematic claims: {e.claims}')
        raise exceptions.InvalidToken()
    
    except SQLAlchemyError as e:
        logger.error('Error al renovar el token {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='refresh')

@router.post(
            "/logout",
            description='Logout path to close session. Close all user sessions ',
            responses={
                200: {'description':'All user sesisons are closed.'},
                500:{'detail':'Internal error', 'model':responses.DatabaseErrorResponse}
            })
@limiter.limit("5/minute")
async def logout(
        request: Request,
        session : Session = Depends(get_session),
        user: db_models.User = Depends(auth_user)):
    try:
        # Busca las sesiones activas
        stmt = ( select(db_models.Session).where(
                db_models.Session.sub == str(user.user_id),
                db_models.Session.is_active == True))

        active_sessions = session.exec(stmt).all()

        if not active_sessions:
            logger.error(f'User {user.user_id} no tenia sesiones activas')
            raise exceptions.SessionNotFound(user.user_id)

        # Invalidar las sesiones actuales
        for individual_session in active_sessions:
            session.delete(individual_session)

        session.commit()

        logger.info(f'User {user.user_id} cerró {len(active_sessions)} sesiones')
        return {"detail":'Cerradas todas las sesiones'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al cerrar sesion: {str(e)}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='logout')

@router.get('/expired')
def get_expired_sessions(
        session: Session = Depends(get_session)):
    try:
        stmt = (select(db_models.Session.sub, db_models.Session.is_active, db_models.Session.expires_at)
                .where(or_(db_models.Session.is_active == False,
                            db_models.Session.expires_at < datetime.now(timezone.utc))))

        results = session.exec(stmt).all()

        if results:
            return results
        
        return {'detail':'No hay sesiones expiradas'}
    except SQLAlchemyError as e:
        raise exceptions.DatabaseError(e, func='get_expired_sessions')