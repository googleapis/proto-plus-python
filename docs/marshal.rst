Type Marshaling
===============

Proto Plus provides a service that converts between protocol buffer objects
and native Python types (or the wrapper types provided by this library).

This allows native Python objects to be used in place of protocol buffer
messages where appropriate. In all cases, we return the native type, and are
liberal on what we accept.

Well-known types
----------------

The following types are currently handled by Proto Plus:

=================================== ======================= ========
Protocol buffer type                Python type             Nullable
=================================== ======================= ========
``google.protobuf.BoolValue``       ``bool``                     Yes
``google.protobuf.BytesValue``      ``bytes``                    Yes
``google.protobuf.DoubleValue``     ``float``                    Yes
``google.protobuf.Duration``        ``datetime.timedelta``         –
``google.protobuf.FloatValue``      ``float``                    Yes
``google.protobuf.Int32Value``      ``int``                      Yes
``google.protobuf.Int64Value``      ``int``                      Yes
``google.protobuf.ListValue``       ``MutableSequence``            –
``google.protobuf.StringValue``     ``str``                      Yes
``google.protobuf.Struct``          ``MutableMapping``             –
``google.protobuf.Timestamp``       ``datetime.datetime``        Yes
``google.protobuf.UInt32Value``     ``int``                      Yes
``google.protobuf.UInt64Value``     ``int``                      Yes
``google.protobuf.Value``           JSON-encodable values        Yes
=================================== ======================= ========

.. note::

    Protocol buffers include well-known types for ``Timestamp`` and
    ``Duration``, both of which have nanosecond precision. However, the
    Python ``datetime`` and ``timedelta`` objects have only microsecond
    precision. This library converts timestamps to an implementation of
    ``datetime.datetime``, DatetimeWithNanoseconds, that includes nanosecond
    precision.

    If you *write* a timestamp field using a Python ``datetime`` value,
    any existing nanosecond precision will be overwritten.


Wrapper types
-------------

Additionally, every :class:`~.Message` subclass is a wrapper class. The
creation of the class also creates the underlying protocol buffer class, and
this is registered to the marshal.

The underlying protocol buffer message class is accessible with the
:meth:`~.Message.pb` class method.


Wrapped Proto Message Class Naming
----------------

By default the underlying protocol buffer class is created with an 8 character
random salt. This allows re-use of the filename by other proto messages if
needed (e.g. if __all__ is not used).

You can disable the random nature of the salt by specifying ``random_filename_salt=False``
in your message class declaration. The underlying schema will make use of the
class name instead. This makes your schema names deterministic and able
to be registered in the likes of a schema registry.

For example, given the following declaration in file path ``./path/to/proto/my_model.py``:

.. code-block:: python

    import proto

    class Composer(proto.Message, random_filename_salt=False):
        given_name = proto.Field(proto.STRING, number=1)
        family_name = proto.Field(proto.STRING, number=2)

    class Song(proto.Message, random_filename_salt=False):
        composer = proto.Field(Composer, number=1)
        title = proto.Field(proto.STRING, number=2)
        lyrics = proto.Field(proto.STRING, number=3)
        year = proto.Field(proto.INT32, number=4)

The resulting protobuf schema names will be:

.. code-block:: bash

    path/to/proto/my_model_composer.proto
    path/to/proto/my_model_song.proto

Where ``random_filename_salt`` is not specified or is set to ``True`` you
will get non-deterministically salted names such as:

.. code-block:: bash

    path/to/proto/my_model_1ac73890.proto
    path/to/proto/my_model_3979fad7.proto

Note that the underlying protobuf classes are regenerated on startup so
non-deterministic naming completely negates the utility of a schema
registry tool.