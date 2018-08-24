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
        # Do not do any special behavior for Message itself.
        if not bases:
            return super().__new__(mcls, name, bases, attrs)

        # A package and full name should be present.
        package = attrs.pop('package', '')
        full_name = attrs.pop('full_name', name)

        # Iterate over the nested messages and enums and

        # Iterate over all the attributes and separate the fields into
        # their own sequence.
        fields = []
        index = 0
        for key, value in copy.copy(attrs).items():
            # Sanity check: If this is not a field, do nothing.
            if not isinstance(value, Field):
                continue

            # Remove the field from the attrs dictionary; the field objects
            # themselves should not be direct attributes.
            attrs.pop(key)

            # Add data that the field requires that we do not take in the
            # constructor because we can derive it from the metaclass.
            # (The goal is to make the declaration syntax as nice as possible.)
            value.mcls_data = {
                'name': key,
                'full_name': '{0}.{1}'.format(full_name, key),
                'index': index,
            }

            # Add a tuple with the field's declaration order, name, and
            # the field itself, in that order.
            fields.append(value)

            # Increment the field index counter.
            index += 1

        # Get a file descriptor object.
        module = attrs.get('__module__', name.lower()).replace('.', '/')
        if module not in _file_descriptor_registry:
            _file_descriptor_registry[module] = descriptor.FileDescriptor(
                name='%s.proto' % module,
                package=package,
                syntax='proto3',
            )

        # Create the underlying proto descriptor.
        # This programatically duplicates the default code generated
        # by protoc.
        desc = descriptor.Descriptor(
            name=name, full_name=full_name,
            file=_file_descriptor_registry[module],
            filename=None, containing_type=None,
            fields=[i.descriptor for i in fields],
            nested_types=[], enum_types=[], extensions=[], oneofs=[],
            syntax='proto3',
        )
        _file_descriptor_registry[module].message_types_by_name[name] = desc

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

    @classmethod
    def __prepare__(mcls, name, bases, **kwargs):
        return collections.OrderedDict()

    @property
    def meta(cls):
        return cls._meta

    def pb(cls, obj=None):
        """Return the underlying protobuf Message class."""
        if not obj:
            return cls.meta.pb
        if not isinstance(obj, cls):
            raise TypeError('%r is not an instance of %s' % (obj, cls.__name__))
        return obj._pb

    def serialize(cls, instance) -> bytes:
        """Return the serialized proto.

        Args:
            instance: An instance of this message type.

        Returns:
            bytes: The serialized representation of the protocol buffer.
        """
        return cls.pb(instance).SerializeToString()

    def deserialize(cls, payload: bytes):
        """Given a serialized proto, deserialize it into a Message instance.

        Args:
            payload (bytes): The serialized proto.

        Returns
            cls: An instance of the message class against which this
                method was called.
        """
        return cls(cls.pb().FromString(payload))


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


_file_descriptor_registry = {}
