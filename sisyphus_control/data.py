import asyncio
from collections import UserDict
from typing import Any, Dict


class Model(UserDict):
    """Holds the data about one entity in a collection."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

    async def update_from_changes(self, changes) -> bool:
        data_changed = False
        for key, value in changes.items():
            if not key in self or self[key] != value:
                self[key] = value
                data_changed = True

        return data_changed


class Collection(UserDict):
    """Holds all the data returned by the table, as Model objects keyed by ID."""

    def __init__(self):
        super().__init__()
        self._listeners = []

    async def add(self, item: Model):
        id = item.data["id"]
        if id in self:
            should_notify = await self[id].update_from_changes(item)
        else:
            self[id] = item
            should_notify = True

        if should_notify:
            await self._notify_listeners()

    def add_listener(self, listener):
        self._listeners.append(listener)

    def remove_listener(self, listener):
        self._listeners.remove(listener)

    async def _notify_listeners(self):
        listeners = list(self._listeners)
        for listener in listeners:
            await asyncio.coroutine(listener)()


if __name__ == "__main__":
    import aiounittest
    import unittest
    from unittest.mock import MagicMock

    class CollectionTests(aiounittest.AsyncTestCase):
        async def test_add(self):
            coll = Collection()
            item = Model({"id": 12345, "key": "value"})
            await coll.add(item)
            returned = coll.get(12345)

            self.assertEqual(item, returned)

        async def test_update_does_not_remove_value(self):
            coll = Collection()
            item = Model({"id": 12345, "key": "value"})
            await coll.add(item)
            delta = Model({"id": 12345})
            await coll.add(delta)

            returned = coll.get(12345)
            self.assertEqual(returned, item)

        async def test_update_adds_new_keys(self):
            coll = Collection()
            item = Model({"id": 12345, "key": "value"})
            await coll.add(item)
            delta = Model({"id": 12345, "key2": "value2"})
            await coll.add(delta)

            returned = coll.get(12345)
            expected = Model({"id": 12345, "key": "value", "key2": "value2"})
            self.assertEqual(returned, expected)

        async def test_update_changes_values(self):
            coll = Collection()
            item = Model({"id": 12345, "key": "value"})
            await coll.add(item)
            delta = Model({"id": 12345, "key": "new_value"})
            await coll.add(delta)

            returned = coll.get(12345)
            self.assertEqual(returned, delta)

        async def test_update_notifies_listeners(self):
            coll = Collection()
            item = Model({"id": 12345, "key": "value"})
            await coll.add(item)

            listener = MagicMock()
            item.add_listener(listener)

            delta = Model({"id": 12345, "key": "new_value"})
            await coll.add(delta)

            assert listener.called

        async def test_no_op_update_does_not_notify_listeners(self):
            coll = Collection()
            item = Model({"id": 12345, "key": "value"})
            await coll.add(item)

            listener = MagicMock()
            item.add_listener(listener)

            delta = Model({"id": 12345, "key": "value"})
            await coll.add(delta)

            assert not listener.called

    unittest.main()
