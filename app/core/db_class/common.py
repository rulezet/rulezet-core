"""Column types and small helpers shared by several model modules.
"""
from sqlalchemy import String
from sqlalchemy import TypeDecorator
import json
import re as _re
import uuid as _uuid_mod


class JSONEncodedList(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        if value is None:
            return '[]'
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        return json.loads(value)    


def _gen_uuid():
    return str(_uuid_mod.uuid4())


def _slugify(name):
    s = name.lower().strip()
    s = _re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')[:48]
