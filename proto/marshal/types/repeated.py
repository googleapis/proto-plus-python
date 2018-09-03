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

import sys

from google.protobuf.internal import containers

from ..marshal import marshal


class RepeatedComposite:
    """A view around a mutable sequence in protocol buffers.

    This implements the full Python list interface, but all methods modify
    the underlying field container directly.
    """
    def __init__(self, sequence: containers.RepeatedCompositeFieldContainer):
        self._pb = sequence

    @property
    def pb(self):
        return self._pb

    @property
    def _pb_type(self):
        """Return the protocol buffer type for this sequence."""
        return self.pb._message_descriptor._concrete_class

    def append(self, value):
        """Append the value to the end of the sequence."""
        self.pb.add(marshal.to_proto(self._pb_type, value))

    def count(self, value):
        """Return the number of times ``value`` appears in the sequence."""
        return len([i for i in self if i == value])

    def extend(self, iterable):
        """Extend the sequence by appending elements from the iterable."""
        self.pb.extend([marshal.to_proto(self._pb_type, i) for i in iterable])

    def index(self, value, start: int = 0, stop: int = sys.maxsize):
        """Return the first index of ``value``.

        If ``value`` is not present, raise ValueError.
        """
        pb_value = marshal.to_proto(self._pb_type, value)
        return self.pb._values.index(pb_value, start=start, stop=stop)

    def insert(self, index: int, value):
        """Insert ``value`` in the sequence before ``index``."""
        pb_value = marshal.to_proto(self._pb_type, value)
        if not isinstance(pb_value, self._pb_type):
            raise TypeError(
                'Parameter to `insert` must be instance of the same class; '
                'expected {expected}, got {got}'.format(
                    expected=self._pb_type.__name__,
                    got=value.__class__.__name__,
                ),
            )
        self.pb._values.insert(index, value)
