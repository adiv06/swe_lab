"""In-memory stand-ins for the pymongo collection methods the app uses."""

import copy

from pymongo.errors import DuplicateKeyError


def get_path(document, path):
    value = document
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def set_path(document, path, value):
    *parents, last = path.split(".")
    for part in parents:
        document = document.setdefault(part, {})
    document[last] = value


def unset_path(document, path):
    *parents, last = path.split(".")
    for part in parents:
        document = document.get(part, {})
    document.pop(last, None)


def matches(document, query):
    for field, condition in query.items():
        value = get_path(document, field)
        if isinstance(condition, dict):
            for op, operand in condition.items():
                if value is None:
                    return False
                if op == "$gte" and not value >= operand:
                    return False
                if op == "$lte" and not value <= operand:
                    return False
                if op == "$in" and value not in operand:
                    return False
        elif isinstance(value, list):
            if condition not in value:
                return False
        elif value != condition:
            return False
    return True


class FakeCollection:
    def __init__(self):
        self.documents = {}

    def create_index(self, *_args, **_kwargs):
        return None

    def insert_one(self, document):
        if document["_id"] in self.documents:
            raise DuplicateKeyError("duplicate key")
        self.documents[document["_id"]] = copy.deepcopy(document)

    def find_one(self, query, projection=None):
        return next(self.find(query), None)

    def find(self, query):
        return (copy.deepcopy(d) for d in list(self.documents.values()) if matches(d, query))

    def replace_one(self, query, replacement, upsert=False):
        self.documents[replacement["_id"]] = copy.deepcopy(replacement)

    def delete_one(self, query):
        found = self.find_one(query)
        if found:
            del self.documents[found["_id"]]

    def _apply(self, document, update):
        for field, amount in update.get("$inc", {}).items():
            set_path(document, field, (get_path(document, field) or 0) + amount)
        for field, value in update.get("$set", {}).items():
            set_path(document, field, value)
        for field in update.get("$unset", {}):
            unset_path(document, field)
        for field, value in update.get("$addToSet", {}).items():
            if value not in document.setdefault(field, []):
                document[field].append(value)

    def update_one(self, query, update, upsert=False):
        current = self.find_one(query)
        if current is None:
            if not upsert:
                return
            document = {k: v for k, v in query.items() if not isinstance(v, dict)}
            document.update(update.get("$setOnInsert", {}))
            self._apply(document, update)
            self.insert_one(document)
            return
        self._apply(self.documents[current["_id"]], update)

    def find_one_and_update(self, query, update, return_document=None):
        current = self.find_one(query)
        if current is None:
            return None
        self._apply(self.documents[current["_id"]], update)
        return copy.deepcopy(self.documents[current["_id"]])

    def find_one_and_delete(self, query):
        current = self.find_one(query)
        if current is not None:
            del self.documents[current["_id"]]
        return current


class FakeDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection())
