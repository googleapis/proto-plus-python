import re

import proto
from proto.message import FilenameSaltStyle


def test_classname_filename_salt_style_causes_classname_salt():
    class Foo(proto.Message, filename_salt_style=FilenameSaltStyle.CLASSNAME):
        bar = proto.Field(proto.INT32, number=1)

    assert Foo.pb(Foo()).DESCRIPTOR.file.name == "test_message_filename_foo.proto"


random_salt_regex = "^test_message_filename_[0123456789abcdef]{8}.proto$"


def test_random_filename_salt_style_causes_random_salt():
    class Foo(proto.Message, filename_salt_style=FilenameSaltStyle.RANDOM):
        bar = proto.Field(proto.INT32, number=1)

    name = Foo.pb(Foo()).DESCRIPTOR.file.name
    assert re.search(random_salt_regex, name)


def test_filename_salt_style_not_set_causes_random_salt():
    class Foo(proto.Message):
        bar = proto.Field(proto.INT32, number=1)

    name = Foo.pb(Foo()).DESCRIPTOR.file.name
    assert re.search(random_salt_regex, name)


def test_random_filename_salt_set_to_rubbish_causes_random_salt():
    class Foo(proto.Message, filename_salt_style="some rubbish"):
        bar = proto.Field(proto.INT32, number=1)

    name = Foo.pb(Foo()).DESCRIPTOR.file.name
    assert re.search(random_salt_regex, name)
