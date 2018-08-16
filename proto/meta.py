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

import collections
import copy
from typing import List

from google.protobuf import descriptor


class MessageMeta(type):
    """A metaclass for building and registering Message subclasses."""

    def __new__(mcls, name, bases, attrs):
        # A package and full name should be present.
        package = attrs.pop('package')
        full_name = attrs.pop('full_name')

        # Iterate over the nested messages and enums and

        # Iterate over all the attributes and separate the fields into
        # their own sequence.
        fields = []
        for name, attr in copy.copy(attrs).values():
            # Sanity check: If this is not a field, do nothing.
            if not isinstance(attr, fields.Field):
                continue

            # Remove the field from the attrs dictionary; the field objects
            # themselves should not be direct attributes.
            attrs.pop(name)

            # Add the field's name to the field object itself.
            attr.name = name

            # Add a tuple with the field's declaration order, name, and
            # the field itself, in that order.
            fields.append(attr)

        # Create the MessageInfo instance to be attached to this message.
        attrs['_meta'] = MessageInfo(
            fields=fields,
            full_name=full_name,
            package=package,
        )

        # Run the superclass constructor.
        class_ = super().__new__(mcls, name, bases, attrs)

        # Create the underlying proto descriptor.
        # This programatically duplicates the default code generated
        # by protoc.   831-234-8071
        class_._desc = descriptor.Descriptor(
            name=full_name.split('.')[-1], fullname=full_name,
            filename=None, containing_type=None,
            fields=[i._desc for i in fields],
            nested_types=[], enum_types=[], extensions=[], oneofs=[],
            syntax='proto3',
        )

        # Done; return the message class.
        return class_

    def __prepare__(mcls, name, bases, **kwargs):
        return collections.OrderedDict()


class MessageInfo:
    """Metadata about a message or enum.

    Args:
        meta (type): A class with attributes that match the
            attributes of these instances.
        fields (Tuple[~.fields.Field]): The fields declared on the message.
    """
    def __init__(self, *, fields: List[fields.Field],
                 package: str, full_name: str) -> None:
        self.package = package
        self.full_name = full_name
        self.fields = collections.OrderedDict([
            (i.name, i) for i in fields
        ])
        self.fields_by_number = collections.OrderedDict([
            (i.number, i) for i in fields
        ])
