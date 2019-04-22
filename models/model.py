# coding=utf-8
from __future__ import absolute_import, unicode_literals

import peewee
from peewee import *
from peewee import Node

from datetime import datetime
import time
import json

from extensions import db

LIMIT = 10


class Model(db.Model):
    class Meta:
        only_save_dirty = True  # 只保存有变化的参数

    db = db.database

    @classmethod
    def table_name(cls):
        return cls._meta.db_table

    @classmethod
    def get_fields(cls):
        keys = []
        for key, value in cls._meta.fields.items():
            if isinstance(value, peewee.ForeignKeyField):
                keys.append('{}_id'.format(key))
            elif isinstance(value, peewee.Field):
                keys.append(key)
        return keys

    @classmethod
    def get_date_id_from_timestamp(cls, create_time=None):
        if create_time is None:
            create_time = cls.now()
        return int(datetime.fromtimestamp(create_time).strftime('%Y%m%d'))

    @classmethod
    def get_by_id(cls, pk_value):
        return cls.get_one(cls._meta.primary_key == pk_value)

    @classmethod
    def get_by_ids(cls, ids, is_object=False):
        result = {}
        if not ids:
            return result

        ids = set(ids)

        query = cls.select().where(cls._meta.primary_key.in_(ids))
        data = cls.get_list(query, is_object=is_object)

        for value in data:
            result[value[cls._meta.primary_key.name]] = value
        return result

    @classmethod
    def get_by_key_values(cls, key, values, is_object=False):
        result = {}
        if not values:
            return result

        values = set(values)

        query = cls.select().where(getattr(cls, key).in_(values))
        data = cls.get_list(query, is_object=is_object)

        for item in data:
            result[item[key]] = item
        return result

    @classmethod
    def get_one(cls, *query, **kwargs):
        try:
            return cls.get(*query, **kwargs)
        except peewee.DoesNotExist:
            return None

    @classmethod
    def get_one_by_query(cls, query):
        try:
            return query.get()
        except peewee.DoesNotExist:
            return None

    @classmethod
    def parse_operator(cls, query, key, value):
        if '__' not in key:
            query = query.where(getattr(cls, key) == value)
        else:
            field, operator = key.split('__')
            if operator == 'in':
                query = query.where(getattr(getattr(cls, field), 'in_')(value))
            elif operator == 'gt':
                query = query.where(getattr(cls, field) > value)
            elif operator == 'gte':
                query = query.where(getattr(cls, field) >= value)
            elif operator == 'lt':
                query = query.where(getattr(cls, field) < value)
            elif operator == 'lte':
                query = query.where(getattr(cls, field) <= value)
            elif operator == 'ne':
                query = query.where(getattr(cls, field) != value)
            elif operator == 'nin':
                query = query.where(getattr(getattr(cls, field), 'not_in')(value))
            else:
                raise Exception('field = {} not support operator = {}'.format(field, operator))

        return query

    @classmethod
    def get_list(cls, query_or_model=None, paging=None, is_object=False, recurse=False):
        if query_or_model is None:
            query = cls.select()

        elif isinstance(query_or_model, dict):
            query = cls.select()
            for key, value in query_or_model.items():
                query = cls.parse_operator(query, key, value)
        else:
            query = query_or_model

        if paging:

            rows_found = query.count()

            offset = int(paging.get('offset', 0))
            limit = int(paging.get('limit', LIMIT))

            if offset < 0:
                if rows_found:
                    if rows_found % limit == 0:
                        offset = (rows_found / limit - 1) * limit
                    else:
                        offset = rows_found / limit * limit
                else:
                    offset = 0

            query = query.offset(offset).limit(limit)

            data = []
            for result in query:
                data.append(result if is_object else result.to_dict(recurse=recurse))

            pagination = {
                'offset': offset,
                'limit': limit,
                'rows_found': rows_found
            }
            return data, pagination

        else:
            data = []
            for result in query:
                data.append(result if is_object else result.to_dict(recurse=recurse))
            return data

    @classmethod
    def execute(cls, sql, statement=None, one=False):
        cursor = cls.db.execute_sql(sql, statement)
        return _format(cursor, one)

    @classmethod
    def rows_found(cls):
        row = cls.execute('SELECT FOUND_ROWS() AS rows_found', one=True)
        if row:
            return row['rows_found']
        return 0

    @staticmethod
    def now(ms=False):
        t = time.time()
        if ms:
            return int(t * 1000)
        return int(t)

    @classmethod
    def set_order_by(cls, query, order_by):
        order_by_list = []
        for value in order_by.split(','):
            if value[0] == '-':
                sort = 'desc'
                value = value[1:]
            else:
                sort = 'asc'

            order_by_list.append(getattr(getattr(cls, value), sort)())

        if order_by_list:
            query = query.order_by(*order_by_list)

        return query

    def to_dict(self, recurse=False, backrefs=False, only=None,
                exclude=None, seen=None, extra_attrs=None,
                fields_from_query=None):
        """
        Convert a model instance (and any related objects) to a dictionary.

        :param bool recurse: Whether foreign-keys should be recursed.
        :param bool backrefs: Whether lists of related objects should be recursed.
        :param only: A list (or set) of field instances indicating which fields
            should be included.
        :param exclude: A list (or set) of field instances that should be
            excluded from the dictionary.
        :param list extra_attrs: Names of model instance attributes or methods
            that should be included.
        :param SelectQuery fields_from_query: Query that was source of model. Take
            fields explicitly selected by the query and serialize them.
        """

        # 所有递归默认只递归一次
        if hasattr(self, 'recurse_once'):
            recurse_once = getattr(self, 'recurse_once')
        else:
            recurse_once = True

        # 获取模型默认过滤字段
        if hasattr(self, 'exclude'):
            default_exclude = getattr(self, 'exclude')
            if exclude is None and default_exclude is not None:
                exclude = default_exclude
            elif exclude is not None and default_exclude is not None:
                if isinstance(exclude, set):
                    exclude = list(exclude)
                exclude.extend(default_exclude)

        # 原始
        only = _clone_set(only)
        extra_attrs = _clone_set(extra_attrs)

        if fields_from_query is not None:
            for item in fields_from_query._select:
                if isinstance(item, Field):
                    only.add(item)
                elif isinstance(item, Node) and item._alias:
                    extra_attrs.add(item._alias)

        data = {}
        exclude = _clone_set(exclude)
        seen = _clone_set(seen)
        exclude |= seen
        model_class = type(self)

        for field in self._meta.sorted_fields:
            if field in exclude or (only and (field not in only)):
                continue

            field_data = self._data.get(field.name)
            if isinstance(field, ForeignKeyField) and recurse:
                if field_data:
                    seen.add(field)
                    rel_obj = getattr(self, field.name)
                    field_data = rel_obj.to_dict(
                        recurse=False if recurse_once else recurse,
                        backrefs=backrefs,
                        only=only,
                        exclude=exclude,
                        seen=seen)
                else:
                    field_data = {}

            data[field.name] = field_data

        if extra_attrs:
            for attr_name in extra_attrs:
                attr = getattr(self, attr_name)
                if callable(attr):
                    data[attr_name] = attr()
                else:
                    data[attr_name] = attr

        if backrefs:
            for related_name, foreign_key in self._meta.reverse_rel.items():
                descriptor = getattr(model_class, related_name)
                if descriptor in exclude or foreign_key in exclude:
                    continue
                if only and (descriptor not in only) and (foreign_key not in only):
                    continue

                accum = []
                exclude.add(foreign_key)
                related_query = getattr(
                    self,
                    related_name + '_prefetch',
                    getattr(self, related_name))

                for rel_obj in related_query:
                    accum.append(rel_obj.to_dict(
                        recurse=False if recurse_once else recurse,
                        backrefs=backrefs,
                        only=only,
                        exclude=exclude))

                data[related_name] = accum

        return data


    @classmethod
    def add(cls, values):
        if hasattr(cls, 'add_fields'):
            for key, value in values.items():
                if key not in cls.add_fields:
                    del values[key]
        if not hasattr(cls, 'timestamps') or cls.timestamps:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            values.setdefault('created_at', now)
            values.setdefault('updated_at', now)
        values.setdefault('is_delete', 0)
        try:
            return cls.create(**values)
        except IntegrityError as e:
            if e[0] == 1062:
                return cls.error_duplicate_response(e)


    def edit_by_id(self, data):
        values = data.copy()
        if hasattr(self, 'update_fields'):
            for key, value in values.items():
                if key not in self.update_fields:
                    del values[key]
                else:
                    setattr(self, key, value)
        if self.is_dirty():
            try:
                if not hasattr(self, 'timestamps') or self.timestamps:
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    setattr(self, 'updated_at', now)
                return self.save()
            except IntegrityError as e:
                if e[0] == 1062:
                    return self.error_duplicate_response(e)
        return False

    @classmethod
    def error_duplicate_response(cls, e):
        raise e



def _format(cursor, one=False):
    description = cursor.description
    keys = []
    for item in description:
        keys.append(item[0])
    if one:
        row = cursor.fetchone()
        if row:
            return dict(zip(keys, row))
    else:
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append(dict(zip(keys, row)))
        return result


def join_arr(arr):
    return ','.join(['%s'] * len(arr))


class SetField(peewee.Field):
    db_field = 'set'

    def db_value(self, value):
        if value and (isinstance(value, list) or isinstance(value, tuple)):
            return ','.join(value)
        return value if value else ''

    def python_value(self, value):
        if value:
            return sorted(value.split(','))
        return []


class JsonField(peewee.Field):
    db_field = 'text'

    def db_value(self, value):
        return json.dumps(value) if value is not None else ''

    def python_value(self, value):
        if value:
            return json.loads(value)
        return ''


class BigIntegerPrimaryKeyField(peewee.BigIntegerField):
    db_field = 'primary_key'

    def __init__(self, *args, **kwargs):
        kwargs['primary_key'] = True
        super(BigIntegerPrimaryKeyField, self).__init__(*args, **kwargs)


def _clone_set(s):
    if s:
        return set(s)
    return set()
