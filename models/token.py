# -*- coding: utf-8 -*-
from functools import wraps
from peewee import *
from flask import request, g
from itsdangerous import URLSafeTimedSerializer
import time
from logging import getLogger


from config import SECRET_KEY, TOKEN_SALT
from extensions import db
from utils.func import random_ascii_string
from .. import meta
from .model import Model
from .user import User

LOGGER = getLogger()


def auth_header(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = request.args.get('access_token')
        if access_token:
            g.headers['Authorization'] = "Bearer {}".format(access_token)
        return f(*args, **kwargs)

    return decorated_function


def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        authorization = Authorization().get_authorization()
        print authorization.is_valid, 'dd'
        if not authorization.is_valid:
            raise meta.UNAUTHORIZED

        g.auth = authorization

        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        authorization = Authorization().get_authorization()
        if not authorization.is_valid:
            raise meta.UNAUTHORIZED

        g.auth = authorization

        return f(*args, **kwargs)

    return decorated_function


class Token(Model):
    id = PrimaryKeyField()
    grant_type = CharField(choices=['PASSWORD'])
    access_token = CharField(max_length=128, unique=True)
    expires_in = IntegerField(default=0)
    refresh_token = CharField(default='', max_length=128)
    client_id = IntegerField(default=0)
    user_id = IntegerField(default=0)
    create_time = IntegerField(default=0)


class Authorization(dict):
    def __init__(self, *args, **kwargs):
        super(Authorization, self).__init__(*args, **kwargs)
        self.is_valid = False
        self.token_length = 40
        self.token_serializer = URLSafeTimedSerializer(SECRET_KEY, salt=TOKEN_SALT)
        self.user = None

    def gen_token(self, grant_type, client_id, user_id):

        token_type = 'Bearer'

        token = Token.get_one(Token.grant_type == grant_type, Token.user_id == user_id,
                              Token.client_id == client_id)

        if token:
            return {
                'access_token': token.access_token,
                'token_type': token_type,
                'expires_in': token.expires_in,
                'refresh_token': token.refresh_token,
            }

        time_now = int(time.time())

        # 永不过期
        expires_in = 0
        refresh_token = random_ascii_string(self.token_length)
        access_token = self.token_serializer.dumps((grant_type, client_id, user_id, time_now, expires_in))

        values = {
            'grant_type': grant_type,
            'access_token': access_token,
            'expires_in': expires_in,
            'refresh_token': refresh_token,
            'client_id': client_id,
            'user_id': user_id,
            'create_time': time_now
        }

        # 保存token信息
        try:
            with db.database.atomic():
                # Token.delete().
                # where((getattr(Token, self.foreign_key) == user_id) & (Token.grant_type == grant_type)).execute()
                Token.create(**values)
        except IntegrityError as e:
            if e[0] == 1062:
                raise meta.LOGIN_TOO_OFTEN
            raise e
        return {
            'access_token': access_token,
            'token_type': token_type,
            'expires_in': expires_in,
            'refresh_token': refresh_token,
        }

    def get_token(self, access_token):
        token = Token.get_one_by_query(
            Token.select(Token, User).join(User, on=(Token.user_id == User.id).alias('user')).where(
                Token.access_token == access_token))
        if token:
            self.update(token.to_dict(recurse=False))
            self.user = token.user
        return token

    def destroy(self):
        return Token.delete().where(Token.access_token == self['access_token']).execute()

    # @cache_it(expire=60)
    def get_authorization(self):
        if 'Authorization' in request.headers:
            header = request.headers.get('Authorization')
        elif request.args.get('access_token'):
            header = "Bearer {}".format(request.args.get('access_token'))
        else:
            header = g.headers.get('Authorization')

        if header and header.split:
            header = header.split()
            print 'header', header

            if len(header) > 1 and header[0] == 'Bearer':
                print header[1], 'h'
                # try:
                row = self.token_serializer.loads(header[1])
                print row, 'row'
                grant_type, client_id, foreign_key_id, create_time, expires_in = row

                # 过期时间为0为不过期
                if expires_in == 0 or (create_time + expires_in) > time.time():
                    if self.get_token(header[1]):
                        self.is_valid = True
                # except Exception as e:
                #     LOGGER.debug(e)

        return self
