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

import abc
import enum

from google.protobuf import message
from google.protobuf import duration_pb2
from google.protobuf import timestamp_pb2
from google.protobuf import struct_pb2
from google.protobuf import wrappers_pb2

import proto
from proto.marshal import compat
from proto.marshal.collections import MapComposite
from proto.marshal.collections import Repeated
from proto.marshal.collections import RepeatedComposite
from proto.marshal.rules import dates
from proto.marshal.rules import struct
from proto.marshal.rules import wrappers


max_uint_32 = 1<<32 - 1
max_int_32 = 1<<31 - 1
min_int_32 = (max_int_32 * -1) + 1

class Rule(abc.ABC):
    """Abstract class definition for marshal rules."""

    @classmethod
    def __subclasshook__(cls, C):
        if hasattr(C, "to_python") and hasattr(C, "to_proto"):
            return True
        return NotImplemented


class BaseMarshal:
    """The base class to translate between protobuf and Python classes.

    Protocol buffers defines many common types (e.g. Timestamp, Duration)
    which also exist in the Python standard library. The marshal essentially
    translates between these: it keeps a registry of common protocol buffers
    and their Python representations, and translates back and forth.

    The protocol buffer class is always the "key" in this relationship; when
    presenting a message, the declared field types are used to determine
    whether a value should be transformed into another class. Similarly,
    when accepting a Python value (when setting a field, for example),
    the declared field type is still used. This means that, if appropriate,
    multiple protocol buffer types may use the same Python type.

    The primary implementation of this is :class:`Marshal`, which should
    usually be used instead of this class directly.
    """

    def __init__(self):
        self._rules = {}
        self._noop = NoopRule()
        self.reset()

    def register(self, proto_type: type, rule: Rule = None):
        """Register a rule against the given ``proto_type``.

        This function expects a ``proto_type`` (the descriptor class) and
        a ``rule``; an object with a ``to_python`` and ``to_proto`` method.
        Each method should return the appropriate Python or protocol buffer
        type, and be idempotent (e.g. accept either type as input).

        This function can also be used as a decorator::

            @marshal.register(timestamp_pb2.Timestamp)
            class TimestampRule:
                ...

        In this case, the class will be initialized for you with zero
        arguments.

        Args:
            proto_type (type): A protocol buffer message type.
            rule: A marshal object
        """
        # Sanity check: Do not register anything to a class that is not
        # a protocol buffer message.
        if not issubclass(proto_type, (message.Message, enum.IntEnum)):
            raise TypeError(
                "Only enums and protocol buffer messages may be "
                "registered to the marshal."
            )

        # If a rule was provided, register it and be done.
        if rule:
            # Ensure the rule implements Rule.
            if not isinstance(rule, Rule):
                raise TypeError(
                    "Marshal rule instances must implement "
                    "`to_proto` and `to_python` methods."
                )

            # Register the rule.
            self._rules[proto_type] = rule
            return

        # Create an inner function that will register an instance of the
        # marshal class to this object's registry, and return it.
        def register_rule_class(rule_class: type):
            # Ensure the rule class is a valid rule.
            if not issubclass(rule_class, Rule):
                raise TypeError(
                    "Marshal rule subclasses must implement "
                    "`to_proto` and `to_python` methods."
                )

            # Register the rule class.
            self._rules[proto_type] = rule_class()
            return rule_class

        return register_rule_class

    @staticmethod
    def _throw_type_error(primitive):
        raise TypeError(f"Unacceptable value of type {type(primitive)}")

    @staticmethod
    def _throw_value_error(proto_type, primitive):
        raise ValueError(f"Unacceptable value {type(primitive)} for type {proto_type}")

    def validate_primitives(self, field, primitive):
        """Replicates validation logic when assigning values to proto.Field attributes
        on instantiated proto.Message objects. This is required to recreate the immediacy
        of ValueError and TypeError checks that the pb2 layer made, but which are now
        deferred because syncing to the pb2 layer itself is often entirely deferred.
        """
        proto_type = field.proto_type
        if field.repeated:
            if primitive and not isinstance(primitive, (list, tuple, Repeated, RepeatedComposite,)):
                self._throw_type_error(primitive)

            # Typically, checking a sequence's length after checking its Truthiness is
            # unnecessary, but this will make us safe from any unexpected behavior from
            # `Repeated` or `RepeatedComposite`.
            if primitive and len(primitive) > 0:
                primitive = primitive[0]

        _type = type(primitive)
        if proto_type == proto.BOOL and _type != bool:
            self._throw_type_error(primitive)
        elif proto_type == proto.STRING and _type not in (str, bytes,):
            self._throw_type_error(primitive)
        elif proto_type == proto.DOUBLE and _type != float:
            self._throw_type_error(primitive)
        elif proto_type == proto.FLOAT and _type != float:
            self._throw_type_error(primitive)
        elif proto_type == proto.INT64 and _type != int:
            self._throw_type_error(primitive)
        elif proto_type == proto.UINT64:
            if  _type != int:
                self._throw_type_error(primitive)
            if primitive < 0:
                self._throw_value_error(proto_type, primitive)
        elif proto_type == proto.INT32:
            if _type != int:
                self._throw_type_error(primitive)
            if primitive < min_int_32 or primitive > max_int_32:
                self._throw_value_error(proto_type, primitive)
        elif proto_type == proto.FIXED64 and _type != int:
            self._throw_type_error(primitive)
        elif proto_type == proto.FIXED32 and _type != int:
            self._throw_type_error(primitive)
        elif proto_type == proto.MESSAGE:
            # Do nothing - this is not a primitive
            pass
        elif proto_type == proto.BYTES and _type != bytes:
            self._throw_type_error(primitive)
        elif proto_type == proto.UINT32:
            if _type != int:
                self._throw_type_error(primitive)
            if primitive < 0 or primitive > max_int_32:
                self._throw_value_error(proto_type, primitive)
        elif proto_type == proto.ENUM:
            # Do nothing - this is not a primitive
            pass
        elif proto_type == proto.SFIXED32:
            if _type != int:
                self._throw_type_error(primitive)
            if primitive < min_int_32 or primitive > max_int_32:
                self._throw_value_error(proto_type, primitive)
        elif proto_type == proto.SFIXED64 and _type != int:
            self._throw_type_error(primitive)
        elif proto_type == proto.SINT32:
            if _type != int:
                self._throw_type_error(primitive)
            if primitive < min_int_32 or primitive > max_int_32:
                self._throw_value_error(proto_type, primitive)
        elif proto_type == proto.SINT64 and _type != int:
            self._throw_type_error(primitive)

    def reset(self):
        """Reset the registry to its initial state."""
        self._rules.clear()

        # Register date and time wrappers.
        self.register(timestamp_pb2.Timestamp, dates.TimestampRule())
        self.register(duration_pb2.Duration, dates.DurationRule())

        # Register nullable primitive wrappers.
        self.register(wrappers_pb2.BoolValue, wrappers.BoolValueRule())
        self.register(wrappers_pb2.BytesValue, wrappers.BytesValueRule())
        self.register(wrappers_pb2.DoubleValue, wrappers.DoubleValueRule())
        self.register(wrappers_pb2.FloatValue, wrappers.FloatValueRule())
        self.register(wrappers_pb2.Int32Value, wrappers.Int32ValueRule())
        self.register(wrappers_pb2.Int64Value, wrappers.Int64ValueRule())
        self.register(wrappers_pb2.StringValue, wrappers.StringValueRule())
        self.register(wrappers_pb2.UInt32Value, wrappers.UInt32ValueRule())
        self.register(wrappers_pb2.UInt64Value, wrappers.UInt64ValueRule())

        # Register the google.protobuf.Struct wrappers.
        #
        # These are aware of the marshal that created them, because they
        # create RepeatedComposite and MapComposite instances directly and
        # need to pass the marshal to them.
        self.register(struct_pb2.Value, struct.ValueRule(marshal=self))
        self.register(struct_pb2.ListValue, struct.ListValueRule(marshal=self))
        self.register(struct_pb2.Struct, struct.StructRule(marshal=self))

    def to_python(self, proto_type, value, *, absent: bool = None):
        # Internal protobuf has its own special type for lists of values.
        # Return a view around it that implements MutableSequence.
        value_type = type(value)  # Minor performance boost over isinstance
        if value_type in compat.repeated_composite_types:
            return RepeatedComposite(value, marshal=self)
        if value_type in compat.repeated_scalar_types:
            if isinstance(proto_type, type):
                return RepeatedComposite(value, marshal=self, proto_type=proto_type)
            else:
                return Repeated(value, marshal=self)

        # Same thing for maps of messages.
        if value_type in compat.map_composite_types:
            return MapComposite(value, marshal=self)

        # Convert ordinary values.
        rule = self._rules.get(proto_type, self._noop)
        return rule.to_python(value, absent=absent)

    def to_proto(self, proto_type, value, *, strict: bool = False):
        # The protos in google/protobuf/struct.proto are exceptional cases,
        # because they can and should represent themselves as lists and dicts.
        # These cases are handled in their rule classes.
        if proto_type not in (
            struct_pb2.Value,
            struct_pb2.ListValue,
            struct_pb2.Struct,
        ):
            # For our repeated and map view objects, simply return the
            # underlying pb.
            if isinstance(value, (Repeated, MapComposite)):
                return value.pb

            # Convert lists and tuples recursively.
            if isinstance(value, (list, tuple)):
                return type(value)(self.to_proto(proto_type, i) for i in value)

        # Convert dictionaries recursively when the proto type is a map.
        # This is slightly more complicated than converting a list or tuple
        # because we have to step through the magic that protocol buffers does.
        #
        # Essentially, a type of map<string, Foo> will show up here as
        # a FoosEntry with a `key` field, `value` field, and a `map_entry`
        # annotation. We need to do the conversion based on the `value`
        # field's type.
        if isinstance(value, dict) and (
            proto_type.DESCRIPTOR.has_options
            and proto_type.DESCRIPTOR.GetOptions().map_entry
        ):
            recursive_type = type(proto_type().value)
            return {k: self.to_proto(recursive_type, v) for k, v in value.items()}

        # Convert ordinary values.
        rule = self._rules.get(proto_type, self._noop)
        pb_value = rule.to_proto(value)

        # Sanity check: If we are in strict mode, did we get the value we want?
        if strict and not isinstance(pb_value, proto_type):
            raise TypeError(
                "Parameter must be instance of the same class; "
                "expected {expected}, got {got}".format(
                    expected=proto_type.__name__, got=pb_value.__class__.__name__,
                ),
            )

        # Return the final value.
        return pb_value


class Marshal(BaseMarshal):
    """The translator between protocol buffer and Python instances.

    The bulk of the implementation is in :class:`BaseMarshal`. This class
    adds identity tracking: multiple instantiations of :class:`Marshal` with
    the same name will provide the same instance.
    """

    _instances = {}

    def __new__(cls, *, name: str):
        """Create a marshal instance.

        Args:
            name (str): The name of the marshal. Instantiating multiple
                marshals with the same ``name`` argument will provide the
                same marshal each time.
        """
        klass = cls._instances.get(name)
        if klass is None:
            klass = cls._instances[name] = super().__new__(cls)

        return klass

    def __init__(self, *, name: str):
        """Instantiate a marshal.

        Args:
            name (str): The name of the marshal. Instantiating multiple
                marshals with the same ``name`` argument will provide the
                same marshal each time.
        """
        self._name = name
        if not hasattr(self, "_rules"):
            super().__init__()


class NoopRule:
    """A catch-all rule that does nothing."""

    def to_python(self, pb_value, *, absent: bool = None):
        return pb_value

    def to_proto(self, value):
        return value


__all__ = ("Marshal",)
