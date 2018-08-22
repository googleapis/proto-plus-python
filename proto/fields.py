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

import enum

from google.protobuf import descriptor


class ProtoType(enum.IntEnum):
    """The set of basic types in protocol buffers."""
    # These values come from google/protobuf/descriptor.proto
    DOUBLE = 1
    FLOAT = 2
    INT64 = 3
    UINT64 = 4
    INT32 = 5
    FIXED64 = 6
    FIXED32 = 7
    BOOL = 8
    STRING = 9
    MESSAGE = 11
    BYTES = 12
    UINT32 = 13
    ENUM = 14
    SFIXED32 = 15
    SFIXED64 = 16
    SINT32 = 17
    SINT64 = 18



class Field:
    """A representation of a type of field in protocol buffers."""

    def __init__(self, proto_type, *, number: int, repeated: bool = False,
                 message_type=None, enum_type=None):
        # This class is not intended to stand entirely alone;
        # data is augmented by the metaclass for Message.
        self.mcls_data = {}

        # Save the direct arguments.
        self._proto_type = proto_type
        self._number = number
        self._repeated = repeated
        self._message = message_type
        self._enum = enum_type

        # Once the descriptor is accessed the first time, cache it.
        # This is important because in rare cases the message or enum
        # types are written later.
        self._descriptor = None

    @property
    def descriptor(self):
        """Return the descriptor for the field."""
        if not self._descriptor:
            self._descriptor = descriptor.FieldDescriptor(
                name=self.mcls_data['name'],
                full_name=self.mcls_data['full_name'],
                index=self.mcls_data['index'],
                number=self._number,
                label=3 if self._repeated else 1,
                type=self._proto_type,
                cpp_type=descriptor.FieldDescriptor.ProtoTypeToCppProtoType(
                    self._proto_type,
                ),
                message_type=self._message._meta.pb,
                enum_type=self._enum,
                containing_type=None,
                is_extension=False,
                extension_scope=None,
            )
        return self._descriptor
