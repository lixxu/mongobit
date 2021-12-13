#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymongo
import six
from bson.errors import InvalidId
from bson.objectid import ObjectId
from pymongo import MongoClient

from .utils import get_sort

PM3 = pymongo.version >= "3.0"
PM36 = pymongo.version >= "3.6"


class MongoBit(object):
    conn = {}
    db = {}

    def __init__(self, config={}):
        if config:
            self.initialize(config)

    def initialize(self, config):
        self.connect(config)

    @classmethod
    def _get_params(cls, config={}):
        keys = ("host", "port", "name", "auth", "user", "pass")
        prefix = "MONGODB" if config.get("MONGODB_HOST") else "DB"
        return {k: config.get("{}_{}".format(prefix, k.upper())) for k in keys}

    def connect(self, config={}):
        params = self._get_params(config)
        assert "name" in params

        conn = MongoClient(params["host"], params["port"], connect=False)
        db = conn[params["name"]]
        if params.get("auth"):
            db.authenticate(params["user"], params["pass"])

        self.alias = config.get("alias", "default")
        MongoBit.conn[self.alias] = conn
        MongoBit.db[self.alias] = db

    @property
    def database(self):
        return self.__class__.db[self.alias]

    @property
    def connection(self):
        return self.__class__.conn[self.alias]

    def close(self):
        self.connection.close()
        self.__class__.conn.pop(self.alias)
        self.__class__.db.pop(self.alias)

    @classmethod
    def _get_coll(cls, alias, model):
        return cls.db[alias][model.__collection__]

    @property
    def model(self):
        return self.__model

    @property
    def count(self):
        return self.__count

    @property
    def cursor(self):
        return self.__cursor

    @classmethod
    def get_total_count(cls, alias, model):
        return cls.get_count(alias, model)

    @classmethod
    def get_count(cls, alias, model, spec=None, **kwargs):
        coll = cls._get_coll(alias, model)
        try:
            return coll.count_documents(spec, **kwargs)
        except Exception:
            if PM3:
                return coll.find(spec, projection=["_id"]).count()

            return coll.find(spec, fields=["_id"]).count()

    @classmethod
    def aggregate(cls, alias, model, pipeline, **kwargs):
        agg = cls._get_coll(alias, model).aggregate(pipeline, **kwargs)
        return agg["result"] if isinstance(agg, dict) else agg

    @classmethod
    def distinct(cls, alias, model, field, spec=None):
        coll = cls._get_coll(alias, model)
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

        doc = cls._get_coll(alias, model).find_one(spec, **kargs)
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
        coll_ = cls._get_coll(alias, model)
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

        obj.__count = cls.get_count(alias, model, spec)
        return obj

    @classmethod
    def insert(cls, alias, model, doc, **kwargs):
        coll = cls._get_coll(alias, model)
        if PM3:
            return coll.insert_one(doc).inserted_id

        kwargs.setdefault("w", 1)
        return coll.insert(doc, **kwargs)

    @classmethod
    def update(cls, alias, model, spec, up_doc, **kwargs):
        coll = cls._get_coll(alias, model)
        if PM3:
            return coll.update_one(
                spec, up_doc, upsert=kwargs.get("upsert", False)
            )

        kwargs.setdefault("w", 1)
        return coll.update(spec, up_doc, **kwargs)

    @classmethod
    def remove(cls, alias, model, spec, **kwargs):
        coll = cls._get_coll(alias, model)
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

    @classmethod
    def create_index(cls, alias, model, index, **kwargs):
        kwargs.setdefault("background", True)
        if PM36:
            kwargs.setdefault("session", None)

        return cls._get_coll(alias, model).create_index(index, **kwargs)

    @classmethod
    def drop_index(cls, alias, model, index, **kwargs):
        if PM36:
            kwargs.setdefault("session", None)

        return cls._get_coll(alias, model).drop_index(index, **kwargs)

    @classmethod
    def drop_indexes(cls, alias, model, **kwargs):
        if PM36:
            kwargs.setdefault("session", None)

        return cls._get_coll(alias, model).drop_index(**kwargs)

    @classmethod
    def list_indexes(cls, alias, model, **kwargs):
        if PM36:
            kwargs.setdefault("session", None)

        return cls._get_coll(alias, model).list_indexes(**kwargs)

    @classmethod
    def index_information(cls, alias, model, **kwargs):
        if PM36:
            kwargs.setdefault("session", None)

        return cls._get_coll(alias, model).index_information(**kwargs)
