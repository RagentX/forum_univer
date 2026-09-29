## настройка БД 
- Установить MySQL 
- Из под root выполнить setup_mysql.sql


## Установка зависимостей

win
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```
linux/macOS
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
## Запуск

```bash
python -m uvicorn auth:app --port 8000
python -m uvicorn forum:app --port 8001
```

Swagger: http://127.0.0.1:8000/docs и http://127.0.0.1:8001/docs.

## Автоматическая проверка API

После установки зависимостей выполните `python test\_api.py` из папки проекта. Скрипт сам запустит сервисы на портах 18000 и 18001, создаст временные базы данных и проверит регистрацию, вход, темы, комментарии, обновление токена и запреты доступа. Успешный результат начинается с `OK:`. Порты 18000 и 18001 должны быть свободны.

