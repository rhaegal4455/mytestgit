import logging

from peewee import *
from .model import Model

LOGGER = logging.getLogger()


class Payment(Model):
    class Meta:
        db_table = 'payment'
    id = PrimaryKeyField()
    user_id = IntegerField()
    create_time = IntegerField()
    charge_amount = IntegerField(default=0)
    confirmed = IntegerField(default=0)
    is_delete = IntegerField(default=0)
    nick = CharField(default='')
    info = CharField(default='')

    @classmethod
    def add(cls, values):
        values.setdefault('create_time', cls.now())

        with cls.db.transaction():
            return cls.create(**values)


class AmountDetail(Model):
    class Meta:
        db_table = 'amount_detail'
    id = PrimaryKeyField()
    user_id = IntegerField()
    create_time = IntegerField()
    amount = IntegerField(default=0)
    type = IntegerField(default=0)
    date_id = IntegerField(default=0)
    amount_change = IntegerField(default=0)
    tips = CharField(default='')

    @classmethod
    def add(cls, values):
        values.setdefault('create_time', cls.now())

        with cls.db.transaction():
            return cls.create(**values)



