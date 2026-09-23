#!/usr/bin/env bash
set -e

# ==============================================================================
# Скрипт создания выделенного пользователя базы данных PostgreSQL
# Создает пользователя (по умолчанию appeals_user) с правами CREATEDB
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
    # shellcheck disable=SC1091
    source .env 2>/dev/null || true
fi

TARGET_USER="${DB_USER:-appeals_user}"
TARGET_PASS="${DB_PASSWORD:-appeals_pass_2026}"

echo "=========================================================="
echo "  Создание пользователя PostgreSQL: $TARGET_USER"
echo "=========================================================="

SQL_CMD="DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$TARGET_USER') THEN
    CREATE ROLE \"$TARGET_USER\" WITH LOGIN PASSWORD '$TARGET_PASS' CREATEDB;
    RAISE NOTICE 'Пользователь % успешно создан.', '$TARGET_USER';
  ELSE
    ALTER ROLE \"$TARGET_USER\" WITH LOGIN PASSWORD '$TARGET_PASS' CREATEDB;
    RAISE NOTICE 'Пароль и права пользователя % обновлены.', '$TARGET_USER';
  END IF;
END
\$\$;"

# 1. Попытка через sudo -u postgres psql
if command -v sudo &>/dev/null && sudo -u postgres psql -c "$SQL_CMD" 2>/dev/null; then
    echo "  -> Пользователь '$TARGET_USER' успешно настроен через sudo -u postgres."
# 2. Попытка напрямую через psql от текущего пользователя
elif command -v psql &>/dev/null && psql -U postgres -d postgres -c "$SQL_CMD" 2>/dev/null; then
    echo "  -> Пользователь '$TARGET_USER' успешно настроен через psql."
else
    echo "Не удалось автоматически выполнить команду через sudo."
    echo "Выполните следующую команду вручную в терминале сервера:"
    echo ""
    echo "  sudo -u postgres psql -c \"CREATE USER $TARGET_USER WITH PASSWORD '$TARGET_PASS' CREATEDB;\""
    echo ""
fi

chmod +x "$0"
