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
import copy
from typing import List, Type

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import symbol_database

from proto.fields import Field

sym_db = symbol_database.Default()


class MessageMeta(type):
    """A metaclass for building and registering Message subclasses."""

    def __new__(mcls, name, bases, attrs):
        # A package and full name should be present.
        package = attrs.pop('package')
        full_name = attrs.pop('full_name')

        # Iterate over the nested messages and enums and

        # Iterate over all the attributes and separate the fields into
        # their own sequence.
        fields = []
        index = 0
        for name, attr in copy.copy(attrs).items():
            # Sanity check: If this is not a field, do nothing.
            if not isinstance(attr, fields.Field):
                continue

            # Remove the field from the attrs dictionary; the field objects
            # themselves should not be direct attributes.
            attrs.pop(name)

            # Add data that the field requires that we do not take in the
            # constructor because we can derive it from the metaclass.
            # (The goal is to make the declaration syntax as nice as possible.)
            attr.mcs_data = {
                'name': name,
                'full_name': '{0}.{1}'.format(full_name, name),
                'index': index,
            }

            # Add a tuple with the field's declaration order, name, and
            # the field itself, in that order.
            fields.append(attr)

            # Increment the field index counter.
            index += 1

        # Create the underlying proto descriptor.
        # This programatically duplicates the default code generated
        # by protoc.
        desc = descriptor.Descriptor(
            name=name, full_name=full_name,
            filename=None, containing_type=None,
            fields=[i._desc for i in fields],
            nested_types=[], enum_types=[], extensions=[], oneofs=[],
            syntax='proto3',
        )

        # Create the stock protobuf Message.
        pb_message = reflection.GeneratedProtocolMessageType(
            name, (message.Message,), {'DESCRIPTOR': desc, '__module__': None},
        )
        sym_db.RegisterMessage(pb_message)

        # Create the MessageInfo instance to be attached to this message.
        attrs['_meta'] = MessageInfo(
            pb=pb_message,
            fields=fields,
            full_name=full_name,
            package=package,
        )

        # Run the superclass constructor.
        cls = super().__new__(mcls, name, bases, attrs)

        # Done; return the message class.
        return cls

    def __prepare__(mcls, name, bases, **kwargs):
        return collections.OrderedDict()

    def serialize(cls, instance) -> bytes:
        """Return the serialized proto.

        Args:
            instance: An instance of this message type.

        Returns:
            bytes: The serialized representation of the protocol buffer.
        """
        return instance.pb.SerializeToString()

    def deserialize(cls, payload: bytes):
        """Given a serialized proto, deserialize it into a Message instance.

        Args:
            payload (bytes): The serialized proto.

        Returns
            cls: An instance of the message class against which this
                method was called.
        """
        return cls(cls._meta.pb.FromString(payload))


class MessageInfo:
    """Metadata about a message or enum.

    Args:
        meta (type): A class with attributes that match the
            attributes of these instances.
        fields (Tuple[~.fields.Field]): The fields declared on the message.
    """
    def __init__(self, *, pb: Type[message.Message], fields: List[Field],
                 package: str, full_name: str) -> None:
        self.pb = pb
        self.package = package
        self.full_name = full_name
        self.fields = collections.OrderedDict([
            (i.name, i) for i in fields
        ])
        self.fields_by_number = collections.OrderedDict([
            (i.number, i) for i in fields
        ])
