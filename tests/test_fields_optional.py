# Copyright 2020 Google LLC
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

import proto


def test_optional_init():
    class Squid(proto.Message):
        mass_kg = proto.Field(proto.INT32, number=1, optional=True)

    massive_squid = Squid(mass_kg=20)
    massless_squid = Squid()

    assert massive_squid.Hasmass_kg
    assert not massless_squid.Hasmass_kg
