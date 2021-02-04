#!/usr/bin/env python
# -*- coding: utf-8 -*-

import types
import datetime
import six
from bson.objectid import ObjectId


class BaseField(object):
    default = None

    def __init__(self, **kwargs):
        self.validators = {}
        self.default = kwargs.get("default", self.__class__.default)
        self.get_validators(kwargs)
        cls = self.__class__
        if not hasattr(cls, "type"):
            tp = cls.__name__.replace("Field", "Type")
            if tp == "AnyType":
                cls.type = None
            elif tp == "StringType":
                cls.type = str
            elif tp == "UnicodeType":
                cls.type = six.text_type
            elif tp == "BoolType":
                cls.type = bool
            elif tp == "DateType":
                cls.type = datetime.date
            elif tp == "DateTimeType":
                cls.type = datetime.datetime
            elif tp == "ObjectIdType":
                cls.type = ObjectId
            else:
                if six.PY2:
                    cls.type = getattr(types, tp)
                else:
                    import builtins

                    cls.type = getattr(builtins, tp[:-4].lower())

    def get_validators(self, kwargs):
        for k in (
            "required",
            "null",
            "max_size",
            "min_size",
            "unique",
            "index",
        ):
            if k in kwargs:
                self.validators[k] = kwargs[k]

    def validates(self, obj, val):
        errors = obj._errors[self.name]
        if self.validators.get("required", False) and not val:
            errors.append("can't be blank")

        if "min_size" in self.validators:
            min_size = self.validators["min_size"]
            if min_size and len(val) < min_size:
                errors.append("{0} chars at least".format(min_size))

        if "max_size" in self.validators:
            max_size = self.validators["max_size"]
            if max_size and len(val) > max_size:
                errors.append("{0} chars at most".format(max_size))

        return len(errors) == 0

    def __get__(self, obj, tp=None):
        if obj is None:
            return self

        if self.name in obj.__dict__:
            return obj.__dict__[self.name]

        if self.default is not None:
            return self.default

        if self.__class__.__name__.startswith(
            ("Str", "Unicode", "List", "Tuple", "Dict")
        ):
            return self.__class__.type()

        return None

    def __set__(self, obj, value):
        if not hasattr(obj, "_errors"):
            obj._errors = dict()

        errors = obj._errors[self.name] = []
        if self.type is None:
            obj.__dict__[self.name] = value
        elif self.validators.get("null", False) and value is None:
            obj.__dict__[self.name] = None
        else:
            if self.type.__name__ in ("str", "unicode"):
                tp = six.string_types
            elif self.type in six.integer_types:
                tp = six.integer_types
            else:
                tp = self.type

            if not isinstance(value, tp):
                errors.append("not {0!r} type".format(self.type))
            elif self.validates(obj, value) is True:
                errors = []
                obj.__dict__[self.name] = value


class IntField(BaseField):
    pass


class FloatField(BaseField):
    pass


class StringField(BaseField):
    pass


TextField = StringField


class UnicodeField(BaseField):
    pass


class ListField(BaseField):
    default = []


class DictField(BaseField):
    default = {}


class TupleField(BaseField):
    pass


class DateField(BaseField):
    pass


class DateTimeField(BaseField):
    pass


class BoolField(BaseField):
    pass


class ObjectIdField(BaseField):
    pass


class AnyField(BaseField):
    pass


class Fields(object):
    pass


fields = Fields()
fields.str = StringField
fields.string = StringField
fields.text = TextField
fields.int = IntField
fields.float = FloatField
fields.unicode = UnicodeField
fields.tuple = TupleField
fields.dict = DictField
fields.list = ListField
fields.bool = BoolField
fields.date = DateField
fields.datetime = DateTimeField
fields.objectid = ObjectIdField
fields.any = AnyField
