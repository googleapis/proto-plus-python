import proto


PACKAGE = "a.test.package.with.and.without.manifest"
__protobuf__ = proto.module(package=PACKAGE, manifest={"This", "That"},)


class This(proto.Message):
    this = proto.Field(proto.INT32, number=1)


class That(proto.Message):
    that = proto.Field(proto.INT32, number=1)


class NotInManifest(proto.Message):
    them = proto.Field(proto.INT32, number=1)


def test_manifest_causes_exclusion_of_classname_salt():

    assert (
        This.pb(This()).DESCRIPTOR.file.name
        == "test_message_filename_with_and_without_manifest.proto"
    )
    assert (
        That.pb(That()).DESCRIPTOR.file.name
        == "test_message_filename_with_and_without_manifest.proto"
    )

    assert (
        NotInManifest.pb(NotInManifest()).DESCRIPTOR.file.name
        == "test_message_filename_with_and_without_manifest_"
        + PACKAGE
        + ".notinmanifest.proto"
    )
