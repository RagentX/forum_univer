import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from common import make_token, check_token

app = FastAPI(title='Авторизация')
DB = os.getenv('AUTH_DB', 'auth.db')

@contextmanager
def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()

with db() as con:
    con.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS refresh_tokens (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL)')

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)

class Refresh(BaseModel):
    refresh_token: str

def password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 200_000).hex()

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def issue(con, user_id: int):
    access = make_token(user_id, 'access', 15)
    refresh = make_token(user_id, 'refresh', 60 * 24 * 7)
    # Уникальный refresh при повторном входе в одну секунду.
    refresh = refresh + '.' + secrets.token_urlsafe(16)
    con.execute('INSERT INTO refresh_tokens VALUES (?, ?)', (token_hash(refresh), user_id))
    return {'access_token': access, 'refresh_token': refresh, 'token_type': 'bearer'}

@app.post('/register', status_code=201)
def register(data: Credentials):
    salt = secrets.token_hex(16)
    try:
        with db() as con:
            cur = con.execute('INSERT INTO users(username, salt, password_hash) VALUES (?, ?, ?)',
                              (data.username, salt, password_hash(data.password, salt)))
            return {'id': cur.lastrowid, 'username': data.username}
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'Имя занято')

@app.post('/login')
def login(data: Credentials):
    with db() as con:
        user = con.execute('SELECT * FROM users WHERE username=?', (data.username,)).fetchone()
        if not user or not hmac.compare_digest(user['password_hash'], password_hash(data.password, user['salt'])):
            raise HTTPException(401, 'Неверный логин или пароль')
        return issue(con, user['id'])

@app.post('/refresh')
def refresh(data: Refresh):
    # Дополнительный суффикс служит одноразовым идентификатором в БД.
    token = data.refresh_token.rsplit('.', 1)[0]
    user_id = check_token(token, 'refresh')
    with db() as con:
        cur = con.execute('DELETE FROM refresh_tokens WHERE token_hash=? AND user_id=?',
                          (token_hash(data.refresh_token), user_id))
        if cur.rowcount != 1:
            raise HTTPException(401, 'Refresh токен уже использован')
        return issue(con, user_id)
