"""
Файл, содержащий необходимые переменные
"""

import configparser

# Объект парсера
config = configparser.ConfigParser()

if len(config.read("settings.ini")) == 0:
    print('Добавьте файл setings.ini\nПример файла -> example/settings.ini')
    exit()

# Токен пользователя
USER_TOKEN = config.get("settings", "user_token")
# Токен группы
GROUP_TOKEN = config.get("settings", "group_token")
# Файл для логгирования
LOGGING_FILE = config.get("settings", "logging_file")
# База данных
CONNSTR = config.get("database", "connstr")
