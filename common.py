import os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException

SECRET = os.getenv('JWT_SECRET', 'change-this-secret-for-real-use')
ALGORITHM = 'HS256'

def make_token(user_id: int, kind: str, minutes: int) -> str:
    return jwt.encode({'sub': str(user_id), 'type': kind,
                       'exp': datetime.now(timezone.utc) + timedelta(minutes=minutes)},
                      SECRET, algorithm=ALGORITHM)

def check_token(token: str, kind: str) -> int:
    try:
        data = jwt.decode(token, SECRET, algorithms=[ALGORITHM], options={'require': ['sub', 'type', 'exp']})
        if data['type'] != kind:
            raise ValueError('Неверный тип токена')
        return int(data['sub'])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail='Недействительный токен')
