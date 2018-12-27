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

from google.protobuf import message
from google.protobuf import duration_pb2
from google.protobuf import timestamp_pb2
from google.protobuf import wrappers_pb2

from proto.marshal import containers
from proto.marshal.collections import MapComposite
from proto.marshal.collections import Repeated
from proto.marshal.collections import RepeatedComposite
from proto.marshal.types import dates
from proto.marshal.types import wrappers


class Rule(abc.ABC):
    """Abstract class definition for marshal rules."""

    @classmethod
    def __subclasshook__(cls, C):
        if hasattr(C, 'to_python') and hasattr(C, 'to_proto'):
            return True
        return NotImplemented


class MarshalRegistry:
    """A class to translate between protocol buffers and Python classes.

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

    The marshal is intended to be a singleton; this module instantiates
    and exports one marshal, which is imported throughout the rest of this
    library. This allows for an advanced case where user code registers
    additional types to be marshaled.
    """
    def __init__(self):
        self._registry = {}
        self._noop = NoopMarshal()
        self.reset()

    def register(self, proto_type: type, rule: Rule = None):
        """Register a rule against the given ``proto_type``.

        This function expects a ``proto_type`` (the descriptor class) and
        a ``rule``; an object with a ``to_python`` and ``to_proto`` method.
        Each method should return the appropriate Python or protocol buffer
        type, and be idempotent (e.g. accept either type as input).

        This function can also be used as a decorator::

            @marshal.register(timestamp_pb2.Timestamp)
            class TimestampMarshal:
                ...

        In this case, the class will be initialized for you with zero
        arguments.

        Args:
            proto_type (type): A protocol buffer message type.
            rule: A marshal object
        """
        # Sanity check: Do not register anything to a class that is not
        # a protocol buffer message.
        if not issubclass(proto_type, message.Message):
            raise TypeError('Only protocol buffer messages may be registered '
                            'to the marshal.')

        # If a rule was provided, register it and be done.
        if rule:
            # Ensure the rule implements Rule.
            if not isinstance(rule, Rule):
                raise TypeError('Marshal rule instances must implement '
                                '`to_proto` and `to_python` methods.')

            # Register the rule.
            self._registry[proto_type] = rule
            return

        # Create an inner function that will register an instance of the
        # marshal class to this object's registry, and return it.
        def register_rule_class(rule_class: type):
            # Ensure the rule class is a valid rule.
            if not issubclass(rule_class, Rule):
                raise TypeError('Marshal rule subclasses must implement '
                                '`to_proto` and `to_python` methods.')

            # Register the rule class.
            self._registry[proto_type] = rule_class()
            return rule_class
        return register_rule_class

    def reset(self):
        """Reset the registry to its initial state."""
        self._registry.clear()

        # Register date and time wrappers.
        self.register(timestamp_pb2.Timestamp, dates.TimestampMarshal())
        self.register(duration_pb2.Duration, dates.DurationMarshal())

        # Register nullable primitive wrappers.
        self.register(wrappers_pb2.BoolValue, wrappers.BoolValueMarshal())
        self.register(wrappers_pb2.BytesValue, wrappers.BytesValueMarshal())
        self.register(wrappers_pb2.DoubleValue, wrappers.DoubleValueMarshal())
        self.register(wrappers_pb2.FloatValue, wrappers.FloatValueMarshal())
        self.register(wrappers_pb2.Int32Value, wrappers.Int32ValueMarshal())
        self.register(wrappers_pb2.Int64Value, wrappers.Int64ValueMarshal())
        self.register(wrappers_pb2.StringValue, wrappers.StringValueMarshal())
        self.register(wrappers_pb2.UInt32Value, wrappers.UInt32ValueMarshal())
        self.register(wrappers_pb2.UInt64Value, wrappers.UInt64ValueMarshal())

    def to_python(self, proto_type, value, *, absent: bool = None):
        # Internal protobuf has its own special type for lists of values.
        # Return a view around it that implements MutableSequence.
        if isinstance(value, containers.repeated_composite_types):
            return RepeatedComposite(value, marshal=self)
        if isinstance(value, containers.repeated_scalar_types):
            return Repeated(value, marshal=self)

        # Same thing for maps of messages.
        if isinstance(value, containers.map_composite_types):
            return MapComposite(value, marshal=self)

        # Convert ordinary values.
        rule = self._registry.get(proto_type, self._noop)
        return rule.to_python(value, absent=absent)

    def to_proto(self, proto_type, value, *, strict: bool = False):
        # For our repeated and map view objects, simply return the
        # underlying pb.
        if isinstance(value, (Repeated, MapComposite)):
            return value.pb

        # Convert lists and tuples recursively.
        if isinstance(value, (list, tuple)):
            return type(value)([self.to_proto(proto_type, i) for i in value])

        # Convert dictionaries recursively when the proto type is a map.
        # This is slightly more complicated than converting a list or tuple
        # because we have to step through the magic that protocol buffers does.
        #
        # Essentially, a type of map<string, Foo> will show up here as
        # a FoosEntry with a `key` field, `value` field, and a `map_entry`
        # annotation. We need to do the conversion based on the `value`
        # field's type.
        if isinstance(value, dict) and (proto_type.DESCRIPTOR.has_options and
                proto_type.DESCRIPTOR.GetOptions().map_entry):
            return {k: self.to_proto(type(proto_type().value), v)
                    for k, v in value.items()}

        # Convert ordinary values.
        rule = self._registry.get(proto_type, self._noop)
        pb_value = rule.to_proto(value)

        # Sanity check: If we are in strict mode, did we get the value we want?
        if strict and not isinstance(pb_value, proto_type):
            raise TypeError(
                'Parameter must be instance of the same class; '
                'expected {expected}, got {got}'.format(
                    expected=proto_type.__name__,
                    got=pb_value.__class__.__name__,
                ),
            )

        # Return the final value.
        return pb_value


class NoopMarshal:
    """A catch-all marshal that does nothing."""

    def to_python(self, pb_value, *, absent: bool = None):
        return pb_value

    def to_proto(self, value):
        return value


marshal = MarshalRegistry()

__all__ = (
    'marshal',
)
