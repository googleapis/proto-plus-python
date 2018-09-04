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

from google.protobuf import descriptor

from proto.primitives import get_default_value


class Field:
    """A representation of a type of field in protocol buffers."""

    def __init__(self, proto_type, *, number: int,
                 message=None, enum=None):
        # This class is not intended to stand entirely alone;
        # data is augmented by the metaclass for Message.
        self.mcls_data = {}

        # Save the direct arguments.
        self.number = number
        self.proto_type = proto_type
        self.message = message
        self.enum = enum

        # Fields are neither repeated nor maps.
        # The RepeatedField and MapField subclasses override these values
        # in their initializers.
        self.repeated = False

        # Once the descriptor is accessed the first time, cache it.
        # This is important because in rare cases the message or enum
        # types are written later.
        self._descriptor = None

    @property
    def descriptor(self):
        """Return the descriptor for the field."""
        if not self._descriptor:
            # Determine the default value.
            default_value = get_default_value(self.proto_type)
            if self.repeated:
                default_value = []

            # Resolve the message type, if any, to its underlying
            # protobuf descriptor.
            message_type = self.message
            if self.message and hasattr(self.message, '_meta'):
                message_type = self.message._meta.pb

            # Set the descriptor.
            self._descriptor = descriptor.FieldDescriptor(
                name=self.mcls_data['name'],
                full_name=self.mcls_data['full_name'],
                index=self.mcls_data['index'],
                number=self.number,
                label=3 if self.repeated else 1,
                type=self.proto_type,
                cpp_type=descriptor.FieldDescriptor.ProtoTypeToCppProtoType(
                    self.proto_type,
                ),
                default_value=default_value,
                message_type=message_type.DESCRIPTOR if message_type else None,
                enum_type=self.enum,
                containing_type=None,
                is_extension=False,
                extension_scope=None,
            )
        return self._descriptor

    @property
    def name(self):
        """Return the name of the field."""
        return self.mcls_data['name']

    @property
    def pb_type(self):
        if self.message:
            if hasattr(self.message, '_meta'):
                return self.message.pb()
            return self.message
        return None


class RepeatedField(Field):
    """A representation of a repeated field in protocol buffers."""

    def __init__(self, proto_type, *, number: int,
                 message=None, enum=None):
        super().__init__(proto_type, number=number, message=message, enum=enum)
        self.repeated = True


class MapField(Field):
    """A representation of a map field in protocol buffers."""

    def __init__(self, key_type, value_type, *, number: int,
                 message=None, enum=None):
        super().__init__(value_type, number=number, message=message, enum=enum)
        self.map_key_type = key_type
