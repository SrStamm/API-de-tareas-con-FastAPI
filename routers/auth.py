from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from db.database import get_session, Session, select
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError
from models import db_models, schemas

router = APIRouter(tags=['Login'])

# Definimos el algoritmo
ALGORITHM = "HS256"

# Duracion de los tokens
ACCESS_TOKEN_DURATION = 60

# Definimos una llave secreta
SECRET = "MW6mdMOU8Ga58KSty8BYakM185zW857fZlTBqdmp1JkVih3qqr"

# Contexto de encriptacion 
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
        
        # Obtiene los datos necesarios
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    
        
        user = session.get(db_models.User, user_id)

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        return user
    
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/login", description='Endpoint para logearse. Se necesita username y password.')
async def login(form: OAuth2PasswordRequestForm = Depends(),
                session : Session = Depends(get_session)) -> schemas.Token:
    
    try:
        statement = select(db_models.User).where(db_models.User.username == form.username)
        user_found = session.exec(statement).first()

        print(user_found)

        if not user_found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Usuario no encontrado o no existe")
        
        if not crypt.verify(form.password, user_found.password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña incorrecta")

        access_expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_DURATION)

        access_token = {
            "sub": str(user_found.user_id),
            "exp": access_expires.timestamp()
        }
        
        encoded_access_token = jwt.encode(access_token, SECRET, algorithm=ALGORITHM)

        return {"access_token" : encoded_access_token, "token_type" : "bearer"}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Error al ingresar: {e}")