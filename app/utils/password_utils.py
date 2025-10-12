import jwt
import os
from passlib.context import CryptContext
from datetime import datetime, timedelta


SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(data: dict):
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    data_to_encode = data.copy()
    data_to_encode.update({'exp': expires_at})

    jwt_token = jwt.encode(data_to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return jwt_token
