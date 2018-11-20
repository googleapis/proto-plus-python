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
import inspect
import re
import uuid
from typing import List, Mapping, Type

from google.protobuf import descriptor_pb2
from google.protobuf import descriptor_pool
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import symbol_database

from proto.fields import Field
from proto.fields import MapField
from proto.fields import RepeatedField
from proto.marshal.marshal import marshal
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
        local_path = tuple(attrs.get('__qualname__', name).split('.'))

        # Sanity check: We get the wrong full name if a class is declared
        # inside a function local scope; correct this.
        if '<locals>' in local_path:
            ix = local_path.index('<locals>')
            local_path = local_path[:ix - 1] + local_path[ix + 1:]

        # Determine the full name in protocol buffers.
        full_name = getattr(Meta, 'full_name',
            '.'.join((package,) + local_path).lstrip('.'),
        )

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
                '__module__': attrs.get('__module__', None),
                '__qualname__': '{prefix}.{name}'.format(
                    prefix=attrs.get('__qualname__', name),
                    name=message_name,
                ),
                'key': Field(field.map_key_type, number=1),
                'value': Field(field.proto_type, number=2,
                    enum=field.enum,
                    message=field.message,
                ),
                'Meta': type('Meta', (object,), {
                    'options': descriptor_pb2.MessageOptions(map_entry=True),
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
        oneofs = collections.OrderedDict()
        proto_imports = set()
        index = 0
        for key, field in copy.copy(attrs).items():
            # Sanity check: If this is not a field, do nothing.
            if not isinstance(field, Field):
                continue

            # Remove the field from the attrs dictionary; the field objects
            # themselves should not be direct attributes.
            attrs.pop(key)

            # Add data that the field requires that we do not take in the
            # constructor because we can derive it from the metaclass.
            # (The goal is to make the declaration syntax as nice as possible.)
            field.mcls_data = {
                'name': key,
                'parent_name': full_name,
                'index': index,
                'package': package,
            }

            # Add the field to the list of fields.
            fields.append(field)

            # If this field is part of a "oneof", ensure the oneof itself
            # is represented.
            if field.oneof:
                # Keep a running tally of the index of each oneof, and assign
                # that index to the field's descriptor.
                oneofs.setdefault(field.oneof, len(oneofs))
                field.descriptor.oneof_index = oneofs[field.oneof]

            # If this field references a message, it may be from another
            # proto file; ensure we know about the import (to faithfully
            # construct our file descriptor proto).
            if field.message and not isinstance(field.message, str):
                field_msg = field.message
                if hasattr(field_msg, 'pb') and callable(field_msg.pb):
                    field_msg = field_msg.pb()

                # Sanity check: The field's message may not yet be defined if
                # it was a Message defined in the same file, and the file
                # descriptor proto has not yet been generated.
                #
                # We do nothing in this situation; everything will be handled
                # correctly when the file descriptor is created later.
                if field_msg:
                    proto_imports.add(field_msg.DESCRIPTOR.file.name)
                    symbol_database.Default().RegisterMessage(field_msg)

            # Increment the field index counter.
            index += 1

        # Determine the filename.
        # We determine an appropriate proto filename based on the
        # Python module. If the filename has already been used (which would
        # cause collisions in the descriptor pool), we salt it.
        filename = '{0}.proto'.format(
            attrs.get('__module__', name.lower()).replace('.', '/')
        )

        # Get or create the information about the file, including the
        # descriptor to which the new message descriptor shall be added.
        file_info = _FileInfo.registry.setdefault(filename, _FileInfo(
            descriptor=descriptor_pb2.FileDescriptorProto(
                name=filename,
                package=package,
                syntax='proto3',
            ),
            messages=collections.OrderedDict(),
            name=filename,
            nested={},
        ))

        # Ensure any imports that would be necessary are assigned to the file
        # descriptor proto being created.
        for proto_import in proto_imports:
            if proto_import not in file_info.descriptor.dependency:
                file_info.descriptor.dependency.append(proto_import)

        # Retrieve any message options.
        opts = getattr(Meta, 'options', descriptor_pb2.MessageOptions())

        # Create the underlying proto descriptor.
        desc = descriptor_pb2.DescriptorProto(
            name=name,
            field=[i.descriptor for i in fields],
            oneof_decl=[descriptor_pb2.OneofDescriptorProto(name=i)
                        for i in oneofs.keys()],
            options=opts,
        )

        # If any descriptors were nested under this one, they need to be
        # attached as nested types here.
        for child_path in copy.copy(file_info.nested).keys():
            if local_path == child_path[:len(local_path)]:
                desc.nested_type.add().MergeFrom(
                    file_info.nested.pop(child_path),
                )

        # Add the descriptor to the file if it is a top-level descriptor,
        # or to a "holding area" for nested messages otherwise.
        if len(local_path) == 1:
            file_info.descriptor.message_type.add().MergeFrom(desc)
        else:
            file_info.nested[tuple(full_name.split('.'))] = desc

        # Create the MessageInfo instance to be attached to this message.
        attrs['_meta'] = _MessageInfo(
            fields=fields,
            full_name=full_name,
            options=opts,
            package=package,
        )

        # Run the superclass constructor.
        cls = super().__new__(mcls, name, bases, attrs)

        # The info class and fields need a reference to the class just created.
        cls._meta.parent = cls
        for field in cls._meta.fields.values():
            field.parent = cls

        # Add this message to the _FileInfo instance; this allows us to
        # associate the descriptor with the message once the descriptor
        # is generated.
        file_info.messages[full_name] = cls

        # Generate the descriptor for the file if it is ready.
        if file_info.ready(new_class=cls):
            file_info.generate_file_pb()

        # Done; return the class.
        return cls

    @classmethod
    def __prepare__(mcls, name, bases, **kwargs):
        return collections.OrderedDict()

    @property
    def meta(cls):
        return cls._meta

    def pb(cls, obj=None):
        """Return the underlying protobuf Message class or instance.

        Args:
            obj: If provided, and an instance of ``cls``, return the
                underlying protobuf instance.
        """
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

    def deserialize(cls, payload: bytes) -> 'Message':
        """Given a serialized proto, deserialize it into a Message instance.

        Args:
            payload (bytes): The serialized proto.

        Returns:
            ~.Message: An instance of the message class against which this
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
        return any([k in self and getattr(self, k)
                    for k in self._meta.fields.keys()])

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
            more details.
        """
        pb_type = self._meta.fields[key].pb_type
        pb_value = getattr(self._pb, key)
        return marshal.to_python(pb_type, pb_value, absent=key not in self)

    def __ne__(self, other):
        """Return True if the messages are unequal, False otherwise."""
        return not self == other

    def __repr__(self):
        return repr(self._pb)

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


class _MessageInfo:
    """Metadata about a message.

    Args:
        fields (Tuple[~.fields.Field]): The fields declared on the message.
        package (str): The proto package.
        full_name (str): The full name of the message.
        file_info (~._FileInfo): The file descriptor and messages for the
            file containing this message.
        options (~.descriptor_pb2.MessageOptions): Any options that were
            set on the message.
    """
    def __init__(self, *, fields: List[Field], package: str, full_name: str,
                 options: descriptor_pb2.MessageOptions) -> None:
        self.package = package
        self.full_name = full_name
        self.options = options
        self.fields = collections.OrderedDict([
            (i.name, i) for i in fields
        ])
        self.fields_by_number = collections.OrderedDict([
            (i.number, i) for i in fields
        ])
        self._pb = None

    @property
    def pb(self) -> Type[message.Message]:
        """Return the protobuf message type for this descriptor.

        If a field on the message references another message which has not
        loaded, then this method returns None.
        """
        return self._pb


class _FileInfo(collections.namedtuple(
        '_FileInfo', ['descriptor', 'messages', 'name', 'nested'])):
    registry: Mapping[str, '_FileInfo'] = {}

    def generate_file_pb(self):
        """Generate the descriptors for all protos in the file.

        This method takes the file descriptor attached to the parent
        message and generates the immutable descriptors for all of the
        messages in the file descriptor. (This must be done in one fell
        swoop for immutability and to resolve proto cross-referencing.)

        This is run automatically when the last proto in the file is
        generated, as determined by the module's __all__ tuple.
        """
        pool = descriptor_pool.Default()

        # Salt the filename in the descriptor.
        # This allows re-use of the filename by other proto messages if
        # needed (e.g. if __all__ is not used).
        self.descriptor.name = '{prefix}_{salt}.proto'.format(
            prefix=self.descriptor.name[:-6],
            salt=str(uuid.uuid4())[0:8],
        )

        # Add the file descriptor.
        pool.Add(self.descriptor)

        # Adding the file descriptor to the pool created a descriptor for
        # each message; go back through our wrapper messages and associate
        # them with the internal protobuf version.
        for full_name, proto_plus_message in self.messages.items():
            # Get the descriptor from the pool, and create the protobuf
            # message based on it.
            descriptor = pool.FindMessageTypeByName(full_name)
            pb_message = reflection.GeneratedProtocolMessageType(
                descriptor.name,
                (message.Message,),
                {'DESCRIPTOR': descriptor, '__module__': None},
            )

            # Register the message with the marshal so it is wrapped
            # appropriately.
            proto_plus_message._meta._pb = pb_message
            marshal.register(
                pb_message,
                MessageMarshal(pb_message, proto_plus_message)
            )

            # Iterate over any fields on the message and, if their type
            # is a message still referenced as a string, resolve the reference.
            for field in proto_plus_message._meta.fields.values():
                if field.message and isinstance(field.message, str):
                    field.message = self.messages[field.message]

        # We no longer need to track this file's info; remove it from
        # the module's registry and from this object.
        self.registry.pop(self.name)

    def ready(self, new_class):
        """Return True if a file descriptor may added, False otherwise.

        This determine if all the messages that we plan to create have been
        created, as best as we are able.

        Since messages depend on one another, we create descriptor protos
        (which reference each other using strings) and wait until we have
        built everything that is going to be in the module, and then
        use the descriptor protos to instantiate the actual descriptors in
        one fell swoop.

        Args:
            new_class (~.MessageMeta): The new class currently undergoing
                creation.
        """
        # If there are any nested descriptors that have not been assigned to
        # the descriptors that should contain them, then we are not ready.
        if len(self.nested):
            return False

        # If there are any unresolved fields (fields with a composite message
        # declared as a string), ensure that the corresponding message is
        # declared.
        for field in self.unresolved_fields:
            if field.message not in self.messages:
                return False

        # If the module in which this class is defined provides an __all__,
        # do not generate the file descriptor until every member of __all__
        # has been populated.
        module = inspect.getmodule(new_class)
        manifest = set(getattr(module, '__all__', ())).difference(
            {new_class.__name__},
        )
        if not all([hasattr(module, i) for i in manifest]):
            return False

        # Okay, we are ready.
        return True

    @property
    def unresolved_fields(self):
        """Return fields with referencing message types as strings."""
        for proto_plus_message in self.messages.values():
            for field in proto_plus_message._meta.fields.values():
                if field.message and isinstance(field.message, str):
                    yield field


__all__ = (
    'Message',
)
