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
        if isinstance(mapping, self._desc):
            self.pb = copy.copy(mapping)
            if kwargs:
                self.pb.MergeFrom(self._desc(**kwargs))
            return

        # Handle the remaining case by converging the mapping and kwargs
        # dictionaries (with kwargs winning), and saving a descriptor
        # based on that.
        if mapping is None:
            mapping = {}
        mapping.update(kwargs)
        self.pb = self._desc(**mapping)

    def __contains__(self, key):
        """Return True if the field is present on the message, False otherwise.

        Because of how protocol buffers approaches fields and values, this
        method essentially returns True as long as the field exists
        on the message, regardless of whether it is set.

        Similarly, the complimentary ``__getitem__`` method promises to always
        return a valid value of the correct type.
        """
        return key in type(self)._meta.fields

    def __getitem__(self, key):
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
        presence, use ``has_wire_field``

        .. note::

            Some well-known protocol buffer types
            (e.g. ``google.protobuf.Timestamp``) will be converted to
            their Python equivalents. See the ``marshal`` module for
            mode details.
        """
        pb_type = self._meta.fields[key].pb_type
        pb_value = getattr(self.pb, key)
        return marshal.to_python(self, pb_type, pb_value,
            absent=not self.has_wire_field(key),
        )

    def __setitem__(self, key, value):
        """Set the value on the given field.

        For well-known protocol buffer types which are marshalled, either
        the protocol buffer object or the Python equivalent is accepted.
        """
        pb_type = self._meta.fields[key].pb_type
        pb_value = marshal.to_proto(self, key, value)
        if pb_value is None:
            self.pb.ClearField(key)
        else:
            self.pb.MergeFrom(self._desc(key=pb_value))

    def __delitem__(self, key):
        """Delete the value on the given field.

        This is generally equivalent to setting a falsy value."""
        self.pb.ClearField(key)

    def has_wire_field(self, key):
        """Return True if this field was set to something non-zero on the wire.

        In most cases, this method will return True when ``__getitem__``
        would return a truthy value and False when it would return a falsy
        value, so explicitly calling this is not useful.

        The exception case is empty messages explicitly set on the wire,
        which are falsy from ``__getitem__``. This method allows to
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
        return self.pb.HasField(key)

    def serialize(self) -> bytes:
        """Return the serialized proto.

        Returns:
            bytes: The serialized representation of the protocol buffer.
        """
        return self.pb.SerializeToString()

    @classmethod
    def deserialize(cls, payload: bytes):
        """Given a serialized proto, deserialize it into a Message instance.

        Args:
            payload (bytes): The serialized proto.

        Returns
            cls: An instance of the message class against which this
                method was called.
        """
        return cls(cls._desc.FromString(payload))
