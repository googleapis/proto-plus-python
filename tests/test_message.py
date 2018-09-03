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

import proto


def test_message_constructor_instance():
    class Foo(proto.Message):
        bar = proto.Field(proto.INT64, number=1)
    foo_original = Foo(bar=42)
    foo_copy = Foo(foo_original)
    assert foo_original.bar == foo_copy.bar == 42
    assert foo_original == foo_copy
    assert foo_original is not foo_copy
    assert isinstance(foo_original, Foo)
    assert isinstance(foo_copy, Foo)
    assert isinstance(Foo.pb(foo_copy), Foo.pb())


def test_message_constructor_underlying_pb2():
    class Foo(proto.Message):
        bar = proto.Field(proto.INT64, number=1)
    foo_pb2 = Foo.pb()(bar=42)
    foo = Foo(foo_pb2)
    assert foo.bar == foo_pb2.bar == 42
    assert foo == foo_pb2
