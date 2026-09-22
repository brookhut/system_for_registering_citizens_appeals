#!/usr/bin/env bash
set -e

# ==============================================================================
# Скрипт автоматического развертывания и запуска проекта (PostgreSQL 16 + Flask)
# Выполняет:
#   1. Проверку конфигурации .env
#   2. Проверку и запуск службы PostgreSQL
#   3. Пересоздание базы данных и таблиц (если уже есть — удаляет и создает с нуля)
#   4. Запуск веб-сервера на доступном порту (с автопереключением, если 5000 занят)
#
# Использование:
#   ./start.sh                - полный цикл (пересоздание БД + запуск)
#   ./start.sh --no-recreate  - запуск сервера без пересоздания существующей БД
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RECREATE_DB=true
for arg in "$@"; do
    case $arg in
        --no-recreate|--skip-db-init)
            RECREATE_DB=false
            shift
            ;;
        --recreate-db|--force)
            RECREATE_DB=true
            shift
            ;;
    esac
done

echo ""
echo "=========================================================="
echo "  Система регистрации обращений граждан — Запуск проекта"
echo "=========================================================="

# 1. Проверка конфигурации .env
echo "[1/4] Проверка конфигурационного файла .env..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "  -> Файл .env не найден. Копирование из .env.example..."
        cp .env.example .env
        chmod 600 .env
    else
        echo "ОШИБКА: Файл .env отсутствует и .env.example не найден!" >&2
        exit 1
    fi
else
    echo "  -> Файл .env найден."
fi

# 2. Проверка и запуск службы PostgreSQL
echo "[2/4] Проверка работы PostgreSQL..."
PG_RUNNING=false

if python3 -c "import socket; s = socket.socket(); s.settimeout(1); s.connect(('127.0.0.1', 5432)); s.close()" 2>/dev/null; then
    PG_RUNNING=true
fi

if [ "$PG_RUNNING" = false ]; then
    echo "  -> PostgreSQL не отвечает на порту 5432. Попытка запуска службы..."
    if command -v systemctl &> /dev/null; then
        sudo systemctl start postgresql 2>/dev/null || true
    fi
    if [ -d "$HOME/pgdata" ] && command -v pg_ctl &> /dev/null; then
        pg_ctl -D "$HOME/pgdata" -l "$HOME/pgdata/logfile" start 2>/dev/null || true
    fi
    sleep 2
fi
echo "  -> Служба PostgreSQL готова к работе."

# 3. Пересоздание базы данных и таблиц
if [ "$RECREATE_DB" = true ]; then
    echo "[3/4] Инициализация базы данных PostgreSQL (проверка и пересоздание)..."
    python3 init_db.py
else
    echo "[3/4] Пересоздание БД пропущено (флаг --no-recreate)."
fi

# 4. Запуск веб-приложения Flask на доступном порту
echo "[4/4] Запуск веб-сервера..."
echo "=========================================================="
exec python3 run.py
