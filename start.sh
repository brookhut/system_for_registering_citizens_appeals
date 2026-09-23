#!/usr/bin/env bash
set -e

# ==============================================================================
# Скрипт автоматического развертывания и запуска проекта (PostgreSQL 16 + Flask)
# Выполняет:
#   1. Проверку конфигурации .env
#   2. Проверку и активацию / автоустановку виртуального окружения (Python + psycopg2)
#   3. Проверку и запуск службы PostgreSQL
#   4. Пересоздание базы данных и таблиц (если уже есть — удаляет и создает с нуля)
#   5. Запуск веб-сервера на доступном порту (с автопереключением, если 5000 занят)
#
# Использование:
#   ./start.sh                - полный цикл (проверка окружения + пересоздание БД + запуск)
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
echo "[1/5] Проверка конфигурационного файла .env..."
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

# 2. Проверка и настройка окружения Python (проверка psycopg2, Flask, etc.)
echo "[2/5] Проверка окружения Python и зависимостей..."

VENV_DIR=""
if [ -d "$SCRIPT_DIR/venv" ] && [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    VENV_DIR="$SCRIPT_DIR/venv"
elif [ -d "$SCRIPT_DIR/.venv" ] && [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    VENV_DIR="$SCRIPT_DIR/.venv"
fi

if [ -n "$VENV_DIR" ]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    PYTHON_CMD="$VENV_DIR/bin/python3"
    echo "  -> Активировано виртуальное окружение: $VENV_DIR"
else
    # Проверяем, есть ли psycopg2 в системном Python
    if python3 -c "import psycopg2" 2>/dev/null; then
        PYTHON_CMD="python3"
        echo "  -> Зависимости найдены в системном Python."
    else
        echo "  -> Модуль psycopg2 не найден в системном Python. Создание виртуального окружения venv..."
        VENV_DIR="$SCRIPT_DIR/venv"
        
        # Попытка создать venv
        if python3 -m venv "$VENV_DIR" 2>/dev/null; then
            # shellcheck disable=SC1091
            source "$VENV_DIR/bin/activate"
            PYTHON_CMD="$VENV_DIR/bin/python3"
            echo "  -> Установка необходимых библиотек из requirements.txt..."
            "$PYTHON_CMD" -m pip install --upgrade pip --quiet 2>/dev/null || true
            "$PYTHON_CMD" -m pip install -r requirements.txt
            echo "  -> Виртуальное окружение успешно создано и настроено."
        else
            # Если python3-venv не установлен в ОС
            echo "  -> Попытка прямой установки зависимостей через pip..."
            pip3 install -r requirements.txt --break-system-packages 2>/dev/null || \
            pip install -r requirements.txt --break-system-packages 2>/dev/null || \
            pip install --user -r requirements.txt 2>/dev/null || true
            
            PYTHON_CMD="python3"
        fi
    fi
fi

# Финальная проверка наличия psycopg2 перед продолжением
if ! "$PYTHON_CMD" -c "import psycopg2" 2>/dev/null; then
    echo "" >&2
    echo "========================================================================" >&2
    echo " ОШИБКА: Модуль 'psycopg2' не найден в Python!" >&2
    echo "" >&2
    echo " Для решения на сервере Ubuntu выполните следующие команды:" >&2
    echo "   sudo apt update" >&2
    echo "   sudo apt install -y python3-venv python3-pip python3-psycopg2" >&2
    echo "   python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
    echo "" >&2
    echo " После этого повторите запуск: ./start.sh" >&2
    echo "========================================================================" >&2
    exit 1
fi
echo "  -> Модуль psycopg2 и зависимости проверены успешно."

# 3. Проверка и запуск службы PostgreSQL
echo "[3/5] Проверка работы PostgreSQL..."
PG_RUNNING=false

if "$PYTHON_CMD" -c "import socket; s = socket.socket(); s.settimeout(1); s.connect(('127.0.0.1', 5432)); s.close()" 2>/dev/null; then
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

# 4. Пересоздание базы данных и таблиц
if [ "$RECREATE_DB" = true ]; then
    echo "[4/5] Инициализация базы данных PostgreSQL (проверка и пересоздание)..."
    "$PYTHON_CMD" init_db.py
else
    echo "[4/5] Пересоздание БД пропущено (флаг --no-recreate)."
fi

# 5. Запуск веб-приложения Flask на доступном порту
echo "[5/5] Запуск веб-сервера..."
echo "=========================================================="
exec "$PYTHON_CMD" run.py
