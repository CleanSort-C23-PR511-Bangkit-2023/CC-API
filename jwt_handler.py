import jwt
from decouple import config
from datetime import datetime, timedelta
import time

def generate_token(user_id: str):
    payload = {
        "exp": datetime.utcnow() + timedelta(days=1),
        "iat": datetime.utcnow(),
        "userId": user_id
    }
    token = jwt.encode(payload, config("JWT_SECRET"), algorithm=config("JWT_ALGORITHM"))
    return token.decode('utf-8')

def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, config("JWT_SECRET"), algorithms=config("JWT_ALGORITHM"))
        return decoded_token if decoded_token["exp"] >= time.time() else None
    except:
        return {}