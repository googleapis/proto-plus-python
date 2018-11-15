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

from google.protobuf import descriptor_pb2
from google.protobuf import message as pb_message

from proto.primitives import ProtoType


class Field:
    """A representation of a type of field in protocol buffers."""

    def __init__(self, proto_type, *, number: int,
                 message=None, enum=None, oneof: str = None,
                 json_name: str = None):
        # This class is not intended to stand entirely alone;
        # data is augmented by the metaclass for Message.
        self.mcls_data = {}
        self.parent = None

        # Save the direct arguments.
        self.number = number
        self.proto_type = proto_type
        self.message = message
        self.enum = enum
        self.oneof = oneof
        self.json_name = json_name

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
            # Resolve the message type, if any, to a string.
            type_name = None
            if isinstance(self.message, str):
                type_name = self.message
                if not self.message.startswith(self.package):
                    type_name = '{package}.{name}'.format(
                        package=self.package,
                        name=self.message,
                    )
            elif self.message:
                if hasattr(self.message, 'DESCRIPTOR'):
                    type_name = self.message.DESCRIPTOR.full_name
                else:
                    type_name = self.message.meta.full_name
            elif self.enum:
                type_name = '{package}.{name}'.format(
                    package=self.package,
                    name=self.enum.__qualname__,
                )

            # Set the descriptor.
            self._descriptor = descriptor_pb2.FieldDescriptorProto(
                name=self.name,
                number=self.number,
                label=3 if self.repeated else 1,
                type=self.proto_type,
                type_name=type_name,
                json_name=self.json_name,
            )

        # Return the descriptor.
        return self._descriptor

    @property
    def name(self) -> str:
        """Return the name of the field."""
        return self.mcls_data['name']

    @property
    def pb_type(self):
        if self.message:
            if hasattr(self.message, '_meta'):
                return self.message.pb()
            return self.message
        return None

    @property
    def ready(self) -> bool:
        """Return True if this field is ready, False otherwise."""

        # All non-message fields are ready.
        # We do not have to check readiness on enums because we process
        # all enums ahead of all messages, thus guaranteeing that they must
        # be processed first.
        if self.proto_type != ProtoType.MESSAGE:
            return True

        # This field may rely on an instantiated stock protobuf message.
        # These are ready.
        if (isinstance(self.message, type) and
                issubclass(self.message, pb_message.Message)):
            return True

        # Corner case: Self-referential messages.
        # Explicitly declare these to be ready.
        if self.parent is self.message:
            return True

        # This field is ready if the underlying message is.
        # That means the message is a message object (not a string) and that
        # the referenced message is also ready.
        #
        # We use the `.pb` property rather than `.ready` here to avoid
        # infinite recursion corner cases (e.g. self-referencing messages).
        if isinstance(self.message, str):
            return False
        return bool(self.message._meta.pb)


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


__all__ = (
    'Field',
    'MapField',
    'RepeatedField',
)
