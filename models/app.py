# -*- coding: utf-8 -*-
from peewee import *
import logging

from .model import Model, JsonField

LOGGER = logging.getLogger()


class App(Model):
    id = PrimaryKeyField()
    type = SmallIntegerField(default=0)  # 应用类型
    app_id = CharField(max_length=256, default='')
    app_key = CharField(max_length=256, default='')
    name = CharField(max_length=10, unique=True)  # 名称
    desc = TextField(max_length=50, default='')  # 描述
    target = CharField(default='self', choices=['self', 'blank'])  # 窗口打开方式类型
    url = CharField(max_length=256, default='')  # 对应URL
    logos = CharField(max_length=256, default='')
    small_logo = CharField(max_length=256, default='')
    is_public = BooleanField(default=True)  # 是否公开
    visible_company_ids = JsonField(default=[])  # 可见的商家列表
    create_time = IntegerField()
    status = SmallIntegerField(default=0)   # 0：未审核

    @classmethod
    def add(cls, values):
        """
        添加
        """
        values.setdefault('create_time', cls.now())
        with cls.db.transaction():
            return cls.create(**values)