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

from typing import Callable

from google.protobuf import message


class Marshal:
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

    def register(self, proto_type: type):
        """Return a function that will register a rule against the given type.

        This function is intended to be used as a decorator:

            @marshal.register(timestamp_pb2.Timestamp)
            class TimestampMarshal:
                ...

        The individual marshal classes are expected to have a ``to_python``
        and ``to_proto`` method. Each should return the appropriate Python
        or protocol buffer type, and be idempotent (e.g. accept either type
        as input).

        Args:
            proto_type (type): A protocol buffer message type.
        """
        # Sanity check: Do not register anything to a class that is not
        # a protocol buffer message.
        if not issubclass(proto_type, message.Message):
            raise TypeError('Only protocol buffer messages may be registered '
                            'to the marshal.')

        # Create an inner function that will register an instance of the
        # marshal class to this object's registry, and return it.
        def register_rule_class(rule_class: type):
            self._registry[proto_type] = rule_class()
            return rule_class
        return register_rule_class

    def get_


class NoopMarshal:
    """A catch-all marshal that does nothing."""

    def to_python(self, value):
        return value

    def to_proto(self, value):
        return value
