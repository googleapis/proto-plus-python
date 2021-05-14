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

import datetime
from enum import EnumMeta
from re import L
from proto.marshal.rules import wrappers
from proto.datetime_helpers import DatetimeWithNanoseconds
from proto.marshal.rules.dates import DurationRule
from typing import Any, Callable, Optional, Union

from google.protobuf import descriptor_pb2
from google.protobuf import duration_pb2
from google.protobuf import struct_pb2
from google.protobuf import timestamp_pb2
from google.protobuf import wrappers_pb2
from google.protobuf.internal.enum_type_wrapper import EnumTypeWrapper

import proto
from proto.primitives import ProtoType


class Field:
    """A representation of a type of field in protocol buffers."""

    # Fields are NOT repeated nor maps.
    # The RepeatedField overrides this values.
    repeated = False

    def __init__(
        self,
        proto_type,
        *,
        number: int,
        message=None,
        enum=None,
        oneof: str = None,
        json_name: str = None,
        optional: bool = False
    ):
        # This class is not intended to stand entirely alone;
        # data is augmented by the metaclass for Message.
        self.mcls_data = None
        self.parent = None

        # If the proto type sent is an object or a string, it is really
        # a message or enum.
        if not isinstance(proto_type, int):
            # Note: We only support the "shortcut syntax" for enums
            # when receiving the actual class.
            if isinstance(proto_type, (EnumMeta, EnumTypeWrapper)):
                enum = proto_type
                proto_type = ProtoType.ENUM
            else:
                message = proto_type
                proto_type = ProtoType.MESSAGE

        # Save the direct arguments.
        self.number = number
        self.proto_type = proto_type
        self.message = message
        self.enum = enum
        self.json_name = json_name
        self.optional = optional
        self.oneof = oneof

        # Once the descriptor is accessed the first time, cache it.
        # This is important because in rare cases the message or enum
        # types are written later.
        self._descriptor = None

    @property
    def descriptor(self):
        """Return the descriptor for the field."""
        if not self._descriptor:
            # Resolve the message type, if any, to a string.
            type_name = None
            if isinstance(self.message, str):
                if not self.message.startswith(self.package):
                    self.message = "{package}.{name}".format(
                        package=self.package, name=self.message,
                    )
                type_name = self.message
            elif self.message:
                type_name = (
                    self.message.DESCRIPTOR.full_name
                    if hasattr(self.message, "DESCRIPTOR")
                    else self.message._meta.full_name
                )
            elif isinstance(self.enum, str):
                if not self.enum.startswith(self.package):
                    self.enum = "{package}.{name}".format(
                        package=self.package, name=self.enum,
                    )
                type_name = self.enum
            elif self.enum:
                type_name = (
                    self.enum.DESCRIPTOR.full_name
                    if hasattr(self.enum, "DESCRIPTOR")
                    else self.enum._meta.full_name
                )

            # Set the descriptor.
            self._descriptor = descriptor_pb2.FieldDescriptorProto(
                name=self.name,
                number=self.number,
                label=3 if self.repeated else 1,
                type=self.proto_type,
                type_name=type_name,
                json_name=self.json_name,
                proto3_optional=self.optional,
            )

        # Return the descriptor.
        return self._descriptor

    @property
    def name(self) -> str:
        """Return the name of the field."""
        return self.mcls_data["name"]

    @property
    def package(self) -> str:
        """Return the package of the field."""
        return self.mcls_data["package"]

    @property
    def inner_pb_type(self):
        return None

    @property
    def pb_type(self):
        """Return the composite type of the field, or None for primitives."""
        # For enums, return the Python enum.
        if self.enum:
            return self.enum

        # For non-enum primitives, return None.
        if not self.message:
            return None

        # Return the internal protobuf message.
        if hasattr(self.message, "_meta"):
            return self.message.pb()
        return self.message

    @property
    def can_get_natively(self) -> bool:
        if self.proto_type == ProtoType.MESSAGE and self.message == struct_pb2.Value:
            return False
        return True

    def can_set_natively(self, val: Any) -> bool:
        if self.proto_type == ProtoType.MESSAGE and self.message == struct_pb2.Value:
            return False
        return True
        # return self.pb_type is None and not self.repeated

    def contribute_to_class(self, cls, name: str):
        """Attaches a descriptor to the top-level proto.Message class, so that attribute
        reads and writes can be specially handled in `_FieldDescriptor.__get__` and
        `FieldDescriptor.__set__`.

        Also contains hooks for write-time type-coersion to translate special cases between
        pure Pythonic objects and pb2-compatible structs or values.
        """
        set_coercion = None
        if self.proto_type == ProtoType.STRING:
            # Bytes are accepted for string values, but strings are not accepted for byte values.
            # This is an artifact of older Python2 implementations.
            set_coercion = self._bytes_to_str
        if self.pb_type == timestamp_pb2.Timestamp:
            set_coercion = self._timestamp_to_datetime
        if self.proto_type == ProtoType.MESSAGE and self.message == duration_pb2.Duration:
            set_coercion = self._duration_to_timedelta
        if self.proto_type == ProtoType.MESSAGE and self.message == wrappers_pb2.BoolValue:
            set_coercion = self._bool_value_to_bool
        if self.enum:
            set_coercion = self._literal_to_enum
        setattr(cls, name, _FieldDescriptor(name, cls=cls, set_coercion=set_coercion))

    @property
    def reverse_enum_map(self):
        """Helper that allows for constant-time lookup on self.enum, used to hydrate
        primitives that are supplied but which stand for their official enum types.

        This is used when a developer supplies the literal value for an enum type (often an int).
        """
        if not self.enum:
            return None
        if not getattr(self, '_reverse_enum_map', None):
            self._reverse_enum_map = {e.value: e for e in self.enum}
        return self._reverse_enum_map

    @property
    def reverse_enum_names_map(self):
        """Helper that allows for constant-time lookup on self.enum, used to hydrate
        primitives that are supplied but which stand for their official enum types.

        This is used when a developer supplies the string value for an enum type's name.
        """
        if not self.enum:
            return None
        if not getattr(self, '_reverse_enum_names_map', None):
            self._reverse_enum_names_map = {e.name: e for e in self.enum}
        return self._reverse_enum_names_map

    def _literal_to_enum(self, val: Any):
        if isinstance(val, self.enum):
            return val
        return (
            self.reverse_enum_map.get(val, None) or
            self.reverse_enum_names_map.get(val, None)
        )

    @staticmethod
    def _bytes_to_str(val: Union[bytes, str]) -> str:
        if type(val) == bytes:
            val = val.decode('utf-8')
        return val

    @staticmethod
    def _timestamp_to_datetime(val: Union[timestamp_pb2.Timestamp, datetime.datetime]) -> datetime.datetime:
        if type(val) == timestamp_pb2.Timestamp:
            val = DatetimeWithNanoseconds.from_timestamp_pb(val)
        return val

    @staticmethod
    def _duration_to_timedelta(val: Union[duration_pb2.Duration, datetime.timedelta]) -> datetime.datetime:
        if type(val) == duration_pb2.Duration:
            val = DurationRule().to_python(val)
        return val

    @staticmethod
    def _bool_value_to_bool(val: Union[wrappers_pb2.BoolValue, bool]) -> Optional[bool]:
        if val is None:
            return None
        if type(val) == wrappers_pb2.BoolValue:
            val = val.value
        return val


class RepeatedField(Field):
    """A representation of a repeated field in protocol buffers."""

    repeated = True


class MapField(Field):
    """A representation of a map field in protocol buffers."""

    def __init__(self, key_type, value_type, *, number: int, message=None, enum=None):
        super().__init__(value_type, number=number, message=message, enum=enum)
        self.map_key_type = key_type

    @property
    def inner_pb_type(self):
        return


class _FieldDescriptor:
    """Handler for proto.Field access on any proto.Message object.

    Wraps each proto.Field instance within a given proto.Message subclass's definition
    with getters and setters that allow for caching of values on the proto-plus object,
    deferment of syncing to the underlying pb2 object, and tracking of the current state.

    Special treatment is given to MapFields, nested Messages, and certain data types, as
    their various implementations within pb2 (which for our purposes is mostly a black box)
    sometimes mandate immediate syncing. This is usually because proto-plus objects are not
    long-lived, and thus information about which fields are stale would be lost if syncing
    was left for serialization time.
    """
    def __init__(self, name: str, *, cls, set_coercion: Optional[Callable] = None):
        # something like "id". required whenever reach back to the pb2 object.
        self.original_name = name
        # something like "_cached_id"
        self.instance_attr_name = f'_cached_fields__{name}'

        # simple types coercion for setting attributes (for example, bytes -> str)
        self._set_coercion = set_coercion or _FieldDescriptor._noop
        self.cls = cls

    @property
    def field(self):
        return self.cls._meta.fields[self.original_name]

    def _hydrate_dicts(self, value: Any):
        """Turns a dictionary assigned to a nested Message into a full instance of
        that Message type.
        """
        if not isinstance(value, dict):
            return value

        if self.field.proto_type == proto.MESSAGE:
            _pb = self.field.message._meta.pb(**value)
            value = self.field.message.wrap(_pb)

        return value

    def _clear_oneofs(self, instance):
        if not self.field.oneof:
            return

        for field_name, field in self.cls._meta.fields.items():
            # Don't clear this field
            if field_name == self.original_name:
                continue

            # Don't clear other fields with different oneof values, or with
            # no such values at all
            if field.oneof != self.field.oneof:
                continue

            delattr(instance, field_name)

    def __set__(self, instance, value):
        """Called whenever a value is assigned to a proto.Field attribute on an instantiated
        proto.Message object.

        Usage:

            class MyMessage(proto.Message):
                name = proto.Field(proto.STRING, number=1)

            my_message = MyMessage()
            my_message.name = "Frodo"

        In the above scenario, `__set__` is called with "Frodo" passed as `value` and `my_instance`
        passed as `instance`.
        """
        value = self._set_coercion(value)
        value = self._hydrate_dicts(value)

        # Warning: `always_commit` is hacky!
        # Some contexts, particularly instances created from MapFields, require immediate syncing.
        # It is impossible to deduce such a scenario purely from logic available to this function,
        # so instead we set a flag on instances when a MapField yields them, and then when those
        # instances receive attribute updates, immediately syncing those values to the underlying
        # pb2 instance is sufficient.
        always_commit: bool = getattr(instance, '_always_commit', False)
        if always_commit or not self.field.can_set_natively(value):
            pb_value = instance._meta.marshal.to_proto(self.field.pb_type, value)
            _pb = instance._meta.pb(**{self.original_name: pb_value})
            instance._pb.ClearField(self.original_name)
            instance._pb.MergeFrom(_pb)
        else:

            if value is None:
                self.__delete__(instance)
                instance._pb.MergeFrom(instance._meta._pb(**{self.original_name: None}))
                return

            instance._meta.marshal.validate_primitives(self.field, value)
            instance._mark_pb_stale(self.original_name)

        setattr(instance, self.instance_attr_name, value)
        self._clear_oneofs(instance)

    def __get__(self, instance: 'proto.Message', _):  # type: ignore
        """Called whenever a value is read from a proto.Field attribute on an instantiated
        proto.Message object.

        Usage:

            class MyMessage(proto.Message):
                name = proto.Field(proto.STRING, number=1)

            my_message = MyMessage(name="Frodo")
            print(my_message.name)

        In the above scenario, `__get__` is called with "my_message" passed as `instance`.
        """
        # If `instance` is None, then we are accessing this field directly
        # off the class itself instead of off an instance.
        if instance is None:
            return self.original_name

        value = getattr(instance, self.instance_attr_name, None)
        if self.field.can_get_natively and value is not None:
            return value
        else:
            # For the most part, only primitive values can be returned natively, meaning
            # this is either a Message itself, in which case, since we're dealing with the
            # underlying pb object, we need to sync all deferred fields.
            # This is functionally a no-op if no fields have been deferred.
            if hasattr(value, '_update_pb'):
                value._update_pb()

        pb_value = getattr(instance._pb, self.original_name, None)
        value = instance._meta.marshal.to_python(self.field.pb_type, pb_value, absent=self.original_name not in instance)

        setattr(instance, self.instance_attr_name, value)
        return value

    def __delete__(self, instance):
        if hasattr(instance, self.instance_attr_name):
            delattr(instance, self.instance_attr_name)
        instance._pb.ClearField(self.original_name)
        if self.original_name in getattr(instance, '_stale_fields', []):
            instance._stale_fields.remove(self.original_name)

    @staticmethod
    def _noop(val):
        return val


__all__ = (
    "Field",
    "MapField",
    "RepeatedField",
)
