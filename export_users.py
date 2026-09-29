"""Выгрузка пользователей из MySQL: python export_users.py [имя_файла.xlsx]."""
import os
import sys
from openpyxl import Workbook
from openpyxl.styles import Font
from database import db
from pathlib import Path

def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "users.xlsx"
    with db(os.getenv('AUTH_DB', 'forum_auth')) as con:
        users = con.execute('SELECT id, username FROM users ORDER BY id').fetchall()

    book = Workbook()
    sheet = book.active
    sheet.title = 'Пользователи'
    sheet.append(['ID', 'Логин'])
    for user in users:
        username = user['username']
        if username.startswith(('=', '+', '-', '@')):
            username = "'" + username
        sheet.append([user['id'], username])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.column_dimensions['A'].width = 12
    sheet.column_dimensions['B'].width = 32
    book.save(output)
    print(f'Выгружено пользователей: {len(users)}. Файл: {output}')


if __name__ == '__main__':
    main()
