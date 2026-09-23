#!/usr/bin/env bash
set -e

# ==============================================================================
# Скрипт установки автозапуска проекта при старте или перезагрузке сервера
# Создает системную службу systemd (appeals.service)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="appeals.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"

echo ""
echo "========================================================================"
echo "  Настройка автоматического запуска проекта при включении/перезагрузке"
echo "========================================================================"

# Проверка прав администратора (sudo)
if [ "$EUID" -ne 0 ]; then
    echo "Для установки системной службы требуются права администратора (sudo)."
    echo "Перезапуск с повышенными привилегиями..."
    exec sudo bash "$0" "$@"
fi

# Определение пользователя, от имени которого должен запускаться сервис
REAL_USER="${SUDO_USER:-$USER}"
if [ "$REAL_USER" = "root" ]; then
    # Если запущен напрямую под root, берем владельца каталога проекта
    REAL_USER="$(stat -c '%U' "$SCRIPT_DIR" 2>/dev/null || echo "root")"
fi

REAL_GROUP="$(id -gn "$REAL_USER" 2>/dev/null || echo "$REAL_USER")"

echo "Параметры службы:"
echo "  Каталог проекта:  $SCRIPT_DIR"
echo "  Пользователь:     $REAL_USER"
echo "  Группа:           $REAL_GROUP"
echo "  Файл службы:      $SERVICE_PATH"
echo ""

# Проверяем наличие исполняемого файла start.sh
if [ ! -f "$SCRIPT_DIR/start.sh" ]; then
    echo "ОШИБКА: Файл start.sh не найден в $SCRIPT_DIR!" >&2
    exit 1
fi
chmod +x "$SCRIPT_DIR/start.sh"

# Создаем файл службы systemd
echo "Создание службы systemd: $SERVICE_PATH..."
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=Система регистрации обращений граждан (Citizens Appeals Management)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=${REAL_USER}
Group=${REAL_GROUP}
WorkingDirectory=${SCRIPT_DIR}
Environment="PATH=${SCRIPT_DIR}/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/bin/bash ${SCRIPT_DIR}/start.sh --no-recreate
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
TimeoutStartSec=60

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_PATH"
echo "  -> Файл службы $SERVICE_PATH успешно создан."

# Проверяем доступность systemd daemon
SYSTEMD_AVAILABLE=false
if command -v systemctl &> /dev/null; then
    if systemctl is-system-running &> /dev/null || [ -d /run/systemd/system ]; then
        SYSTEMD_AVAILABLE=true
    fi
fi

if [ "$SYSTEMD_AVAILABLE" = true ]; then
    echo "Применение изменений в systemd..."
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"
    echo "  -> Автозапуск службы ${SERVICE_NAME} включен."
    
    echo "Запуск службы ${SERVICE_NAME}..."
    systemctl restart "${SERVICE_NAME}"
    sleep 2
    
    echo ""
    echo "Статус службы:"
    systemctl status "${SERVICE_NAME}" --no-pager || true
else
    echo ""
    echo "Внимание: systemd не активен в текущем окружении (например, внутри docker-контейнера)."
    echo "Файл службы $SERVICE_PATH записан."
    echo "На хост-системе выполните команды для активации:"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable --now ${SERVICE_NAME}"
fi

echo ""
echo "========================================================================"
echo " Автозапуск успешно настроен!"
echo " Проект будет автоматически подниматься при загрузке и перезагрузке сервера."
echo ""
echo " Полезные команды для управления:"
echo "   Статус службы:   sudo systemctl status ${SERVICE_NAME}"
echo "   Остановить:      sudo systemctl stop ${SERVICE_NAME}"
echo "   Запустить:       sudo systemctl start ${SERVICE_NAME}"
echo "   Перезапустить:   sudo systemctl restart ${SERVICE_NAME}"
echo "   Смотреть логи:   sudo journalctl -u ${SERVICE_NAME} -f"
echo "   Удалить автозапуск: ./uninstall_autostart.sh"
echo "========================================================================"
