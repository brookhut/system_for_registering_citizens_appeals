#!/usr/bin/env python3
"""
Скрипт пересоздания базы данных и таблиц для PostgreSQL 16 (и выше).
Проверяет наличие базы данных appeals_db (или указанной в .env):
если база данных существует, она принудительно удаляется (с закрытием активных сессий)
и создается заново с нуля. Таблицы создаются заново, и инициализируется
встроенная учетная запись superadmin из .env.
"""

import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from app.config import Config
from app.database import Base, engine, init_db, ensure_superadmin, db_session


def recreate_database():
    db_name = getattr(Config, 'DB_NAME', 'appeals_db')
    db_user = getattr(Config, 'DB_USER', 'postgres')
    db_pass = getattr(Config, 'DB_PASSWORD', '')
    db_host = getattr(Config, 'DB_HOST', 'localhost')
    db_port = getattr(Config, 'DB_PORT', '5432')

    # If DATABASE_URL is set, extract database name if needed
    if Config.DATABASE_URL and '/' in Config.DATABASE_URL:
        # e.g. postgresql://user:pass@host:5432/dbname
        db_name = Config.DATABASE_URL.split('/')[-1].split('?')[0]

    print(f"=== Инициализация базы данных PostgreSQL 16 ===")
    print(f"Хост: {db_host}:{db_port}")
    print(f"Пользователь: {db_user}")
    print(f"Целевая БД: {db_name}")

    # 1. Подключаемся к системной базе данных 'postgres' для управления базами
    try:
        conn = psycopg2.connect(
            dbname='postgres',
            user=db_user,
            password=db_pass,
            host=db_host,
            port=db_port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Проверка наличия базы данных
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
        exists = cur.fetchone()

        if exists:
            print(f"База данных '{db_name}' уже существует. Удаление (DROP DATABASE WITH FORCE)...")
            # PostgreSQL 13+ (включая 16) поддерживает WITH (FORCE) для сброса соединений
            try:
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE);')
            except Exception:
                # Резервный способ сброса сессий для старых версий
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
    print("Встроенный superadmin успешно инициализирован из .env.")
    print("=== Инициализация завершена успешно! ===")


if __name__ == '__main__':
    recreate_database()
