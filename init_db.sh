#!/usr/bin/env bash
set -e

# ==============================================================================
# Скрипт пересоздания базы данных и таблиц для PostgreSQL 16
# Проверяет наличие БД и таблиц: если они есть — удаляет и создает заново.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "  Пересоздание базы данных и структуры таблиц (PostgreSQL 16)"
echo "=========================================================="

# Проверка и выбор Python с установленными зависимостями
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
else
    if python3 -c "import psycopg2" 2>/dev/null; then
        PYTHON_CMD="python3"
    else
        echo "Модуль psycopg2 не найден. Создание виртуального окружения venv..."
        python3 -m venv "$SCRIPT_DIR/venv" 2>/dev/null || true
        if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
            # shellcheck disable=SC1091
            source "$SCRIPT_DIR/venv/bin/activate"
            PYTHON_CMD="$SCRIPT_DIR/venv/bin/python3"
            "$PYTHON_CMD" -m pip install -r requirements.txt
        else
            echo "ОШИБКА: Установите зависимости командой: pip install -r requirements.txt" >&2
            exit 1
        fi
    fi
fi

"$PYTHON_CMD" init_db.py
