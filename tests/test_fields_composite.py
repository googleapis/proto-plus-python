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


def test_composite_init():
    class Foo(proto.Message):
        bar = proto.Field(proto.STRING, number=1)
        baz = proto.Field(proto.INT64, number=2)

    class Spam(proto.Message):
        foo = proto.Field(proto.MESSAGE, number=1, message_type=Foo)
        eggs = proto.Field(proto.BOOL, number=2)

    spam = Spam(foo=Foo(bar='str', baz=42))
    assert spam.foo.bar == 'str'
    assert spam.foo.baz == 42
    assert spam.eggs is False
