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
from typing import Optional

from google.type import decimal_pb2


class DecimalRule:
    """A marshal between ``google.type.Decimal`` and Python's
    ``decimal.Decimal``.
    """
    def to_python(
        self, value, *, absent: bool = None
    ) -> Optional[decimal.Decimal]:
        if isinstance(value, decimal_pb2.Decimal):
            if absent:
                return None
            return decimal.Decimal(value.value)
        return value

    def to_proto(self, value) -> decimal_pb2.Decimal:
        if isinstance(value, (decimal.Decimal, int, float)):
            return decimal_pb2.Decimal(value=str(value).lower())
        if isinstance(value, decimal_pb2.Decimal):
            return value
        raise TypeError('Invalid type received for decimal value.')
