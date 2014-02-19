#!/usr/bin/env python
#-*- coding: utf-8 -*-

from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
from utils import get_sort


class MongoBit(object):
    conn = {}
    db = {}

    def __init__(self, config={}):
        if config:
            self.initialize(config)

    def initialize(self, config):
        self.connect(config)

    def connect(self, config={}):
        host = config.get('DB_HOST', 'localhost')
        port = config.get('DB_PORT', 27017)
        assert 'DB_NAME' in config
        database = config['DB_NAME']
        conn = MongoClient(host, port)
        db = conn[database]
        is_auth = config.get('DB_AUTH', False)
        if is_auth:
            user = config.get('DB_USER')
            passwd = config.get('DB_PASS')
            db.authenticate(user, passwd)

        self.alias = config.get('alias', 'default')
        MongoBit.conn[self.alias] = conn
        MongoBit.db[self.alias] = db

    @property
    def database(self):
        return MongoBit.db[self.alias]

    @property
    def connection(self):
        return MongoBit.conn[self.alias]

    def close(self):
        self.connection.disconnect()
        MongoBit.conn.pop(self.alias)
        MongoBit.db.pop(self.alias)

    @classmethod
    def get_total_count(cls, alias, model):
        return MongoBit.db[alias][model.coll_name].count()

    @classmethod
    def get_count(cls, alias, model, spec=None):
        return MongoBit.db[alias][model.coll_name].find(spec,
                                                        fields=['_id']).count()

    @classmethod
    def distinct(cls, alias, model, field, spec=None):
        collection = MongoBit.db[alias][model.coll_name]
        if spec:
            return collection.find(spec, fields=[field]).distinct(field)

        return collection.distinct(field)

    @classmethod
    def find_one(cls, alias, model, id=None, **kwargs):
        if 'spec' in kwargs:
            spec = kwargs['spec']
        else:
            if isinstance(id, basestring):
                try:
                    id = ObjectId(id)
                except InvalidId:
                    return None

            spec = dict(_id=id)

        fields = kwargs.get('fields')
        sort = get_sort(kwargs.get('sort'))
        skip = kwargs.get('skip', 0)
        doc = MongoBit.db[alias][model.coll_name].find_one(spec,
                                                           fields=fields,
                                                           sort=sort,
                                                           skip=skip,
                                                           )

        return model(**doc) if doc else None

    @classmethod
    def find(cls, alias, model, **kwargs):
        obj = cls()
        obj.alias = alias
        obj.__model = model
        spec = kwargs.get('spec') or None
        fields = kwargs.get('fields') or None
        sort = get_sort(kwargs.get('sort'))
        limit = kwargs.get('limit', 0)
        skip = kwargs.get('skip', 0)
        hint = kwargs.get('hint')
        if hint:
            obj.__cursor = MongoBit.db[alias][model.coll_name].find(spec,
                fields=fields,
                sort=sort,
                limit=limit,
                skip=skip,
                ).hint(hint)
        else:
            obj.__cursor = MongoBit.db[alias][model.coll_name].find(spec,
                fields=fields,
                sort=sort,
                limit=limit,
                skip=skip,
                )

        obj.__count = obj.__cursor.count()
        return obj

    @classmethod
    def insert(cls, alias, model, doc, **kwargs):
        kwargs.setdefault('w', 1)
        return MongoBit.db[alias][model.coll_name].insert(doc, **kwargs)

    @classmethod
    def save(cls, alias, model, doc, **kwargs):
        kwargs.setdefault('w', 1)
        return MongoBit.db[alias][model.coll_name].save(doc, **kwargs)

    @classmethod
    def update(cls, alias, model, spec, up_doc, **kwargs):
        kwargs.setdefault('w', 1)
        return MongoBit.db[alias][model.coll_name].update(spec,
                                                          up_doc,
                                                          **kwargs
                                                          )

    @classmethod
    def remove(cls, alias, model, spec, **kwargs):
        kwargs.setdefault('w', 1)
        return MongoBit.db[alias][model.coll_name].remove(spec, **kwargs)

    def __iter__(self):
        return self

    def next(self):
        if self.count < 1:
            raise StopIteration

        self.__count -= 1
        return self.model(**self.cursor.next())

    def create_index(self, alias, model, index, background=True):
        MongoBit.db[alias][model.coll_name].ensure_index(index,
                                                         background=background)

    @property
    def model(self):
        return self.__model

    @property
    def count(self):
        return self.__count

    @property
    def cursor(self):
        return self.__cursor
