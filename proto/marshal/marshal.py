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
            self._registry[proto_type] = rule
            return

        # Create an inner function that will register an instance of the
        # marshal class to this object's registry, and return it.
        def register_rule_class(rule_class: type):
            self._registry[proto_type] = rule_class()
            return rule_class
        return register_rule_class

    def to_python(self, proto_type, value, *, absent: bool = None):
        # Internal protobuf has its own special type for lists of composite
        # values. Return a view around it that behaves like a list.

        # Convert ordinary values.
        rule = self._registry.get(proto_type, self._noop)
        return rule.to_python(value, absent=absent)

    def to_proto(self, proto_type, value):
        # Convert lists and tuples recursively.
        if isinstance(value, (list, tuple)):
            return type(value)([self.to_proto(proto_type, i) for i in value])

        # Convert ordinary values.
        rule = self._registry.get(proto_type, self._noop)
        return rule.to_proto(value)


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
