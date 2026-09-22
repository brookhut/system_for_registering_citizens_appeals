import os
import socket
import sys
from app import create_app
from app.config import Config

app = create_app()


def is_port_available(port: int, host: str = '0.0.0.0') -> bool:
    """
    Проверяет, доступен ли указанный порт для привязки сокета.
    Возвращает True, если порт свободен, и False, если занят.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(start_port: int = 5000, host: str = '0.0.0.0', max_attempts: int = 100) -> int:
    """
    Находит доступный свободный порт, начиная с start_port.
    Если порт занят, последовательно проверяет следующие порты.
    """
    current_port = start_port
    while current_port < start_port + max_attempts:
        if is_port_available(current_port, host):
            return current_port
        print(f"Порт {current_port} уже занят. Проверяем следующий порт...")
        current_port += 1
    raise RuntimeError(f"Не удалось найти свободный порт в диапазоне {start_port}–{start_port + max_attempts}")


if __name__ == '__main__':
    host = '0.0.0.0'
    requested_port = int(os.getenv('PORT', 5000))

    # Проверка доступности порта и автоматический выбор свободного
    port = find_available_port(start_port=requested_port, host=host)

    if port != requested_port:
        print(f"ВНИМАНИЕ: Запрошенный порт {requested_port} занят. Приложение будет запущено на свободном порту {port}.")
    else:
        print(f"Порт {port} свободен. Запуск приложения на http://{host}:{port}")

    # Запуск Flask-приложения на доступном порту
    app.run(host=host, port=port, debug=False)
