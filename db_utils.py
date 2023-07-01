"""
Файл с описанием класса подклюения к БД
"""
# pylint: disable = import-error, line-too-long, logging-fstring-interpolation
import logging
import sys

import psycopg2


class Saver:
    """
    Сохранение состояния пользователя
    """

    # pylint: disable=too-many-arguments
    def __init__(self, connstr=None, database='user_data', user='admin', password='password',
                 host='127.0.0.1', port=80, table='searched_users'):
        """
        Создает соединение с базой данных PostgreSQL.
        """
        self.logger = logging.getLogger(__name__)
        self.connection = None
        self.table = table
        try:
            self.connection = psycopg2.connect(connstr) if connstr else psycopg2.connect(
                database=database,
                user=user,
                password=password,
                host=host,
                port=port
            )
            self.check_table()
            logging.info('Успешное подключение к базе данных!')
        except psycopg2.Error as error:
            logging.error(f"Ошибка при подключении к базе данных: {error}")

    def create_table(self):
        """
        Создание таблицы, если она не существует.
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.table} (
                    user_id INTEGER PRIMARY KEY,
                    searched_users INTEGER[] NOT NULL
                );
                """
            )
            self.connection.commit()

    def check_table(self):
        """
        Проверка существования таблицы, создание при необходимости.
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
                (self.table,)
            )
            if not cursor.fetchone()[0]:
                response = input('Создать базу? (Y/N): ').upper()
                if response == 'Y':
                    self.create_table()
                    logging.info('Таблица создана, запускаю бота!')
                else:
                    print('Выхожу...')
                    sys.exit(0)
            else:
                logging.info('База существует, запускаю бота')

    def save_session_to_db(self, user_id, searched_users):
        """
        Сохраняет или обновляет сессию пользователя в базе данных.
        :param user_id:          ID пользователя ВКонтакте.
        :param searched_users:   Найденные пользователи.
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {self.table} (user_id, searched_users)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    searched_users = {self.table}.searched_users || %s;
                """,
                (user_id, searched_users, searched_users)
            )
            self.connection.commit()

    def get_user_data_from_db(self, user_id):
        """
        Извлекает данные о пользователе из базы данных.
        :param user_id: ID пользователя.
        :return:        Список найденных пользователей, либо None.
        """
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT searched_users FROM {self.table} WHERE user_id = %s;", (user_id,))
            result = cursor.fetchone()

        return result[0] if result else []
