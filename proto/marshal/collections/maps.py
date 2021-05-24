# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
from typing import Dict, Set

import proto
from proto.utils import cached_property


class MapComposite(collections.abc.MutableMapping):
    """A view around a mutable sequence in protocol buffers.

    This implements the full Python MutableMapping interface, but all methods
    modify the underlying field container directly.
    """

    @cached_property
    def _pb_type(self):
        """Return the protocol buffer type for this sequence."""
        # Huzzah, another hack. Still less bad than RepeatedComposite.
        return type(self.pb.GetEntryClass()().value)

    def __init__(self, sequence, *, marshal):
        """Initialize a wrapper around a protobuf map.

        Args:
            sequence: A protocol buffers map.
            marshal (~.MarshalRegistry): An instantiated marshal, used to
                convert values going to and from this map.
        """
        self._pb = sequence
        self._marshal = marshal
        self._item_cache: Dict = {}
        self._stale_keys: Set[str] = set()

    def __contains__(self, key):
        # Protocol buffers is so permissive that querying for the existence
        # of a key will in of itself create it.
        #
        # By taking a tuple of the keys and querying that, we avoid sending
        # the lookup to protocol buffers and therefore avoid creating the key.
        if key in self._item_cache:
            return True
        return key in tuple(self.keys())

    def __getitem__(self, key):
        # We handle raising KeyError ourselves, because otherwise protocol
        # buffers will create the key if it does not exist.
        value = self._item_cache.get(key, _Empty.shared)

        if isinstance(value, _Empty):
            if key not in self:
                raise KeyError(key)
            value = self._marshal.to_python(self._pb_type, self.pb[key])

            # This is the first domino in a hacky workaround that is completed
            # in `fields._FieldDescriptor.__set__`. Because of the by-value nature
            # of protobufs (which conflicts with the by-reference nature of Python),
            # proto-plus objects that are yielded from MapFields must immediately
            # write to their internal pb2 object whenever their fields are updated.
            # This is a new requirement as always writing to a proto-plus object's
            # inner pb2 protobuf used to be the default, but has been moved to a
            # lazy-syncing system for performance reasons.
            if isinstance(value, proto.Message):
                value._always_commit = True

            self._item_cache[key] = value

        return value

    def __setitem__(self, key, value):
        self._item_cache[key] = value
        self._stale_keys.add(key)
        # self._sync_key(key, value)

    def _sync_all_keys(self):
        for key in self._stale_keys:
            self._sync_key(key)
        self._stale_keys.clear()

    def _sync_key(self, key, value = None):
        value = value or self._item_cache.pop(key, None)
        if value is None:
            self.pb.pop(key)
            return
        pb_value = self._marshal.to_proto(self._pb_type, value, strict=True)

        # Directly setting a key is not allowed; however, protocol buffers
        # is so permissive that querying for the existence of a key will in
        # of itself create it.
        #
        # Therefore, we create a key that way (clearing any fields that may
        # be set) and then merge in our values.
        self.pb[key].Clear()
        self.pb[key].MergeFrom(pb_value)

    def __delitem__(self, key):
        self._item_cache.pop(key, None)
        self._stale_keys.add(key)
        # self.pb.pop(key)

    def __len__(self):
        _all_keys = set(list(self._item_cache.keys()))
        _all_keys = _all_keys.union(list(self.pb.keys()))
        return len(_all_keys)
        # return len(self.pb)

    def __iter__(self):
        self._sync_all_keys()
        return iter(self.pb)

    @property
    def pb(self):
        return self._pb


class _Empty:
    pass


_Empty.shared = _Empty()