import re

import proto


def test_no_random_filename_salt_on_false():
    class Foo(proto.Message, random_filename_salt=False):
        bar = proto.Field(proto.INT32, number=1)

    assert Foo.pb(Foo()).DESCRIPTOR.file.name == "test_message_filename_foo.proto"


def test_random_filename_salt_on_true():
    class Foo(proto.Message, random_filename_salt=True):
        bar = proto.Field(proto.INT32, number=1)

    name = Foo.pb(Foo()).DESCRIPTOR.file.name
    assert re.search("^test_message_filename_[0123456789abcdef]{8}.proto$", name)


def test_random_filename_salt_on_not_set():
    class Foo(proto.Message):
        bar = proto.Field(proto.INT32, number=1)

    name = Foo.pb(Foo()).DESCRIPTOR.file.name
    assert re.search("^test_message_filename_[0123456789abcdef]{8}.proto$", name)
