#!/usr/bin/env python3
"""
Скрипт пересоздания базы данных и таблиц для PostgreSQL 16 (и выше).
Использует выделенного пользователя базы данных (по умолчанию appeals_user).
Проверяет наличие базы данных appeals_db (или указанной в .env):
если база данных существует, она пересоздается (или все таблицы внутри очищаются и создаются с нуля).
Таблицы создаются заново, и инициализируется встроенная учетная запись superadmin из .env.
"""

import sys
from urllib.parse import urlparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from app.config import Config
from app.database import init_db


def parse_db_config():
    db_name = getattr(Config, 'DB_NAME', 'appeals_db') or 'appeals_db'
    db_user = getattr(Config, 'DB_USER', 'appeals_user') or 'appeals_user'
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


def get_maintenance_connection(db_user, db_pass, db_host, db_port):
    for maint_db in ('template1', 'postgres'):
        conn_params = {
            'dbname': maint_db,
            'user': db_user,
            'host': db_host,
            'port': db_port
        }
        if db_pass:
            conn_params['password'] = db_pass

        try:
            conn = psycopg2.connect(**conn_params)
            return conn, maint_db
        except psycopg2.OperationalError as e:
            err_str = str(e)
            if 'password authentication failed' in err_str or ('role' in err_str and 'does not exist' in err_str):
                raise e
            continue
    raise psycopg2.OperationalError("Не удалось подключиться к служебной базе данных (template1/postgres)")


def drop_all_tables_in_db(db_name, db_user, db_pass, db_host, db_port):
    """Очищает все таблицы в целевой БД каскадно."""
    conn_params = {
        'dbname': db_name,
        'user': db_user,
        'host': db_host,
        'port': db_port
    }
    if db_pass:
        conn_params['password'] = db_pass

    conn = psycopg2.connect(**conn_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("""
        DROP TABLE IF EXISTS appeals CASCADE;
        DROP TABLE IF EXISTS management_plots CASCADE;
        DROP TABLE IF EXISTS management_districts CASCADE;
        DROP TABLE IF EXISTS results CASCADE;
        DROP TABLE IF EXISTS topics CASCADE;
        DROP TABLE IF EXISTS appeal_types CASCADE;
        DROP TABLE IF EXISTS plots CASCADE;
        DROP TABLE IF EXISTS managements CASCADE;
        DROP TABLE IF EXISTS districts CASCADE;
        DROP TABLE IF EXISTS sources CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
    """)
    cur.close()
    conn.close()


def recreate_database():
    db_name, db_user, db_pass, db_host, db_port = parse_db_config()

    print(f"=== Инициализация базы данных PostgreSQL 16 ===")
    print(f"Хост: {db_host}:{db_port}")
    print(f"Пользователь БД: {db_user}")
    print(f"Целевая БД: {db_name}")

    conn = None
    try:
        conn, maint_db = get_maintenance_connection(db_user, db_pass, db_host, db_port)
    except psycopg2.OperationalError as err:
        err_str = str(err)
        print("\n" + "=" * 70, file=sys.stderr)
        if 'role' in err_str and 'does not exist' in err_str:
            print(f" ОШИБКА: Пользователь БД '{db_user}' еще не создан в PostgreSQL!", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            print(f" Создайте пользователя '{db_user}' одной командой в Ubuntu:", file=sys.stderr)
            print(f"   sudo -u postgres psql -c \"CREATE USER {db_user} WITH PASSWORD '{db_pass}' CREATEDB;\"", file=sys.stderr)
        elif 'password authentication failed' in err_str:
            print(f" ОШИБКА: Неверный пароль для пользователя БД '{db_user}'!", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            print(" Убедитесь, что в файле .env указан верный DB_PASSWORD.", file=sys.stderr)
            print(f" Чтобы сменить пароль в PostgreSQL, выполните:", file=sys.stderr)
            print(f"   sudo -u postgres psql -c \"ALTER USER {db_user} WITH PASSWORD '{db_pass}';\"", file=sys.stderr)
        elif 'no password supplied' in err_str or 'fe_sendauth' in err_str:
            print(f" ОШИБКА: В файле .env не указан пароль DB_PASSWORD!", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            print(" Укажите пароль в файле .env (переменные DB_PASSWORD и DATABASE_URL).", file=sys.stderr)
        else:
            print(f" Ошибка подключения к PostgreSQL: {err}", file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)
        sys.exit(1)

    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Проверка наличия целевой базы данных
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
        exists = cur.fetchone()

        if exists:
            print(f"База данных '{db_name}' уже существует. Пересоздание...")
            dropped = False
            try:
                cur.execute(f'DROP DATABASE "{db_name}" WITH (FORCE);')
                dropped = True
                print(f"Предыдущая база данных '{db_name}' удалена.")
            except Exception:
                pass

            if not dropped:
                # Если drop database заблокирован активными сессиями других пользователей,
                # очищаем все существующие таблицы напрямую каскадно
                print(f"Очистка всех существующих таблиц в '{db_name}' (DROP TABLES CASCADE)...")
                drop_all_tables_in_db(db_name, db_user, db_pass, db_host, db_port)
                print(f"Все существующие таблицы в '{db_name}' очищены.")
            else:
                print(f"Создание чистой базы данных '{db_name}' (UTF-8, владелец {db_user})...")
                cur.execute(f'CREATE DATABASE "{db_name}" OWNER "{db_user}" ENCODING \'UTF8\' TEMPLATE template1;')
                print(f"База данных '{db_name}' успешно создана.")
        else:
            print(f"Создание чистой базы данных '{db_name}' (UTF-8, владелец {db_user})...")
            cur.execute(f'CREATE DATABASE "{db_name}" OWNER "{db_user}" ENCODING \'UTF8\' TEMPLATE template1;')
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
