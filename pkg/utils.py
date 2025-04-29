from passlib.context import CryptContext
import jwt
from .models import User
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
ALGORITHM = "HS256"


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    expared_at = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(data | {"exp": expared_at}, SECRET_KEY, algorithm=ALGORITHM)
