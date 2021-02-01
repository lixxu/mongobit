#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymongo
import six
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
from .utils import get_sort

PM3 = pymongo.version >= "3.0"


class MongoBit(object):
    conn = {}
    db = {}

    def __init__(self, config={}):
        if config:
            self.initialize(config)

    def initialize(self, config):
        self.connect(config)

    def connect(self, config={}):
        host = config.get("DB_HOST", "localhost")
        port = config.get("DB_PORT", 27017)
        assert "DB_NAME" in config
        database = config["DB_NAME"]
        conn = MongoClient(host, port)
        db = conn[database]
        is_auth = config.get("DB_AUTH", False)
        if is_auth:
            user = config.get("DB_USER")
            passwd = config.get("DB_PASS")
            db.authenticate(user, passwd)

        self.alias = config.get("alias", "default")
        MongoBit.conn[self.alias] = conn
        MongoBit.db[self.alias] = db

    @property
    def database(self):
        return MongoBit.db[self.alias]

    @property
    def connection(self):
        return MongoBit.conn[self.alias]

    def close(self):
        self.connection.close()
        MongoBit.conn.pop(self.alias)
        MongoBit.db.pop(self.alias)

    @staticmethod
    def _get_coll(alias, model):
        return MongoBit.db[alias][model.__collection__]

    @classmethod
    def get_total_count(cls, alias, model):
        return MongoBit._get_coll(alias, model).count()

    @classmethod
    def get_count(cls, alias, model, spec=None, **kwargs):
        coll = MongoBit._get_coll(alias, model)
        try:
            return coll.count_documents(spec, **kwargs)
        except Exception:
            return coll.find(spec, fields=["_id"]).count()

    @classmethod
    def distinct(cls, alias, model, field, spec=None):
        coll = MongoBit._get_coll(alias, model)
        if spec:
            if PM3:
                return coll.distinct(field, filter=spec)

            return coll.find(spec, fields=[field]).distinct(field)

        return coll.distinct(field)

    @classmethod
    def find_one(cls, alias, model, id=None, **kwargs):
        if "spec" in kwargs or "filter" in kwargs:
            spec = kwargs.get("spec")
            if not spec:
                spec = kwargs.get("filter")

        else:
            if isinstance(id, six.string_types):
                try:
                    id = ObjectId(id)
                except InvalidId:
                    return None

            spec = dict(_id=id)

        fields = kwargs.get("fields")
        if not fields:
            fields = kwargs.get("projection")

        sort = get_sort(kwargs.get("sort"))
        skip = kwargs.get("skip", 0)
        kargs = dict(sort=sort, skip=skip)
        if fields:
            if PM3:
                kargs.update(projection=fields)
            else:
                kargs.update(fields=fields)

        doc = MongoBit._get_coll(alias, model).find_one(spec, **kargs)
        return model(**doc) if doc else None

    @classmethod
    def find(cls, alias, model, **kwargs):
        obj = cls()
        obj.alias = alias
        obj.__model = model
        spec = kwargs.get("spec") or None
        if not spec:
            spec = kwargs.get("filter") or None

        fields = kwargs.get("fields") or None
        if not fields:
            fields = kwargs.get("projection") or None

        sort = get_sort(kwargs.get("sort"))
        limit = kwargs.get("limit", 0)
        skip = kwargs.get("skip", 0)
        hint = kwargs.get("hint")
        coll_ = MongoBit._get_coll(alias, model)
        kargs = dict(sort=sort, limit=limit, skip=skip)
        if fields:
            if PM3:
                kargs.update(projection=fields)
            else:
                kargs.update(fields=fields)

        if hint:
            obj.__cursor = coll_.find(spec, **kargs).hint(hint)
        else:
            obj.__cursor = coll_.find(spec, **kargs)

        obj.__count = obj.__cursor.count()
        return obj

    @classmethod
    def insert(cls, alias, model, doc, **kwargs):
        coll = MongoBit._get_coll(alias, model)
        if PM3:
            return coll.insert_one(doc).inserted_id

        kwargs.setdefault("w", 1)
        return coll.insert(doc, **kwargs)

    @classmethod
    def update(cls, alias, model, spec, up_doc, **kwargs):
        coll = MongoBit._get_coll(alias, model)
        if PM3:
            return coll.update_one(
                spec, up_doc, upsert=kwargs.get("upsert", False)
            )

        kwargs.setdefault("w", 1)
        return coll.update(spec, up_doc, **kwargs)

    @classmethod
    def remove(cls, alias, model, spec, **kwargs):
        coll = MongoBit._get_coll(alias, model)
        if PM3:
            return coll.delete_one(spec)

        kwargs.setdefault("w", 1)
        return coll.remove(spec, **kwargs)

    def __iter__(self):
        return self

    def next(self):
        if self.count < 1:
            raise StopIteration

        self.__count -= 1
        return self.model(**self.cursor.next())

    def __next__(self):
        return self.next()

    def create_index(self, alias, model, index, background=True):
        MongoBit._get_coll(alias, model).create_index(
            index, background=background
        )

    @property
    def model(self):
        return self.__model

    @property
    def count(self):
        return self.__count

    @property
    def cursor(self):
        return self.__cursor
