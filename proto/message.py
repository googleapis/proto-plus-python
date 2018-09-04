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
import collections.abc
import copy
import re
from typing import List, Type

from google.protobuf import descriptor
from google.protobuf.descriptor_pb2 import MessageOptions
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import symbol_database

from proto.fields import Field
from proto.fields import MapField
from proto.fields import RepeatedField
from proto.marshal import marshal
from proto.marshal.types.message import MessageMarshal
from proto.primitives import ProtoType


class MessageMeta(type):
    """A metaclass for building and registering Message subclasses."""

    def __new__(mcls, name, bases, attrs):
        # Do not do any special behavior for Message itself.
        if not bases:
            return super().__new__(mcls, name, bases, attrs)

        # Pop metadata off the attrs.
        Meta = attrs.pop('Meta', object())

        # A package and full name should be present.
        package = getattr(Meta, 'package', '')
        full_name = getattr(Meta, 'full_name', name)

        # Special case: Maps. Map fields are special; they are essentially
        # shorthand for a nested message and a repeated field of that message.
        # Decompose each map into its constituent form.
        # https://developers.google.com/protocol-buffers/docs/proto3#maps
        for key, field in copy.copy(attrs).items():
            if not isinstance(field, MapField):
                continue

            # Determine the name of the entry message.
            message_name = '{pascal_key}Entry'.format(
                pascal_key=re.sub(
                    r'_[\w]',
                    lambda m: m.group().upper(),
                    key,
                ).capitalize(),
            )

            # Create the "entry" message (with the key and value fields).
            attrs[message_name] = MessageMeta(message_name, (Message,), {
                'key': Field(field.map_key_type, number=1),
                'value': Field(field.proto_type, number=2),
                'Meta': type('Meta', (object,), {
                    'full_name': '{0}.{1}'.format(full_name, message_name),
                    'options': MessageOptions(map_entry=True),
                    'package': package,
                }),
            })

            # Create the repeated field for the entry message.
            attrs[key] = RepeatedField(ProtoType.MESSAGE,
                number=field.number,
                message=attrs[message_name],
            )

        # Okay, now we deal with all the rest of the fields.
        # Iterate over all the attributes and separate the fields into
        # their own sequence.
        fields = []
        index = 0
        for key, field in copy.copy(attrs).items():
            # Sanity check: If this is not a field, do nothing.
            if not isinstance(field, Field):
                continue

            # Remove the field from the attrs dictionary; the field objects
            # themselves should not valuebe direct attributes.
            attrs.pop(key)

            # Add data that the field requires that we do not take in the
            # constructor because we can derive it from the metaclass.
            # (The goal is to make the declaration syntax as nice as possible.)
            field.mcls_data = {
                'name': key,
                'full_name': '{0}.{1}'.format(full_name, key),
                'index': index,
            }

            # Add a tuple with the field's declaration order, name, and
            # the field itself, in that order.
            fields.append(field)

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

        # Retrieve any message options.
        opts = getattr(Meta, 'options', MessageOptions())

        # Create the underlying proto descriptor.
        # This programatically duplicates the default code generated
        # by protoc.
        desc = descriptor.Descriptor(
            name=name, full_name=full_name,
            file=_file_descriptor_registry[module],
            filename=None, containing_type=None,
            fields=[i.descriptor for i in fields],
            nested_types=[], enum_types=[], extensions=[], oneofs=[],
            serialized_options=opts.SerializeToString(),
            syntax='proto3',
        )
        _file_descriptor_registry[module].message_types_by_name[name] = desc

        # Create the stock protobuf Message.
        pb_message = reflection.GeneratedProtocolMessageType(
            name, (message.Message,), {'DESCRIPTOR': desc, '__module__': None},
        )
        symbol_database.Default().RegisterMessage(pb_message)

        # Create the MessageInfo instance to be attached to this message.
        attrs['_meta'] = MessageInfo(
            pb=pb_message,
            fields=fields,
            full_name=full_name,
            package=package,
            options=opts,
        )

        # Run the superclass constructor.
        cls = super().__new__(mcls, name, bases, attrs)

        # Register the new class with the marshal.
        marshal.register(pb_message, MessageMarshal(pb_message, cls))

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
        if obj is None:
            return cls.meta.pb
        if not isinstance(obj, cls):
            raise TypeError('%r is not an instance of %s' % (
                obj, cls.__name__,
            ))
        return obj._pb

    def wrap(cls, pb):
        """Return a Message object that shallowly wraps the descriptor.

        Args:
            pb: A protocol buffer object, such as would be returned by
                :meth:`pb`.
        """
        return cls(pb, __wrap_original=True)

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


class Message(metaclass=MessageMeta):
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
        # Sanity check: Did we get something not on that list? Error if so.
        if mapping and not isinstance(
                mapping, (collections.abc.Mapping, type(self), self._meta.pb)):
            raise TypeError('Invalid constructor input for %s: %r' % (
                self.__class__.__name__, mapping,
            ))

        # Handle the first two cases: they both involve keeping
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

    def __bool__(self):
        """Return True if any field is truthy, False otherwise."""
        return any([getattr(self, k) for k in self._meta.fields.keys()])

    def __contains__(self, key):
        """Return True if this field was set to something non-zero on the wire.

        In most cases, this method will return True when ``__getattr__``
        would return a truthy value and False when it would return a falsy
        value, so explicitly calling this is not useful.

        The exception case is empty messages explicitly set on the wire,
        which are falsy from ``__getattr__``. This method allows to
        distinguish between an explicitly provided empty message and the
        absence of that message, which is useful in some edge cases.

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
            return bool(pb_value)

    def __delattr__(self, key):
        """Delete the value on the given field.

        This is generally equivalent to setting a falsy value.
        """
        self._pb.ClearField(key)

    def __eq__(self, other):
        """Return True if the messages are equal, False otherwise."""
        # If these are the same type, use internal protobuf's equality check.
        if isinstance(other, type(self)):
            return self._pb == other._pb

        # If the other type is the target protobuf object, honor that also.
        if isinstance(other, self._meta.pb):
            return self._pb == other

        # Ask the other object.
        return NotImplemented

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

    def __ne__(self, other):
        """Return True if the messages are unequal, False otherwise."""
        return not self == other

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


class MessageInfo:
    """Metadata about a message.

    Args:
        pb (type): The underlying protobuf message.
        fields (Tuple[~.fields.Field]): The fields declared on the message.
        package (str): The proto package
        full_name (str): The full name of the message.
        options (~.descriptor_pb2.MessageOptions): Any options that were
            set on the message.
    """
    def __init__(self, *, pb: Type[message.Message], fields: List[Field],
                 package: str, full_name: str,
                 options: MessageOptions) -> None:
        self.pb = pb
        self.package = package
        self.full_name = full_name
        self.options = options
        self.fields = collections.OrderedDict([
            (i.name, i) for i in fields
        ])
        self.fields_by_number = collections.OrderedDict([
            (i.number, i) for i in fields
        ])


_file_descriptor_registry = {}
