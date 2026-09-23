#!/usr/bin/env bash
set -e

# ==============================================================================
# Скрипт удаления автозапуска проекта (удаление службы appeals.service)
# ==============================================================================

SERVICE_NAME="appeals.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"

echo ""
echo "========================================================================"
echo "  Удаление службы автозапуска проекта (${SERVICE_NAME})"
echo "========================================================================"

# Проверка прав администратора (sudo)
if [ "$EUID" -ne 0 ]; then
    echo "Для удаления системной службы требуются права администратора (sudo)."
    echo "Перезапуск с повышенными привилегиями..."
    exec sudo bash "$0" "$@"
fi

if command -v systemctl &> /dev/null; then
    echo "Остановка и отключение службы..."
    systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
fi

if [ -f "$SERVICE_PATH" ]; then
    rm -f "$SERVICE_PATH"
    echo "  -> Файл службы $SERVICE_PATH удален."
else
    echo "  -> Файл службы $SERVICE_PATH уже отсутствует."
fi

if command -v systemctl &> /dev/null; then
    systemctl daemon-reload 2>/dev/null || true
    systemctl reset-failed 2>/dev/null || true
fi

echo ""
echo "Служба ${SERVICE_NAME} успешно удалена из автозапуска системы."
echo "========================================================================"
