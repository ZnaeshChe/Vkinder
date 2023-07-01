"""
Главный файл запуска
"""

import logging

from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.exceptions import ApiError
from vkinder import VKinderBot
from config import GROUP_TOKEN, CONNSTR, LOGGING_FILE

# переменные для работы
VK_BOT_TOKEN = GROUP_TOKEN
CONNECTION = CONNSTR


def setup_logging():
    """
    Логгирование
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(LOGGING_FILE), logging.StreamHandler()],
    )


def main():
    """
    Основная функция
    """
    # Инициализация логгирования
    setup_logging()

    # Инициализация бота
    vkinder_bot = VKinderBot(token=VK_BOT_TOKEN, connstr=CONNECTION)

    try:
        # Запуск Long Poll
        longpoll = VkLongPoll(vkinder_bot.session)
    except ApiError as error:
        logging.error(f"Ошибка при запуске Long Poll: {error}")
        return

    # Вывод сообщения о запуске
    logging.info("Бот запущен!")

    # Обработка сообщений
    for event in longpoll.listen():
        if (
            event.type == VkEventType.MESSAGE_NEW
            and event.to_me
            and event.from_user
            and event.text
        ):
            vkinder_bot.process_message(event)


if __name__ == "__main__":
    main()
