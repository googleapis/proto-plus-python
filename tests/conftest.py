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

import imp
from unittest import mock

from google.protobuf import descriptor_pool
from google.protobuf import symbol_database

import proto
from proto.marshal import types
from proto.message import _FileInfo


def pytest_runtest_setup(item):
    _FileInfo.registry.clear()

    # Replace the descriptor pool and symbol database to avoid tests
    # polluting one another.
    pool = descriptor_pool.DescriptorPool()
    sym_db = symbol_database.SymbolDatabase(pool=pool)
    item._mocks = (
        mock.patch.object(descriptor_pool, 'Default', return_value=pool),
        mock.patch.object(symbol_database, 'Default', return_value=sym_db),
    )
    [i.start() for i in item._mocks]

    # Re-import any pb2 modules that may have been imported by the
    # test's module. This ensures that the protos are inducted into the
    # new descriptor pool.
    reloaded = set()
    for name in dir(item.module):
        if name.endswith('_pb2') and not name.startswith('test_'):
            setattr(item.module, name, imp.reload(getattr(item.module, name)))
            reloaded.add(name)
    if 'wrappers_pb2' in reloaded:
        imp.reload(types.wrappers)
    if reloaded.intersection({'timestamp_pb2', 'duration_pb2'}):
        imp.reload(types.dates)
    proto.marshal.reset()


def pytest_runtest_teardown(item):
    [i.stop() for i in item._mocks]
