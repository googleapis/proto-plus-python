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
import pytest

from google.type import decimal_pb2

import proto
from proto.marshal.marshal import BaseMarshal


def test_decimal_read(value_func=lambda s: decimal_pb2.Decimal(value=s)):
    class Foo(proto.Message):
        event_price = proto.Field(proto.MESSAGE, number=1, message=decimal_pb2.Decimal,)

    for v in ["2", "2.", "2.5", "2.5e10", "2.5e-10", "-2.5", "NaN", "inf"]:
        foo = Foo(event_price=value_func(v))
        assert isinstance(foo.event_price, decimal.Decimal)

        if v == "NaN":
            # Because IEEE 754
            assert foo.event_price.is_nan()
        else:
            assert foo.event_price == decimal.Decimal(v)
            if v != "2.5e-10":
                # Gets lost in the conversion.
                assert foo.event_price == float(v)
            if v == "2":
                # Can't compare 2. because it can't easily be converted to an int.
                assert foo.event_price == int(v)


def test_decimal_read_float():
    test_decimal_read(value_func=float)


def test_decimal_read_string():
    test_decimal_read(value_func=str)


def test_decimal_read_int():
    class Foo(proto.Message):
        event_price = proto.Field(proto.MESSAGE, number=1, message=decimal_pb2.Decimal,)

    for v in ["2", "-2", "+2"]:
        foo = Foo(event_price=int(v))
        assert isinstance(foo.event_price, decimal.Decimal)
        assert foo.event_price == decimal.Decimal(v)
        assert foo.event_price == int(v)


def test_decimal_write_init():
    class Foo(proto.Message):
        event_price = proto.Field(proto.MESSAGE, number=1, message=decimal_pb2.Decimal,)

    for v in ["2", "2.", "2.5", "2.5e10", "2.5e-10", "-2.5"]:
        foo = Foo(event_price=decimal.Decimal(v))
        assert isinstance(foo.event_price, decimal.Decimal)
        assert isinstance(Foo.pb(foo).event_price, decimal_pb2.Decimal)
        assert foo.event_price == decimal.Decimal(v)
        if v not in {"2.5", "2.5e-10"}:
            # Does not represent as a float well.
            assert foo.event_price == float(v)
        if v not in {"2.", "2.5e10"}:
            # The trailing decimal gets rounded off.
            assert Foo.pb(foo).event_price.value == v


def test_decimal_write(value_func=lambda s: decimal_pb2.Decimal(value=s)):
    class Foo(proto.Message):
        event_price = proto.Field(proto.MESSAGE, number=1, message=decimal_pb2.Decimal,)

    for v in ["2", "2.", "2.5", "2.5e10", "2.5e-10", "-2.5", "infinity", "nan"]:
        foo = Foo()
        foo.event_price = value_func(v)
        assert isinstance(foo.event_price, decimal.Decimal)
        assert isinstance(Foo.pb(foo).event_price, decimal_pb2.Decimal)
        if v not in {"2.", "2.5e10"}:
            # Conversion strips the dot and adds a + sign, respectively.
            assert Foo.pb(foo).event_price.value == v
        if v == "nan":
            # Because IEEE754
            assert foo.event_price.is_nan()
        else:
            assert foo.event_price == decimal.Decimal(v)
            if v != "2.5e-10":
                # Float conversion imprecision.
                assert foo.event_price == float(v)


def test_decimal_write_py_decimal():
    test_decimal_write(value_func=decimal.Decimal)


def test_decimal_absence():
    class Foo(proto.Message):
        event_price = proto.Field(proto.MESSAGE, number=1, message=decimal_pb2.Decimal,)

    foo = Foo()
    assert foo.event_price is None


def test_decimal_del():
    class Foo(proto.Message):
        event_price = proto.Field(proto.MESSAGE, number=1, message=decimal_pb2.Decimal,)

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
    for v in ["2", "2.", "2.5", "2.5e10", "2.5e-10", "-2.5"]:
        py_value = decimal.Decimal(v)
        assert marshal.to_python(decimal_pb2.Decimal, py_value) is py_value


def test_decimal_to_proto_error():
    # Catch type checking
    marshal = BaseMarshal()
    with pytest.raises(TypeError):
        marshal.to_proto(decimal_pb2.Decimal, None)
