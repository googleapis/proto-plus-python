import collections
import re

from google.protobuf import descriptor_pb2

from proto import _file_info, _package_info


def sample_file_info(name):
    filename = name + ".proto"

    # Get the essential information about the proto package, and where
    # this component belongs within the file.
    package, marshal = _package_info.compile(name, {})

    # Get or create the information about the file, including the
    # descriptor to which the new message descriptor shall be added.
    return _file_info._FileInfo.registry.setdefault(
        filename,
        _file_info._FileInfo(
            descriptor=descriptor_pb2.FileDescriptorProto(
                name=filename, package=package, syntax="proto3",
            ),
            enums=collections.OrderedDict(),
            messages=collections.OrderedDict(),
            name=filename,
            nested={},
        ),
    )


def test_salt_operation_causes_salt():
    # given
    name = "my-fileinfo"
    salt = "my-sat"
    file_info = sample_file_info(name)

    # when
    file_info.generate_file_pb(lambda: salt)

    # then
    assert file_info.descriptor.name == name + "_" + salt + ".proto"


def test_uncallable_salt_operation_causes_random_salt():
    # given
    name = "my-fileinfo"
    salt = "uncallable-salt-operation"
    file_info = sample_file_info(name)

    # when
    file_info.generate_file_pb(salt)

    # then
    actual = file_info.descriptor.name
    regex = "^" + name + "_[0123456789abcdef]{8}.proto$"
    assert re.search(regex, actual)


def test_none_salt_operation_causes_random_salt():
    # given
    name = "my-fileinfo"
    salt = None
    file_info = sample_file_info(name)

    # when
    file_info.generate_file_pb(salt)

    # then
    actual = file_info.descriptor.name
    regex = "^" + name + "_[0123456789abcdef]{8}.proto$"
    assert re.search(regex, actual)
