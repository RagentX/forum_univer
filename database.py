"""Общий небольшой слой для MySQL; у сервисов разные базы."""
import os
from contextlib import contextmanager
import mysql.connector


class Connection:
    def __init__(self, name):
        self.raw = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', '127.0.0.1'),
            port=int(os.getenv('MYSQL_PORT', '3306')),
            user=os.getenv('MYSQL_USER', 'forum'),
            password=os.getenv('MYSQL_PASSWORD', 'forumpass'),
            database=name,
            charset='utf8mb4',
        )
        self.cursors = []

    def execute(self, query, params=()):
        cursor = self.raw.cursor(dictionary=True, buffered=True)
        cursor.execute(query, params)
        self.cursors.append(cursor)
        return cursor

    def close(self):
        for cursor in self.cursors:
            cursor.close()
        self.raw.close()


@contextmanager
def db(name):
    con = Connection(name)
    try:
        yield con
        con.raw.commit()
    except Exception:
        con.raw.rollback()
        raise
    finally:
        con.close()
