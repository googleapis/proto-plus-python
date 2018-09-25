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

from unittest import mock

from google.protobuf import descriptor_pool
from google.protobuf import symbol_database

from proto import message


def pytest_runtest_setup(item):
    pool = descriptor_pool.DescriptorPool()
    sym_db = symbol_database.SymbolDatabase(pool=pool)
    message.registry.clear()
    item._mocks = (
        mock.patch.object(descriptor_pool, 'Default', return_value=pool),
        mock.patch.object(symbol_database, 'Default', return_value=sym_db),
    )
    [i.start() for i in item._mocks]


def pytest_runtest_teardown(item):
    [i.stop() for i in item._mocks]
