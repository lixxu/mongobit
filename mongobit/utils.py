#!/usr/bin/env python
#-*- coding: utf-8 -*-

import re
from pymongo import ASCENDING as ASC, DESCENDING as DESC


def get_value(v, cs=False):
    '''cs: case sensitive'''
    if v:
        if cs is False:
            return re.compile(ur'^{0}$'.format(re.escape(v)), re.I)

        return v

    return None


# for composite field
# format is: 'field1, field2, field3, ...'
def get_spec(field, doc, cs=False):
    if ',' in field:
        spec = dict()
        for k in field.split(','):
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
    for items in sort.split(';'):
        lst = []
        for item in items.strip().split(','):
            item = item.strip()
            if ' ' in item:
                field, _sort = item.split(' ')[:2]
                lst.append((field, DESC if 'desc' in _sort.lower() else ASC))
            else:
                lst.append((item, ASC))

        if lst:
            lsts.append(lst)

    return lsts[0] if len(lsts) == 1 else lsts
