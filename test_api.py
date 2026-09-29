"""Запуск: python test_api.py (сервисы запускаются автоматически)."""
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from openpyxl import load_workbook

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
        env['JWT_SECRET'] = 'test-secret-only'
        try:
            for module, port in [('auth', '18000'), ('forum', '18001')]:
                processes.append(subprocess.Popen(
                    [sys.executable, '-m', 'uvicorn', f'{module}:app', '--host', '127.0.0.1', '--port', port],
                    cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE))
            ready(AUTH, processes[0])
            ready(FORUM, processes[1])

            user = {'username': 'test_' + uuid.uuid4().hex[:12], 'password': 'secret123'}
            status, _ = request('POST', AUTH + '/register', user)
            assert status == 201, 'Регистрация'
            status, tokens = request('POST', AUTH + '/login', user)
            assert status == 200 and tokens['access_token'] and tokens['refresh_token'], 'Вход'
            access = tokens['access_token']
            refresh = tokens['refresh_token']

            status, _ = request('POST', FORUM + '/topics', {'title': 'Тема', 'body': 'Текст'})
            assert status in (401, 403), 'Запрет создания темы без токена'
            status, topic = request('POST', FORUM + '/topics', {'title': 'Тема', 'body': 'Текст'}, access)
            assert status == 201 and topic['id'] > 0, 'Создание темы'
            topic_id = topic['id']
            status, comment = request('POST', FORUM + f'/topics/{topic_id}/comments', {'body': 'Ответ'}, access)
            assert status == 201 and comment['topic_id'] == topic_id, 'Комментарий'
            status, topics = request('GET', FORUM + '/topics')
            assert status == 200 and any(t['id'] == topic_id for t in topics), 'Список тем'
            status, topic = request('GET', FORUM + f'/topics/{topic_id}')
            assert status == 200 and topic['comments'][0]['body'] == 'Ответ', 'Тема с комментариями'

            status, new_tokens = request('POST', AUTH + '/refresh', {'refresh_token': refresh})
            assert status == 200 and new_tokens['refresh_token'] != refresh, 'Обновление токенов'
            status, _ = request('POST', AUTH + '/refresh', {'refresh_token': refresh})
            assert status == 401, 'Повторное использование refresh токена'
            status, _ = request('POST', FORUM + '/topics', {'title': 'Ещё', 'body': 'Текст'}, new_tokens['refresh_token'])
            assert status == 401, 'Refresh токен не подходит для API форума'
            report = str(Path(temp) / 'users.xlsx')
            subprocess.run([sys.executable, 'export_users.py', report], cwd=ROOT, env=env, check=True)
            book = load_workbook(report, read_only=True)
            assert any(row[1] == user['username'] for row in book.active.values), 'Экспорт пользователей'
            book.close()
            print('OK: регистрация, вход, темы, комментарии, refresh, доступ и Excel')
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
