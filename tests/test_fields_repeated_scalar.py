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


def test_repeated_scalar_init():
    class Foo(proto.Message):
        bar = proto.Field(proto.INT32, repeated=True, number=1)

    foo = Foo(bar=[1, 1, 2, 3, 5, 8, 13])
    assert foo.bar == [1, 1, 2, 3, 5, 8, 13]


def test_repeated_scalar_append():
    class Foo(proto.Message):
        bar = proto.Field(proto.INT32, repeated=True, number=1)

    foo = Foo(bar=[1, 1, 2, 3, 5, 8, 13])
    foo.bar.append(21)
    foo.bar.append(34)
    assert foo.bar == [1, 1, 2, 3, 5, 8, 13, 21, 34]


def test_repeated_scalar_iadd():
    class Foo(proto.Message):
        bar = proto.Field(proto.INT32, repeated=True, number=1)

    foo = Foo(bar=[1, 1, 2, 3, 5, 8, 13])
    foo.bar += [21, 34]
    assert foo.bar == [1, 1, 2, 3, 5, 8, 13, 21, 34]


def test_repeated_scalar_overwrite():
    class Foo(proto.Message):
        bar = proto.Field(proto.INT32, repeated=True, number=1)

    foo = Foo(bar=[1, 1, 2, 3, 5, 8, 13])
    foo.bar = [1, 2, 4, 8, 16]
    assert foo.bar == [1, 2, 4, 8, 16]


def test_repeated_scalar_del():
    class Foo(proto.Message):
        bar = proto.Field(proto.INT32, repeated=True, number=1)

    foo = Foo(bar=[1, 1, 2, 3, 5, 8, 13])
    del foo.bar
    assert foo.bar == []
    assert not foo.bar
