"""
Функции для работы бота
"""
# pylint: disable = import-error, invalid-name, line-too-long
import logging
import sys

import vk_api

from vk_api.exceptions import ApiError

import messages
from db_utils import Saver
from config import USER_TOKEN

# Токен пользователя для поиска
VK_USER_TOKEN = USER_TOKEN


class VKinder:
    """
    Класс для поиска пользователей
    """

    def __init__(self, token):
        self.session = self.get_vk_session(token)
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def get_vk_session(token):
        """
        Получение сессии ВК
        :param token: Токен пользователя
        :return: Объект сессии, None при ошибке
        """
        try:
            session = vk_api.VkApi(token=token)
        except vk_api.exceptions.ApiError as error:
            logging.error(f"Ошибка создании сессии ВК пользователя: {error}")
            return None
        except vk_api.exceptions.LoginRequired as error:
            logging.error(f"Ошибка создании сессии ВК пользователя: {error}")
            return None
        return session

    def search_users(self, age, gender, city, status, count=50, offset=0):
        """
        Поиск по критериям
        :param age:    Возраст
        :param gender: Пол
        :param city:   Город
        :param status: Семейное положение
        :param count:  Количество пользователей
        :param offset: Смещение
        :return:       Список пользователей
        """
        api = self.session.get_api()

        try:
            users = api.users.search(
                count=count,
                age_from=age,
                age_to=age,
                sex=gender,
                city=city,
                status=status,
                offset=offset,
                fields="photo_id"
            )
        except vk_api.exceptions.ApiError as e:
            logging.error(f"Ошибка при поиске пользователей: {e}")
            return None

        return users["items"]

    def get_photo_popularity(self, photo_id):
        """
        Подсчет популярности фото
        :param photo_id: Id фото
        :return: Количество лайков и комментариев
        """
        api = self.session.get_api()
        try:
            photo_data = api.photos.getById(photos=photo_id)[0]
        except vk_api.exceptions.ApiError as e:
            logging.error(f"Ошибка при получении информации о фото: {e}")
            return 0

        return photo_data["likes"]["count"] + photo_data["comments"]["count"]

    def get_top_photos(self, user_id, top_count=3):
        """
        Получение топ n фото
        :param user_id: Id пользователя
        :param top_count: Количество фото
        :return: Топ n фото
        """
        api = self.session.get_api()
        try:
            # Получаем фото пользователя
            photos = api.photos.getAll(owner_id=user_id, extended=1)
            if photos['count'] == 0:
                return None
            # Сортируем по популярности
            popular_photos = sorted(
                photos["items"], key=lambda x: x["likes"]["count"], reverse=True
            )
            # Возвращаем топ n фото
            top_photos = popular_photos[:top_count]
            # Получаем фото, где пользователь отмечен
            tagged_photos = [photo for photo in photos["items"] if photo.get("tags")]
            # Сортируем по популярности
            tagged_photos = sorted(tagged_photos, key=lambda x: x["likes"]["count"], reverse=True)
            # Добавляем к топ-фото
            top_photos += tagged_photos[:top_count - len(top_photos)]
            return top_photos
        except vk_api.exceptions.ApiError as e:
            logging.error(f"Ошибка при получении фото пользователя: {e}")
            return None


class VKinderBot:
    """
    Бот для группы
    """
    def __init__(self, token, **kwargs):
        self.session = self.get_vk_session(token)
        self.api = self.session.get_api()
        self.vkinder = None

        # Количество сохраняемых пользователей за один поиск
        self.top_users = 5

        # Кэш локальный и базы данных
        self.user_data_cache = {}
        self.user_data = Saver(**kwargs)

        token = VK_USER_TOKEN
        try:
            self.vkinder = VKinder(token)
        except Exception as error:
            logging.error(error)
            sys.exit(1)

        # Состояния при работе с пользователем
        self.step_handlers = {
            None: self.process_age,
            "age": self.process_gender,
            "gender": self.process_city,
            "city": self.process_status,
            "status": self.handle_search_users,
            "final": self.handle_final_step,
            "again": self.process_age
        }

    def send_photos_and_link(self, user_id, photos, link):
        """
        Отправляет фотографии и ссылку на пользователя ВКонтакте.

        :param user_id: int, идентификатор пользователя, которому отправлять сообщение.
        :param photos:  список фотографий.
        :param link:    str, ссылка на пользователя ВКонтакте.
        """
        attachments = ",".join([f"photo{photo['owner_id']}_{photo['id']}" for photo in photos])
        self.api.messages.send(user_id=user_id, attachment=attachments, message=link, random_id=0)

    def send_message(self, user_id, message):
        """
        Отправка сообщения

        :param user_id: Id пользователя
        :param message: Сообщение
        """
        try:
            self.api.messages.send(user_id=user_id, message=message, random_id=0)
        except ApiError:
            # Если ошибка `Flood control`, пропускаем
            pass

    def process_age(self, user_id, *args):
        """
        Ввод года
        :param user_id: Id пользователя
        :return:        Статус пользователя в боте
        """
        self.send_message(user_id, messages.process_age)
        return "age"

    def process_gender(self, user_id, *args):
        """
        Ввод пола
        :param user_id: Id пользователя
        :return:        Статус пользователя в боте
        """
        self.send_message(user_id, messages.process_gender)
        return "gender"

    def process_city(self, user_id, *args):
        """
        Ввод города
        :param user_id: Id пользователя
        :return:        Статус пользователя в боте
        """
        self.send_message(user_id, messages.process_city)
        return "city"

    def process_status(self, user_id, *args):
        """
        Ввод семейного положения
        :param user_id: Id пользователя
        :return:        Статус пользователя в боте
        """
        self.send_message(user_id, messages.process_status)
        return "status"

    def get_next_profile(self, user_id):
        """
        Возвращает следующую анкету из сохраненных для данного пользователя.

        :param user_id: int, идентификатор пользователя.
        :return: dict, информация об анкете или None, если анкеты закончились.
        """
        if not self.user_data_cache[user_id].get('profiles'):
            age, gender, city, status = (
                self.user_data_cache[user_id]["age"],
                self.user_data_cache[user_id]["gender"],
                self.user_data_cache[user_id]["city"],
                self.user_data_cache[user_id]["status"],
            )

            self.user_data_cache[user_id]["offset"] += self.top_users
            try:
                users = self.vkinder.search_users(age, gender, city, status,
                                                  offset=self.user_data_cache[user_id]["offset"])
            except ApiError:
                self.send_message(user_id, messages.session_error)
                return None
            self.user_data_cache[user_id]['profiles'] = [user for user in users if
                                                         not user.get('is_closed', True) and user['id'] not in
                                                         self.user_data_cache[user_id]['in_db']][
                                                        :self.top_users]
        return self.user_data_cache[user_id]['profiles'].pop(-1)

    def process_message(self, event):
        """
        Обработка сообщения

        :param event: Событие
        """
        current_data = self.user_data_cache.get(event.user_id)

        if current_data is None:
            self.initialize_user_data(event.user_id)
            current_step = None
        else:
            if event.text.lower() == 'избранное':
                self.handle_favorites(event.user_id)
                return
            current_step = current_data['step']

        self.handle_current_step(event.user_id, event.text, current_step)

    def initialize_user_data(self, user_id):
        """
        Инициализация данных пользователя при первом взаимодействии

        :param user_id: ID пользователя
        """
        # Инициализация в кэше
        self.user_data_cache[user_id] = {'step': None, 'offset': 0, 'last': None, 'favorites': []}
        # Поиск в базе данных
        self.user_data_cache[user_id]['in_db'] = self.user_data.get_user_data_from_db(user_id)
        # Отправим приветствие
        greet_message = messages.greet_again if self.user_data_cache[user_id]['in_db'] else messages.greet_status
        self.send_message(user_id, greet_message)

    def handle_current_step(self, user_id, text, current_step):
        """
        Обработка текущего шага бота

        :param user_id:      ID пользователя
        :param text:         Текст сообщения
        :param current_step: Текущий шаг
        """
        if current_step in self.step_handlers:
            handler = self.step_handlers[current_step]
            if self.is_valid_input(text, current_step):
                next_step = handler(user_id, text, current_step)
                self.user_data_cache[user_id][current_step] = text
            else:
                self.send_message(user_id, messages.incorrect_data)
                next_step = current_step
        else:
            self.send_message(user_id, messages.incorrect_data)
            next_step = current_step

        self.user_data_cache[user_id]['step'] = next_step

    def handle_favorites(self, user_id):
        users = self.user_data_cache[user_id]['favorites']
        if users:
            self.send_message(user_id, '\n'.join([messages.favorites,
                                                 '\n'.join(users)]))
        else:
            self.send_message(user_id, messages.no_favorites)

    def handle_final_step(self, user_id, text, _):
        if text.lower() == "еще":
            next_profile = self.get_next_profile(user_id)
            if next_profile:
                link = f"https://vk.com/id{next_profile['id']}"
                self.user_data_cache[user_id]['last'] = link
                self.user_data.save_session_to_db(user_id, [next_profile["id"]])
                self.user_data_cache[user_id]['in_db'].append(next_profile["id"])
                top_photos = self.vkinder.get_top_photos(next_profile["id"])
                self.send_photos_and_link(user_id, top_photos, link)
                return "final"
            else:
                self.send_message(user_id, messages.final_again)
                return "again"
        elif text.lower() == "заново":
            self.send_message(user_id, '\n'.join([messages.final_user_again,
                                                  messages.process_age]))
            return "age"
        elif text.lower() == "в избранное":
            self.send_message(user_id, 'Добавил в избранное!')
            self.user_data_cache[user_id]['favorites'].append(self.user_data_cache[user_id]['last'])
            return "final"
        else:
            self.send_message(user_id, messages.some_error)
            return "final"

    def handle_search_users(self, user_id, text, current_step):
        if self.is_valid_input(text, "status"):
            self.user_data_cache[user_id]["status"] = int(text)
            age, gender, city, status = (
                self.user_data_cache[user_id]["age"],
                self.user_data_cache[user_id]["gender"],
                self.user_data_cache[user_id]["city"],
                self.user_data_cache[user_id]["status"],
            )
            try:
                users = self.vkinder.search_users(age, gender, city, status)
            except ApiError:
                self.send_message(user_id, messages.session_error)
                return current_step
            self.user_data_cache[user_id]['profiles'] = [user for user in users if
                                                         not user.get('is_closed', True) and user['id'] not in
                                                         self.user_data_cache[user_id]['in_db']][
                                                        :self.top_users]

            # Отправляем первую анкету, если она есть
            next_profile = self.get_next_profile(user_id)
            if next_profile:
                link = f"https://vk.com/id{next_profile['id']}"
                self.user_data_cache[user_id]['last'] = link
                self.user_data.save_session_to_db(user_id, [next_profile["id"]])
                self.user_data_cache[user_id]['in_db'].append(next_profile["id"])
                top_photos = self.vkinder.get_top_photos(next_profile["id"])
                self.send_photos_and_link(user_id, top_photos, link)

            else:
                self.send_message(user_id, messages.final_status)

            self.send_message(user_id, messages.final_status)
            return "final"
        else:
            self.send_message(user_id, messages.incorrect_data)
            return current_step

    @staticmethod
    def get_vk_session(token):
        """
        Получение сессии VK
        :param token: Токен
        :return:      Объект сессии
        """
        try:
            session = vk_api.VkApi(token=token)
        except vk_api.exceptions.ApiError as error:
            logging.error(error)
            return None
        return session

    @staticmethod
    def is_valid_input(text, step):
        """
        Проверка корректности ввода состояния
        :param text: Текст сообщения
        :param step: Шаг
        :return:     True, если корректно, иначе False
        """
        if step is None:
            return True
        if step == "age":
            return text.isdigit() and (12 < int(text) < 100)
        if step == "gender":
            return text in ("1", "2")
        if step == "city":
            return text.isdigit()
        if step == "status":
            return text in ("1", "2", "3", "4", "5")
        if step == "final":
            return text.lower() in ['заново', 'еще', 'в избранное']
        if step == "again":
            return text.lower() == 'заново'
        return False
