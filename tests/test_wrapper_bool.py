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

from google.protobuf import wrappers_pb2

import proto


def test_bool_value_read():
    class Foo(proto.Message):
        bar = proto.Field(proto.ProtoType.MESSAGE,
            message_type=wrappers_pb2.BoolValue,
            number=1,
        )
    assert Foo(bar=True).bar is True
    assert Foo(bar=False).bar is False
    assert Foo().bar is None


def test_bool_value_distinction_from_bool():
    class Foo(proto.Message):
        bar = proto.Field(proto.ProtoType.MESSAGE,
            message_type=wrappers_pb2.BoolValue,
            number=1,
        )
        baz = proto.Field(proto.ProtoType.BOOL, number=2)
    assert Foo().bar is None
    assert Foo().baz is False


def test_bool_value_rmw():
    class Foo(proto.Message):
        bar = proto.Field(proto.ProtoType.MESSAGE,
            message_type=wrappers_pb2.BoolValue,
            number=1,
        )
        baz = proto.Field(proto.ProtoType.MESSAGE,
            message_type=wrappers_pb2.BoolValue,
            number=1,
        )
    foo = Foo(bar=False)
    assert foo.bar is False
    assert foo.baz is None
    foo.baz = True
    assert foo.baz is True
    assert Foo.pb(foo).baz.value is True
    foo.bar = None
    assert foo.bar is None
    assert not Foo.pb(foo).HasField('bar')


def test_bool_value_write_bool_value():
    class Foo(proto.Message):
        bar = proto.Field(proto.ProtoType.MESSAGE,
            message_type=wrappers_pb2.BoolValue,
            number=1,
        )
    foo = Foo(bar=True)
    foo.bar = wrappers_pb2.BoolValue()
    assert foo.bar is False


def test_bool_value_del():
    class Foo(proto.Message):
        bar = proto.Field(proto.ProtoType.MESSAGE,
            message_type=wrappers_pb2.BoolValue,
            number=1,
        )
    foo = Foo(bar=False)
    assert foo.bar is False
    del foo.bar
    assert foo.bar is None
