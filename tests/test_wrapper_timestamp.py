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

from datetime import datetime
from datetime import timedelta
from datetime import timezone

from google.protobuf import duration_pb2
from google.protobuf import timestamp_pb2

import proto


def test_timestamp_read():
    class Foo(proto.Message):
        event_time = proto.Field(proto.ProtoType.MESSAGE,
            number=1,
            message_type=timestamp_pb2.Timestamp,
        )
    foo = Foo(event_time=timestamp_pb2.Timestamp(seconds=1335020400))
    assert isinstance(foo.event_time, datetime)
    assert foo.event_time.year == 2012
    assert foo.event_time.month == 4
    assert foo.event_time.day == 21
    assert foo.event_time.hour == 15
    assert foo.event_time.minute == 0
    assert foo.event_time.tzinfo == timezone.utc
