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

import datetime

from google.protobuf import duration_pb2
from google.protobuf import timestamp_pb2

from .registry import marshal


@marshal.register(timestamp_pb2.Timestamp)
class TimestampMarshal:
    """A marshal between Python datetimes and protobuf timestamps.

    Note: Python datetimes are less precise than protobuf datetimes
    (microsecond vs. nanosecond level precision). If nanosecond-level
    precision matters, it is recommended to interact with the internal
    proto directly.
    """
    def to_python(self, value, *, absent: bool = None) -> datetime.datetime:
        if isinstance(value, timestamp_pb2.Timestamp):
            if absent:
                return None
            return datetime.fromtimestamp(
                value.seconds + value.nanos / 1e9,
                tz=datetime.timezone.utc,
            )
        return value

    def to_proto(self, value) -> timestamp_pb2.Timestamp:
        if isinstance(value, datetime.datetime):
            return timestamp_pb2.Timestamp(
                seconds=int(value.strftime('%s')),
                nanos=int(value.strftime('%f')) * 1000,
            )
        return value


@marshal.register(duration_pb2.Duration)
class DurationMarshal:
    """A marshal between Python timedeltas and protobuf durations.

    Note: Python timedeltas are less precise than protobuf durations
    (microsecond vs. nanosecond level precision). If nanosecond-level
    precision matters, it is recommended to interact with the internal
    proto directly.
    """
    def to_python(self, value, *, absent: bool = None) -> datetime.timedelta:
        if isinstance(value, duration_pb2.Duration):
            return datetime.timedelta(
                days=value.seconds // 86400,
                seconds=value.seconds % 86400,
                microseconds=value.nanos // 1000,
            )
        return value

    def to_proto(self, value) -> duration_pb2.Duration:
        if isinstance(value, datetime.timedelta):
            return duration_pb2.Duration(
                seconds=value.days * 86400 + value.seconds,
                nanos=value.microseconds * 1000,
            )
