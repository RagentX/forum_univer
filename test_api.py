"""Запуск: python test_api.py (сервисы запускаются автоматически)."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
AUTH = 'http://127.0.0.1:18000'
FORUM = 'http://127.0.0.1:18001'


def request(method, url, data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    body = json.dumps(data).encode() if data is not None else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=3) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def ready(url, process):
    for _ in range(50):
        if process.poll() is not None:
            raise RuntimeError(f'Сервис завершился с кодом {process.returncode}')
        try:
            with urlopen(url + '/openapi.json', timeout=1):
                return
        except URLError:
            time.sleep(0.1)
    raise RuntimeError('Сервис не запустился')


def main():
    processes = []
    with tempfile.TemporaryDirectory() as temp:
        env = os.environ.copy()
        env['AUTH_DB'] = str(Path(temp) / 'auth.db')
        env['FORUM_DB'] = str(Path(temp) / 'forum.db')
        env['JWT_SECRET'] = 'test-secret-only'
        try:
            for module, port in [('auth', '18000'), ('forum', '18001')]:
                processes.append(subprocess.Popen(
                    [sys.executable, '-m', 'uvicorn', f'{module}:app', '--host', '127.0.0.1', '--port', port],
                    cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE))
            ready(AUTH, processes[0])
            ready(FORUM, processes[1])

            user = {'username': 'student', 'password': 'secret123'}
            status, _ = request('POST', AUTH + '/register', user)
            assert status == 201, 'Регистрация'
            status, tokens = request('POST', AUTH + '/login', user)
            assert status == 200 and tokens['access_token'] and tokens['refresh_token'], 'Вход'
            access = tokens['access_token']
            refresh = tokens['refresh_token']

            status, _ = request('POST', FORUM + '/topics', {'title': 'Тема', 'body': 'Текст'})
            assert status in (401, 403), 'Запрет создания темы без токена'
            status, topic = request('POST', FORUM + '/topics', {'title': 'Тема', 'body': 'Текст'}, access)
            assert status == 201 and topic['id'] == 1, 'Создание темы'
            status, comment = request('POST', FORUM + '/topics/1/comments', {'body': 'Ответ'}, access)
            assert status == 201 and comment['topic_id'] == 1, 'Комментарий'
            status, topics = request('GET', FORUM + '/topics')
            assert status == 200 and len(topics) == 1, 'Список тем'
            status, topic = request('GET', FORUM + '/topics/1')
            assert status == 200 and topic['comments'][0]['body'] == 'Ответ', 'Тема с комментариями'

            status, new_tokens = request('POST', AUTH + '/refresh', {'refresh_token': refresh})
            assert status == 200 and new_tokens['refresh_token'] != refresh, 'Обновление токенов'
            status, _ = request('POST', AUTH + '/refresh', {'refresh_token': refresh})
            assert status == 401, 'Повторное использование refresh токена'
            status, _ = request('POST', FORUM + '/topics', {'title': 'Ещё', 'body': 'Текст'}, new_tokens['refresh_token'])
            assert status == 401, 'Refresh токен не подходит для API форума'
            print('OK: регистрация, вход, темы, комментарии, refresh и проверки доступа')
        finally:
            for process in processes:
                process.terminate()
            for process in processes:
                try:
                    process.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()


if __name__ == '__main__':
    main()
