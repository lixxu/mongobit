#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from time import strftime

import six
from bson.objectid import ObjectId

from .fields import fields, BaseField
from .utils import get_spec, get_sort
from .mongobit import MongoBit

TIME_FMT = "%Y-%m-%d %H:%M:%S"


class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        if name not in ("Model", "_Model"):
            # generate the default table name
            if "__collection__" not in attrs:
                coll_name = attrs.pop("coll_name", None) or "{}s".format(
                    name.lower()
                )
                attrs["__collection__"] = coll_name

            if "_id" not in attrs:
                attrs.update(_id=fields.objectid())

            if attrs.get("use_ts", False):
                if "created_at" not in attrs:
                    attrs.update(created_at=fields.str())

                if "updated_at" not in attrs:
                    attrs.update(updated_at=fields.str())

            attrs.update(_db_fields={})
            for k, v in six.iteritems(attrs):
                if isinstance(v, BaseField):
                    attrs["_db_fields"][k] = v
                    v.name = k

            # generates the unique fields
            attrs.update(_unique_fields=list(), _index_fields=list())
            if "created_at" in attrs:
                attrs["_index_fields"].append(get_sort("created_at"))

            if "updated_at" in attrs:
                attrs["_index_fields"].append(get_sort("updated_at desc"))

            for k, v in six.iteritems(attrs["_db_fields"]):
                if "unique" in v.validators:
                    uk = v.validators["unique"]
                    if uk is True or uk is False:
                        ukey = k
                    else:
                        ukey = uk

                    attrs["_unique_fields"].append(ukey)

                if "index" in v.validators:
                    _idx = v.validators["index"]
                    if _idx is True:
                        idx = get_sort("{0} {1}".format(k, _idx))
                    elif _idx.lower() in ("asc", "desc"):
                        idx = get_sort("{0} {1}".format(k, _idx))
                    else:
                        idx = get_sort(_idx)

                    if idx:
                        if isinstance(idx[0], list):
                            attrs["_index_fields"].extend(idx)
                        else:
                            attrs["_index_fields"].append(idx)

        return type.__new__(cls, name, bases, attrs)


@six.add_metaclass(ModelMeta)
class Model(dict):
    def __init__(self, **kwargs):
        if "_id" not in kwargs:
            self._is_new = True
            self._id = ObjectId()
            if hasattr(self, "created_at"):
                self.created_at = strftime(TIME_FMT)

        else:
            self._is_new = False

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, k):
        return getattr(self, k)

    def __setitem__(self, k, v):
        setattr(self, k, v)

    def __nonzero__(self):
        return True

    def __bool__(self):
        return True

    def update(self, dct=None, **kwargs):
        if isinstance(dct, Model):
            [setattr(self, k, v) for k, v in dct.dict.items()]
        elif isinstance(dct, dict):
            [setattr(self, k, v) for k, v in dct.items()]
        else:
            [setattr(self, k, v) for k, v in kwargs.items()]

    @property
    def dict(self):
        return {k: getattr(self, k) for k in self.__class__._db_fields}

    def __str__(self):
        return "{}".format(self.dict)

    def __repr__(self):
        kls = self.__class__
        return "<{}.{} object at {}>".format(
            kls.__module__, kls.__name__, id(self)
        )

    def safe_get(self, k, default=None):
        return self.get(k, default)

    @property
    def id(self):
        return self._id

    @property
    def canbe_removed(self):
        return False

    def get_clear_fields(self, doc=None):
        cls = self.__class__
        if doc:
            return {k: doc[k] for k in doc if k in cls._db_fields}

        return {k: getattr(self, k) for k in cls._db_fields}

    def get_update_doc(self, **kwargs):
        set_doc = kwargs.pop("set_doc", None)
        unset_doc = kwargs.pop("unset_doc", None)
        push_doc = kwargs.pop("push_doc", None)
        pull_doc = kwargs.pop("pull_doc", None)
        pull_all_doc = kwargs.pop("pull_all_doc", None)
        pop_doc = kwargs.pop("pop_doc", None)
        inc_doc = kwargs.pop("inc_doc", None)
        ats_doc = kwargs.pop("add_to_set_doc", None)
        if not ats_doc:
            ats_doc = kwargs.pop("addToSet", None)

        up_doc = {}
        if set_doc:
            _set_doc = set_doc.copy()
            fields = self.__class__._db_fields
            for k in list(_set_doc.keys()):
                if k in fields and _set_doc[k] == getattr(self, k):
                    _set_doc.pop(k)

            if _set_doc:
                up_doc["$set"] = _set_doc

        if unset_doc:
            up_doc["$unset"] = unset_doc

        if push_doc:
            up_doc["$push"] = push_doc

        if pull_doc:
            up_doc["$pull"] = pull_doc

        if pull_all_doc:
            up_doc["$pullAll"] = pull_all_doc

        if pop_doc:
            up_doc["$pop"] = pop_doc

        if inc_doc:
            up_doc["$inc"] = inc_doc

        if ats_doc:
            up_doc["$addToSet"] = ats_doc

        return up_doc

    def pre_action(self, **kwargs):
        skip = kwargs.pop("skip", False)
        update_ts = kwargs.pop("update_ts", True)
        if skip is True:
            self._errors = {}
        else:
            self.validate()

        return skip, update_ts, self.is_valid

    def insert_doc(self, **kwargs):
        kwargs.setdefault("w", 1)
        skip, update_ts, is_valid = self.pre_action(**kwargs)
        if not is_valid:
            return

        if "updated_at" in self.__class__._db_fields:
            if update_ts is not False:
                self.update(updated_at=strftime(TIME_FMT))

        return MongoBit.insert(
            alias=self.__class__._db_alias,
            model=self.__class__,
            doc=self.get_clear_fields(),
            **kwargs
        )

    def save_doc(self, **kwargs):
        return self.insert_doc(**kwargs)

    def update_doc(self, **kwargs):
        kwargs.setdefault("w", 1)
        up_doc = self.get_update_doc(**kwargs)
        if "$set" in up_doc:
            self.update(up_doc["$set"])

        skip, update_ts, is_valid = self.pre_action(**kwargs)
        if not is_valid:
            return

        if up_doc:
            if "updated_at" in self.__class__._db_fields:
                if update_ts is not False:
                    if "$set" not in up_doc:
                        up_doc["$set"] = dict(updated_at=strftime(TIME_FMT))
                    else:
                        up_doc["$set"].update(updated_at=strftime(TIME_FMT))

            return MongoBit.update(
                alias=self.__class__._db_alias,
                model=self.__class__,
                spec=dict(_id=self.id),
                up_doc=up_doc,
                **kwargs
            )

    def save(self, **kwargs):
        if self._is_new:
            return self.save_doc(**kwargs)

        return self.update_doc(**kwargs)

    def destroy(self, **kwargs):
        self.remove(**kwargs)

    def remove(self, **kwargs):
        kwargs.setdefault("w", 1)
        return MongoBit.remove(
            alias=self.__class__._db_alias,
            model=self.__class__,
            spec=dict(_id=self.id),
            **kwargs
        )

    @classmethod
    def total_count(cls):
        return MongoBit.get_total_count(cls._db_alias, cls)

    @classmethod
    def get_count(cls, spec=None):
        return MongoBit.get_count(cls._db_alias, cls, spec)

    @classmethod
    def distinct(cls, field, spec=None):
        return MongoBit.distinct(cls._db_alias, cls, field, spec=spec)

    @classmethod
    def find_one(cls, id=None, **kwargs):
        return MongoBit.find_one(cls._db_alias, cls, id=id, **kwargs)

    @classmethod
    def find(cls, **kwargs):
        paginate = kwargs.get("paginate", False)
        if paginate is False:
            return MongoBit.find(cls._db_alias, cls, **kwargs)

        from flask import request, current_app
        from flask_paginate import Pagination

        if hasattr(current_app, "y18n"):
            t = current_app.y18n.t
        else:
            t = None

        page1 = int(kwargs.get("page", 1))
        page2 = int(request.view_args.get("page", 1))
        page3 = int(request.args.get("page", 1))
        page = max((page1, page2, page3))
        if "per_page" in kwargs:
            per_page = kwargs["per_page"]
        elif "PER_PAGE" in current_app.config:
            per_page = current_app.config["PER_PAGE"]
        else:
            per_page = 10

        if "link_size" in kwargs:
            link_size = kwargs["link_size"]
        elif "LINK_SIZE" in current_app.config:
            link_size = current_app.config["LINK_SIZE"]
        else:
            link_size = ""

        if "link_align" in kwargs:
            alignment = kwargs["link_align"]
        elif "LINK_ALIGN" in current_app.config:
            alignment = current_app.config["LINK_ALIGN"]
        else:
            alignment = ""

        bs_version = (
            kwargs.get("bs_version")
            or current_app.config.get("BS_VERSION")
            or 2
        )
        css_framework = (
            kwargs.get("css_framework")
            or current_app.config.get("CSS_FRAMEWORK")
            or "bootstrap"
        )

        skip = (page - 1) * per_page
        kwargs.update(limit=per_page, skip=skip)
        objs = MongoBit.find(cls._db_alias, cls, **kwargs)

        total = kwargs.get("total", "all")
        if total == "all":
            total = cls.total_count()
        elif total == "docs":
            total = objs.count

        args = dict(
            page=page,
            per_page=per_page,
            inner_window=kwargs.get("inner_window", 2),
            outer_window=kwargs.get("outer_window", 1),
            prev_label=kwargs.get("prev_label"),
            next_label=kwargs.get("next_label"),
            search=kwargs.get("search", False),
            total=total,
            display_msg=kwargs.get("display_msg"),
            search_msg=kwargs.get("search_msg"),
            record_name=kwargs.get("record_name"),
            link_size=link_size,
            alignment=alignment,
            bs_version=bs_version,
            css_framework=css_framework,
        )
        if t:
            for k in (
                "display_msg",
                "search_msg",
                "prev_label",
                "next_label",
                "record_name",
            ):
                if not args[k]:
                    args[k] = t(k)

        objs.pagination = Pagination(found=objs.count, **args)
        objs.skip = skip
        return objs

    @property
    def is_valid(self):
        if hasattr(self, "_errors"):
            for v in self._errors.values():
                if len(v) != 0:
                    return False

            return True

        # please validate first
        return False

    def validate(self, cs=False, update=False):
        self._errors = {}
        self.check_unique(cs=cs)

    def check_unique(self, fields=None, cs=False):
        """Case sensitive: cs."""
        cls = self.__class__
        if fields is None:
            fields = cls._unique_fields

        update = not self._is_new
        for field in fields:
            spec = self.get_spec(field, self, cs=cs)
            if spec and update:
                spec.update(_id={"$ne": self.id})

            if spec and cls.find_one(spec=spec):
                self._errors[field] = "is already taken"

    @property
    def get_spec(self):
        return get_spec

    @property
    def get_sort(self):
        return get_sort
