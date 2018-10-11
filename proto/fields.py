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

# This layer-of-indirection file exists to work around the restriction in
# protouf-proper that requires descriptors to be instantiated in files ending
# in `_pb2.py`.
# Consider this file (fields.py) to be the public interface.

from ._fields_pb2 import Field
from ._fields_pb2 import MapField
from ._fields_pb2 import RepeatedField

__all__ = (
    'Field',
    'MapField',
    'RepeatedField',
)
