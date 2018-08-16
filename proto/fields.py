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


class FieldType(type):
    """Metaclass for field types within protocol buffers."""





class Field:
    """A representation of a type of primitive field in protocol buffers."""

    def __init__(self, *, number: int, repeated: bool = False) -> None:
        self._number = number
        self._repeated = repeated



class Int32(Field):
    type_code = 5
    type_name = 'int32'


class String(Field):
    type_code = 9
    type_name = 'string'

    def to_python(self, value: str):
        return value

    def to_proto(self, value: str) -> str:
        return value

class Message(metaclass=FieldType):
    type_code = 11




"""
class FooMessage(Message):
    bar = fields.StringField(number=1)
    baz = BazMessage.Field(number=2)

    bar = Field(str, number=1)
    baz = Field(BazMessage, number=2, repeated=True)
    bacon = Oneof(bar, baz)
