# Copyright 2021 Google LLC
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

import decimal

from google.type import decimal_pb2

import proto
from proto.marshal.marshal import BaseMarshal


def test_decimal_read():
    class Foo(proto.Message):
        event_price = proto.Field(
            proto.MESSAGE, number=1, message=decimal_pb2.Decimal,
        )

    for v in ['2', '2.', '2.5', '2.5e10', '2.5e-10', '-2.5']:
        foo = Foo(event_price=decimal_pb2.Decimal(value=v))
        assert isinstance(foo.event_price, decimal.Decimal)
        assert foo.event_price == decimal.Decimal(v)
        assert foo.event_price == float(v)
        if v in ('2', '2.'):
            assert foo.event_price == int(v)


def test_decimal_read_float():
    class Foo(proto.Message):
        event_price = proto.Field(
            proto.MESSAGE, number=1, message=decimal_pb2.Decimal,
        )

    for v in ['2', '2.', '2.5', '2.5e10', '2.5e-10', '-2.5']:
        foo = Foo(event_price=float(value=v))
        assert isinstance(foo.event_price, decimal.Decimal)
        assert foo.event_price == decimal.Decimal(v)
        assert foo.event_price == float(v)
        if v in ('2', '2.'):
            assert foo.event_price == int(v)


def test_decimal_write_init():
    class Foo(proto.Message):
        event_price = proto.Field(
            proto.MESSAGE, number=1, message=decimal_pb2.Decimal,
        )

    for v in ['2', '2.', '2.5', '2.5e10', '2.5e-10', '-2.5']:
        foo = Foo(event_price=decimal.Decimal(v))
        assert isinstance(foo.event_price, decimal.Decimal)
        assert isinstance(Foo.pb(foo).event_price, decimal_pb2.Decimal)
        assert foo.event_price == decimal.Decimal(v)
        assert foo.event_price == float(v)
        assert Foo.pb(foo).event_price.value == v


def test_decimal_write():
    class Foo(proto.Message):
        event_price = proto.Field(
            proto.MESSAGE, number=1, message=decimal_pb2.Decimal,
        )

    for v in ['2', '2.', '2.5', '2.5e10', '2.5e-10', '-2.5']:
        foo = Foo()
        foo.event_price = decimal.Decimal(v)
        assert isinstance(foo.event_price, decimal.Decimal)
        assert isinstance(Foo.pb(foo).event_price, decimal_pb2.Decimal)
        assert foo.event_price == decimal.Decimal(v)
        assert foo.event_price == float(v)
        assert Foo.pb(foo).event_price.value == v


def test_decimal_write_pb2():
    class Foo(proto.Message):
        event_price = proto.Field(
            proto.MESSAGE, number=1, message=decimal_pb2.Decimal,
        )

    for v in ['2', '2.', '2.5', '2.5e10', '2.5e-10', '-2.5']:
        foo = Foo()
        foo.event_price = decimal_pb2.Decimal(value=v)
        assert isinstance(foo.event_price, decimal.Decimal)
        assert isinstance(Foo.pb(foo).event_price, decimal_pb2.Decimal)
        assert foo.event_price == decimal.Decimal(v)
        assert foo.event_price == float(v)
        assert Foo.pb(foo).event_price.value == v


def test_decimal_absence():
    class Foo(proto.Message):
        event_price = proto.Field(
            proto.MESSAGE, number=1, message=decimal_pb2.Decimal,
        )

    foo = Foo()
    assert foo.event_price is None


def test_decimal_del():
    class Foo(proto.Message):
        event_price = proto.Field(
            proto.MESSAGE, number=1, message=decimal_pb2.Decimal,
        )

    foo = Foo(event_price=2.5)
    del foo.event_price
    assert foo.event_price is None


def test_decimal_to_python_idempotent():
    # This path can never run in the current configuration because proto
    # values are the only thing ever saved, and `to_python` is a read method.
    #
    # However, we test idempotency for consistency with `to_proto` and
    # general resiliency.
    marshal = BaseMarshal()
    for v in ['2', '2.', '2.5', '2.5e10', '2.5e-10', '-2.5']:
        py_value = decimal.Decimal(v)
        assert marshal.to_python(decimal_pb2.Decimal, py_value) is py_value
