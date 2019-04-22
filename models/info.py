# coding=utf8
import logging

from peewee import *
from .model import Model

LOGGER = logging.getLogger()


class Info(Model):
    class Meta:
        db_table = 'info'
    id = PrimaryKeyField()
    type = IntegerField(default=0)  # 消息中心通知：1 ，首页消息通知：2, 信息记录：3（json）
    content = TextField()



