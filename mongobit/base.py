#!/usr/bin/env python
#-*- coding: utf-8 -*-

from time import strftime
from pymongo import ASCENDING as ASC, DESCENDING as DESC
from pymongo.errors import OperationFailure
from bson.objectid import ObjectId
from bson.errors import InvalidId

from fields import fields, BaseField
from utils import get_spec, get_sort
from mongobit import MongoBit

time_fmt = '%Y-%m-%d %H:%M:%S'


class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        if name not in ('Model', '_Model'):
            # generate the default table name
            if 'coll_name' not in attrs:
                attrs.update(coll_name='{}s'.format(name.lower()))

            if '_id' not in attrs:
                attrs.update(_id=fields.objectid())

            if 'created_at' not in attrs:
                attrs.update(created_at=fields.str())

            if attrs.get('use_ts', True) and 'updated_at' not in attrs:
                attrs.update(updated_at=fields.str())

            attrs.update(_db_fields=dict())
            for k, v in attrs.iteritems():
                if isinstance(v, BaseField):
                    attrs['_db_fields'][k] = v
                    v.name = k

            # generates the unique fields
            attrs.update(_unique_fields=list(),
                         _index_fields=list(),
                         )
            attrs['_index_fields'].append(get_sort('created_at'))

            if 'updated_at' in attrs:
                attrs['_index_fields'].append(get_sort('updated_at desc'))

            for k, v in attrs['_db_fields'].iteritems():
                if 'unique' in v.validators:
                    uk = v.validators['unique']
                    if uk is True or uk is False:
                        ukey = k
                    else:
                        ukey = uk

                    attrs['_unique_fields'].append(ukey)

                if 'index' in v.validators:
                    _idx = v.validators['index']
                    if _idx is True:
                        idx = get_sort('{0} {1}'.format(k, _idx))
                    elif _idx.lower() in ('asc', 'desc'):
                        idx = get_sort('{0} {1}'.format(k, _idx))
                    else:
                        idx = get_sort(_idx)

                    if idx:
                        if isinstance(idx[0], list):
                            attrs['_index_fields'].extend(idx)
                        else:
                            attrs['_index_fields'].append(idx)

        return type.__new__(cls, name, bases, attrs)


class Model(dict):
    __metaclass__ = ModelMeta

    def __init__(self, **kwargs):
        if '_id' not in kwargs:
            self._is_new = True
            self._id = ObjectId()
            self.created_at = strftime(time_fmt)
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

    def update(self, dct=None, **kwargs):
        if isinstance(dct, Model):
            [setattr(self, k, v) for k, v in dct.dict.items()]
        elif isinstance(dct, dict):
            [setattr(self, k, v) for k, v in dct.items()]
        else:
            [setattr(self, k, v) for k, v in kwargs.items()]

    @property
    def dict(self):
        return dict((k, getattr(self, k)) for k in self.__class__._db_fields)

    def __str__(self):
        return unicode(self.dict)

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
            return dict((k, doc[k]) for k in doc if k in cls._db_fields)

        return dict((k, getattr(self, k)) for k in cls._db_fields)

    def save(self, doc={}, safe=True, skip=False, update_ts=None):
        if skip is True:
            self._errors = {}
        else:
            self.validate()

        if update_ts or 'updated_at' in self.__class__._db_fields:
            if doc:
                doc.update(updated_at=strftime(time_fmt))
            else:
                self.update(updated_at=strftime(time_fmt))

        if self.is_valid:
            if doc:
                MongoBit.update(self.__class__._db_alias,
                                self.__class__,
                                self.get_clear_fields(),
                                self.get_clear_fields(doc),
                                safe=safe,
                                )
            else:
                MongoBit.save(self.__class__._db_alias,
                              self.__class__,
                              self.get_clear_fields(),
                              safe=safe,
                              )

    def _remove(self, safe=True):
        MongoBit.remove(self.__class__._db_alias,
                        self.__class__,
                        self,
                        safe=safe,
                        )

    def destroy(self, safe=True):
        self._remove(safe=safe)

    def remove(self, safe=True):
        self.destroy(safe=safe)

    @classmethod
    def total_count(cls):
        return MongoBit.get_total_count(cls._db_alias, cls)

    @classmethod
    def get_count(cls, spec=None):
        return MongoBit.get_count(cls._db_alias, cls, spec)

    @classmethod
    def distinct(cls, field):
        return MongoBit.distinct(cls._db_alias, cls, field)

    @classmethod
    def find_one(cls, id=None, **kwargs):
        return MongoBit.find_one(cls._db_alias, cls, id=id, **kwargs)

    @classmethod
    def find(cls, **kwargs):
        paginate = kwargs.get('paginate', False)
        if paginate is False:
            return MongoBit.find(cls._db_alias, cls, **kwargs)

        from flask import session, request, current_app
        from flask.ext.paginate import Pagination
        if hasattr(current_app, 'y18n'):
            t = current_app.y18n.t
        else:
            t = None

        page = kwargs.get('page', int(request.args.get('page', 1)))
        if 'per_page' in kwargs:
            per_page = kwargs['per_page']
        elif 'per_page' in session:
            per_page = session['per_page']
        elif 'PER_PAGE' in current_app.config:
            per_page = current_app.config['PER_PAGE']
        else:
            per_page = 10

        if 'link_size' in kwargs:
            link_size = kwargs['link_size']
        elif 'LINK_SIZE' in current_app.config:
            link_size = current_app.config['LINK_SIZE']
        else:
            link_size = ''

        if 'link_align' in kwargs:
            alignment = kwargs['link_align']
        elif 'LINK_ALIGN' in current_app.config:
            alignment = current_app.config['LINK_ALIGN']
        else:
            alignment = ''

        skip = (page - 1) * per_page
        kwargs.update(limit=per_page, skip=skip)
        objs = MongoBit.find(cls._db_alias, cls, **kwargs)

        total = kwargs.get('total', 'all')
        if total == 'all':
            total = cls.total_count()
        elif total == 'docs':
            total = objs.count

        args = dict(page=page,
                    per_page=per_page,
                    inner_window=kwargs.get('inner_window', 2),
                    outer_window=kwargs.get('outer_window', 1),
                    prev_label=kwargs.get('prev_label'),
                    next_label=kwargs.get('next_label'),
                    search=kwargs.get('search', False),
                    total=total,
                    display_msg=kwargs.get('display_msg'),
                    search_msg=kwargs.get('search_msg'),
                    record_name=kwargs.get('record_name', 'records'),
                    link_size=link_size,
                    alignment=alignment,
                    )
        if t:
            for k in ('display_msg', 'search_msg', 'prev_label', 'next_label'):
                if not args[k]:
                    args[k] = t(k)

        objs.pagination = Pagination(found=objs.count, **args)
        objs.skip = skip
        return objs

    @property
    def is_valid(self):
        if hasattr(self, '_errors'):
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
        '''cs: case sensitive'''
        cls = self.__class__
        if fields is None:
            fields = cls._unique_fields

        update = not self._is_new
        for field in fields:
            spec = self.get_spec(field, self, cs=cs)
            if spec and update:
                spec.update(_id={'$ne': self.id})

            if spec and cls.find_one(spec=spec):
                self._errors[field] = 'is already taken'

    @property
    def get_spec(self):
        return get_spec

    @property
    def get_sort(self):
        return get_sort
