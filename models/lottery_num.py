# -*- coding: utf-8 -*-
import datetime
import logging

from peewee import *
from .model import Model

LOGGER = logging.getLogger()


class LotteryNum(Model):
    class Meta:
        db_table = 'lottery_num'
    id = IntegerField(primary_key=True)
    time = CharField(null=False, max_length=32)
    num_one = SmallIntegerField(null=False)
    num_sec = SmallIntegerField(null=False)
    num_thr = SmallIntegerField(null=False)
    num_add = SmallIntegerField(null=False)
    num_str = CharField(null=False, max_length=16)
    result = CharField(null=False, max_length=16)
    type = SmallIntegerField(null=False)
    by_hand = SmallIntegerField(null=False, default=0)
    create_time = CharField(default=0, max_length=32)

    @classmethod
    def create_record(cls, period_id, time, num_one, num_sec, num_thr, num_add, num_str, result, type, by_hand):
        return cls.insert(id=period_id, time=time, num_one=num_one,
                          num_sec=num_sec, num_thr=num_thr, num_add=num_add, num_str=num_str,
                          result=result, type=type, by_hand=by_hand, create_time=datetime.datetime.now()).execute()


class LotteryLog(Model):
    class Meta:
        db_table = 'lottery_log'
    id = PrimaryKeyField()
    user_id = IntegerField()
    period = IntegerField(default=0)
    create_time = CharField(default=0, max_length=32)
    text = CharField(default=0, max_length=32)
    amount = IntegerField()
    is_checked = IntegerField(default=0)
    room_id = IntegerField(default=0)

    @classmethod
    def create_record(cls, user_id, num_id, text, amount):
        return cls.insert(user_id=user_id, num_id=num_id, text=text,
                          amount=amount, create_time=datetime.datetime.now()).execute()



