import logging
import sys

from sqlalchemy import create_engine, Column, Integer, ARRAY, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = 'new_users_2'

    user_id = Column(Integer, primary_key=True)
    searched_users = Column(ARRAY(Integer), nullable=False)


class Saver:
    def __init__(self, connstr=None):
        self.logger = logging.getLogger(__name__)
        self.engine = create_engine(connstr)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.table_check()

    def table_create(self):
        """
        Создание таблицы, если она не существует.
        """
        Base.metadata.create_all(self.engine)

    def table_check(self):
        """
        Проверка существования таблицы, создание при необходимости.
        """
        inspector = inspect(self.engine)
        if not inspector.has_table(User.__tablename__):
            response = input('Таблицы не существует. Создать таблицу? (Y/N): ').upper()
            if response == 'Y':
                self.table_create()
                self.logger.info('Таблица создана.')
            else:
                self.logger.info('Выход...')
                sys.exit(0)

    def save_session_to_db(self, user_id, searched_users):
        """
        Сохраняет или обновляет сессию пользователя в базе данных.
        :param user_id:          ID пользователя ВКонтакте.
        :param searched_users:   Найденный пользователь.
        """
        user = self.session.query(User).get(user_id)
        if user:
            user.searched_users = user.searched_users + searched_users
            self.session.merge(user)
        else:
            user = User(user_id=user_id, searched_users=searched_users)
            self.session.add(user)

        self.session.flush()
        self.session.commit()

    def get_user_data_from_db(self, user_id):
        """
        Извлекает данные о пользователе из базы данных.
        :param user_id: ID пользователя.
        :return:        Список найденных пользователей, либо None.
        """
        user = self.session.query(User).get(user_id)
        if user:
            return user.searched_users
        else:
            return []
