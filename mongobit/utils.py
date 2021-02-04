#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import warnings
import re
import six
from pymongo import ASCENDING as ASC, DESCENDING as DESC


def get_value(v, cs=False):
    """Case sensitive: cs."""
    if v:
        if cs is False:
            if isinstance(v, six.string_types):
                vv = re.escape(v)
            else:
                vv = v

            return re.compile(six.u(r"^{0}$".format(vv)), re.I)

        return v

    return None


# for composite field
# format is: 'field1, field2, field3, ...'
def get_spec(field, doc, cs=False):
    if "," in field:
        spec = {}
        for k in field.split(","):
            k = k.strip()
            v = get_value(doc[k], cs=cs)
            if v:
                spec[k] = v
            else:
                break

        return spec

    v = get_value(doc[field], cs=cs)
    return {field: v} if v else None


def get_sort(sort):
    if sort is None or isinstance(sort, list):
        return sort

    lsts = []
    for items in sort.split(";"):
        lst = []
        for item in items.strip().split(","):
            item = item.strip()
            if " " in item:
                field, _sort = item.split(" ")[:2]
                lst.append((field, DESC if "desc" in _sort.lower() else ASC))
            else:
                lst.append((item, ASC))

        if lst:
            lsts.append(lst)

    return lsts[0] if len(lsts) == 1 else lsts


def safe_deprecation(kwargs):
    if "safe" in kwargs:
        warnings.warn(
            "safe is deprecated, please use w instead", DeprecationWarning
        )
