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


# def test_repeated_composite_init():
#     class Foo(proto.Message):
#         bar = proto.Field(proto.INT32, number=1)
#
#     class Baz(proto.Message):
#         foo = proto.Field(proto.MESSAGE,
#             message_type=Foo,
#             number=1,
#             repeated=True,
#         )
#
#     baz = Baz(foo=[Foo(bar=42)])
#     assert len(baz.foo) == 1
#     assert baz.foo[0].bar == 42
