# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.security import generate_password_hash, check_password_hash
from peewee import *
import logging

from .. import meta

from .model import Model

LOGGER = logging.getLogger()


class User(Model):
    id = PrimaryKeyField(help_text='主键')
    username = CharField(max_length=40, unique=True, verbose_name='用户名')
    nickname = CharField(max_length=40, default='', help_text='昵称')
    password = CharField(max_length=100, help_text='密码')
    enabled = BooleanField(default=False, help_text='是否启用')
    create_time = IntegerField(default=0, help_text='创建时间戳')
    update_time = IntegerField(default=0, help_text='更新时间戳')
    avatar_url = CharField(default='', max_length=100, help_text='头像地址')
    balance = IntegerField(default=0)

    exclude = [password]

    def check_password(self, password):
        if password:
            return check_password_hash(self.password, password)

        return False

    def set_password(self, password):
        if len(str(password)) >= 6:
            self.password = generate_password_hash(password)
            self.save()
            return True
        return False

    def modify(self, values):
        if values.get('password'):
            values['password'] = generate_password_hash(values['password'])

        return super(User, self).modify(values)

    @classmethod
    def get_by_username(cls, username):
        """

        :param username: 用户名
        :type username: str, unicode
        :return:
        :rtype: User
        """
        return cls.get_one(cls.username == username)

    @classmethod
    def add(cls, values):
        """
        添加帐号，如果手机号已经登记过则失败
        """
        try:
            values.setdefault('enabled', True)
            values.setdefault('create_time', cls.now())
            values['password'] = generate_password_hash(values['password'])

            with cls.db.transaction():

                return cls.create(**values)
        except IntegrityError as e:
            if e[0] == 1062:
                raise meta.USER_USERNAME_EXIST

            raise e

    @classmethod
    def get_user_infos_by_ids(cls, ids):
        if not ids:
            return
        result = {}
        query = cls.select().where(cls.id << ids)
        for item in query:
            result[item.id] = {'nickname': item.nickname}
        return result

    @classmethod
    def update_amount(cls, user_id, amount, adding=False):
        if adding:
            return cls.update({User.balance: User.balance + amount}).where(cls.id == user_id).execute()
        return cls.update({User.balance: User.balance - amount}).where(cls.id == user_id).execute()



