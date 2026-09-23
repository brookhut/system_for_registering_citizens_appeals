#!/usr/bin/env bash
#!/usr/bin/env python3
"""
Скрипт пересоздания базы данных и таблиц для PostgreSQL 16 (и выше).
Проверяет наличие базы данных appeals_db (или указанной в .env):
если база данных существует, она принудительно удаляется (с закрытием активных сессий)
и создается заново с нуля. Таблицы создаются заново, и инициализируется
встроенная учетная запись superadmin из .env.
"""

import sys
from urllib.parse import urlparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from app.config import Config
from app.database import init_db


def parse_db_config():
    db_name = getattr(Config, 'DB_NAME', 'appeals_db') or 'appeals_db'
    db_user = getattr(Config, 'DB_USER', 'postgres') or 'postgres'
    db_pass = getattr(Config, 'DB_PASSWORD', '') or ''
    db_host = getattr(Config, 'DB_HOST', 'localhost') or 'localhost'
    db_port = getattr(Config, 'DB_PORT', '5432') or '5432'

    # Парсим DATABASE_URL, если он задан
    if Config.DATABASE_URL:
        try:
            parsed = urlparse(Config.DATABASE_URL)
            if parsed.username:
                db_user = parsed.username
            if parsed.password:
                db_pass = parsed.password
            if parsed.hostname:
                db_host = parsed.hostname
            if parsed.port:
                db_port = str(parsed.port)
            if parsed.path and len(parsed.path) > 1:
                db_name = parsed.path.lstrip('/')
        except Exception:
            pass

    return db_name, db_user, db_pass, db_host, db_port


def recreate_database():
    db_name, db_user, db_pass, db_host, db_port = parse_db_config()

    print(f"=== Инициализация базы данных PostgreSQL 16 ===")
    print(f"Хост: {db_host}:{db_port}")
    print(f"Пользователь: {db_user}")
    print(f"Целевая БД: {db_name}")

    conn_params = {
        'dbname': 'postgres',
        'user': db_user,
        'host': db_host,
        'port': db_port
    }
    if db_pass:
        conn_params['password'] = db_pass

    # 1. Подключаемся к системной базе данных 'postgres' для управления базами
    conn = None
    try:
        conn = psycopg2.connect(**conn_params)
    except psycopg2.OperationalError as err:
        err_str = str(err)
        # Если соединение через TCP без пароля отклонено
        if 'no password supplied' in err_str or 'fe_sendauth' in err_str:
            # Пробуем подключиться через локальный UNIX-сокет без указания host
            try:
                unix_params = {'dbname': 'postgres', 'user': db_user}
                if db_pass:
                    unix_params['password'] = db_pass
                conn = psycopg2.connect(**unix_params)
            except Exception:
                print("\n" + "=" * 70, file=sys.stderr)
                print(" ОШИБКА АВТОРИЗАЦИИ POSTGRESQL: fe_sendauth: no password supplied", file=sys.stderr)
                print("=" * 70, file=sys.stderr)
                print(" В PostgreSQL для пользователя 'postgres' требуется пароль.", file=sys.stderr)
                print(" Задайте пароль пользователю 'postgres' в системе:", file=sys.stderr)
                print("   sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'postgres';\"", file=sys.stderr)
                print("\n И укажите этот пароль в файле .env:", file=sys.stderr)
                print("   DB_PASSWORD=postgres", file=sys.stderr)
                print("   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/appeals_db", file=sys.stderr)
                print("=" * 70 + "\n", file=sys.stderr)
                sys.exit(1)
        elif 'password authentication failed' in err_str:
            print("\n" + "=" * 70, file=sys.stderr)
            print(" ОШИБКА АВТОРИЗАЦИИ POSTGRESQL: неверный пароль пользователя!", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            print(" Убедитесь, что в файле .env указан правильный DB_PASSWORD.", file=sys.stderr)
            print(" Чтобы сбросить/задать пароль для 'postgres' в ОС, выполните:", file=sys.stderr)
            print("   sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'postgres';\"", file=sys.stderr)
            print(" И впишите в .env: DB_PASSWORD=postgres", file=sys.stderr)
            print("=" * 70 + "\n", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Ошибка при работе с PostgreSQL: {err}", file=sys.stderr)
            sys.exit(1)

    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Проверка наличия базы данных
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
        exists = cur.fetchone()

        if exists:
            print(f"База данных '{db_name}' уже существует. Удаление (DROP DATABASE WITH FORCE)...")
            try:
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE);')
            except Exception:
                cur.execute(f"""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid();
                """, (db_name,))
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}";')

            print(f"Предыдущая база данных '{db_name}' успешно удалена.")

        print(f"Создание чистой базы данных '{db_name}' (UTF-8)...")
        cur.execute(f'CREATE DATABASE "{db_name}" ENCODING \'UTF8\' TEMPLATE template1;')
        print(f"База данных '{db_name}' успешно создана.")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Ошибка при работе с PostgreSQL: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Создаем таблицы и инициализируем супер-администратора
    print("Создание таблиц и структуры базы данных...")
    init_db()
    print("Все таблицы успешно созданы.")
    print("Встроенный superadmin успешно инициализирован.")
    print("=== Инициализация завершена успешно! ===")


if __name__ == '__main__':
    recreate_database()
