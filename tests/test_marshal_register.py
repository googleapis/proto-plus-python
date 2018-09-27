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

import pytest

from google.protobuf import descriptor_pb2

import proto


def test_registration():
    FileDescriptor = descriptor_pb2.FileDescriptorProto
    try:
        @proto.marshal.register(FileDescriptor)
        class Marshal:
            def to_proto(self, value):
                return value

            def to_python(self, value, *, absent=None):
                return value
        assert isinstance(proto.marshal._registry[FileDescriptor], Marshal)
    finally:
        proto.marshal._registry.pop(FileDescriptor, None)


def test_invalid_marshal_class():
    with pytest.raises(TypeError):
        @proto.marshal.register(descriptor_pb2.FileDescriptorProto)
        class Marshal:
            pass


def test_invalid_marshal_rule():
    with pytest.raises(TypeError):
        proto.marshal.register(descriptor_pb2.DescriptorProto, rule=object())
