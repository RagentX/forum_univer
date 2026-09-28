import os
import sqlite3
from contextlib import contextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from common import check_token

app = FastAPI(title='Форум')
DB = os.getenv('FORUM_DB', 'forum.db')
security = HTTPBearer()

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
    con.execute('CREATE TABLE IF NOT EXISTS topics (id INTEGER PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, author_id INTEGER NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL, body TEXT NOT NULL, author_id INTEGER NOT NULL)')

def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    return check_token(credentials.credentials, 'access')

class Topic(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)

class Comment(BaseModel):
    body: str = Field(min_length=1)

@app.post('/topics', status_code=201)
def add_topic(data: Topic, user_id: int = Depends(current_user)):
    with db() as con:
        cur = con.execute('INSERT INTO topics(title, body, author_id) VALUES (?, ?, ?)',
                          (data.title, data.body, user_id))
        return {'id': cur.lastrowid, 'title': data.title, 'body': data.body, 'author_id': user_id}

@app.get('/topics')
def list_topics():
    with db() as con:
        return [dict(row) for row in con.execute('SELECT * FROM topics ORDER BY id DESC')]

@app.get('/topics/{topic_id}')
def get_topic(topic_id: int):
    with db() as con:
        topic = con.execute('SELECT * FROM topics WHERE id=?', (topic_id,)).fetchone()
        if not topic:
            raise HTTPException(404, 'Тема не найдена')
        result = dict(topic)
        result['comments'] = [dict(row) for row in con.execute('SELECT * FROM comments WHERE topic_id=? ORDER BY id', (topic_id,))]
        return result

@app.post('/topics/{topic_id}/comments', status_code=201)
def add_comment(topic_id: int, data: Comment, user_id: int = Depends(current_user)):
    with db() as con:
        if not con.execute('SELECT 1 FROM topics WHERE id=?', (topic_id,)).fetchone():
            raise HTTPException(404, 'Тема не найдена')
        cur = con.execute('INSERT INTO comments(topic_id, body, author_id) VALUES (?, ?, ?)',
                          (topic_id, data.body, user_id))
        return {'id': cur.lastrowid, 'topic_id': topic_id, 'body': data.body, 'author_id': user_id}
