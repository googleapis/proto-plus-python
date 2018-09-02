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

import copy

from proto import meta
from proto.marshal import marshal


class Message(metaclass=meta.MessageMeta):
    """The abstract base class for a message.

    Args:
        mapping (Union[dict, ~.Message]): A dictionary or message to be
            used to determine the values for this message.
        kwargs (dict): Keys and values corresponding to the fields of the
            message.
    """
    def __init__(self, mapping=None, **kwargs):
        # We accept several things for `mapping`:
        #   * An instance of this class.
        #   * An instance of the underlying protobuf descriptor class.
        #   * A dict
        #   * Nothing (keyword arguments only).
        #
        # To start, handle the first two cases: they both involve keeping
        # a copy of the underlying protobuf descriptor instance.
        if isinstance(mapping, type(self)):
            mapping = mapping._pb
        if isinstance(mapping, self._meta.pb):
            # Make a copy of the mapping.
            # This is a constructor for a new object, so users will assume
            # that it will not have side effects on the arguments being
            # passed in.
            #
            # The `__wrap_original` argument is private API to override
            # this behavior, because `MessageMarshal` actually does want to
            # wrap the original argument it was given. The `wrap` method
            # on the metaclass is the public API for this behavior.
            if not kwargs.pop('__wrap_original', False):
                mapping = copy.copy(mapping)
            self._pb = mapping
            if kwargs:
                self._pb.MergeFrom(self._meta.pb(**kwargs))
            return

        # Handle the remaining case by converging the mapping and kwargs
        # dictionaries (with kwargs winning), and saving a descriptor
        # based on that.
        if mapping is None:
            mapping = {}
        mapping.update(kwargs)

        # Update the mapping to address any values that need to be
        # coerced.
        for key, value in copy.copy(mapping).items():
            pb_type = self._meta.fields[key].pb_type
            pb_value = marshal.to_proto(pb_type, value)
            if pb_value is None:
                mapping.pop(key)
            else:
                mapping[key] = pb_value

        # Create the internal protocol buffer.
        self._pb = self._meta.pb(**mapping)

    def __getattr__(self, key):
        """Retrieve the given field's value.

        In protocol buffers, the presence of a field on a message is
        sufficient for it to always be "present".

        For primitives, a value of the correct type will always be returned
        (the "falsy" values in protocol buffers consistently match those
        in Python). For repeated fields, the falsy value is always an empty
        sequence.

        For messages, protocol buffers does distinguish between an empty
        message and absence, but this distinction is subtle and rarely
        relevant. Therefore, this method always returns an empty message
        (following the official implementation). To check for message
        presence, use ``key in self`` (in other words, ``__contains__``).

        .. note::

            Some well-known protocol buffer types
            (e.g. ``google.protobuf.Timestamp``) will be converted to
            their Python equivalents. See the ``marshal`` module for
            mode details.
        """
        pb_type = self._meta.fields[key].pb_type
        pb_value = getattr(self._pb, key)
        return marshal.to_python(pb_type, pb_value, absent=key not in self)

    def __setattr__(self, key, value):
        """Set the value on the given field.

        For well-known protocol buffer types which are marshalled, either
        the protocol buffer object or the Python equivalent is accepted.
        """
        if key.startswith('_'):
            return super().__setattr__(key, value)
        pb_type = self._meta.fields[key].pb_type
        pb_value = marshal.to_proto(pb_type, value)

        # We *always* clear the existing field.
        # This is the only way to successfully write nested falsy values,
        # because otherwise MergeFrom will no-op on them.
        self._pb.ClearField(key)

        # Merge in the value being set.
        if pb_value is not None:
            self._pb.MergeFrom(self._meta.pb(**{key: pb_value}))

    def __delattr__(self, key):
        """Delete the value on the given field.

        This is generally equivalent to setting a falsy value."""
        self._pb.ClearField(key)

    def __contains__(self, key):
        """Return True if this field was set to something non-zero on the wire.

        In most cases, this method will return True when ``__getattr__``
        would return a truthy value and False when it would return a falsy
        value, so explicitly calling this is not useful.

        The exception case is empty messages explicitly set on the wire,
        which are falsy from ``__getattr__``. This method allows to
        distinguish between an explcitly provided empty message and the
        absence of that meessage, which is useful in some edge cases.

        The most common edge case is the use of ``google.protobuf.BoolValue``
        to get a boolean that distinguishes between ``False`` and ``None``
        (or the same for a string, int, etc.). This library transparently
        handles that case for you, but this method remains available to
        accomodate cases not automatically covered.

        Args:
            key (str): The name of the field.

        Returns:
            bool: Whether the field's value corresponds to a non-empty
                wire serialization.
        """
        pb_value = getattr(self._pb, key)
        try:
            # Protocol buffers "HasField" is unfriendly; it only works
            # against composite, non-repeated fields, and raises ValueError
            # against any repeated field or primitive.
            #
            # There is no good way to test whether it is valid to provide
            # a field to this method, so sadly we are stuck with a
            # somewhat inefficient try/except.
            return self._pb.HasField(key)
        except ValueError:
            if hasattr(pb_value, 'SerializeToString'):
                return bool(pb_value.SerializeToString())
            return bool(pb_value)
