import proto

PACKAGE = "a.test.package.with.manifest"
__protobuf__ = proto.module(package=PACKAGE, manifest={"ThisFoo", "ThisBar"},)


class ThisFoo(proto.Message):
    foo = proto.Field(proto.INT32, number=1)


class ThisBar(proto.Message):
    bar = proto.Field(proto.INT32, number=2)


def test_manifest_causes_exclusion_of_classname_salt():
    assert (
        ThisFoo.pb(ThisFoo()).DESCRIPTOR.file.name
        == "test_message_filename_with_manifest.proto"
    )
    assert (
        ThisBar.pb(ThisBar()).DESCRIPTOR.file.name
        == "test_message_filename_with_manifest.proto"
    )
