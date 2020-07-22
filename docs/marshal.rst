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
----------------------------------

By default the underlying protocol buffer class is created with an 8 character
random salt. This allows re-use of the filename by other proto messages if
needed (e.g. if __all__ is not used).

This means new filenames are created each time the underlying proto classes are generated
which is at startup. Normally this is not visible and causes no issue however if you are
using a schema registry this presents a problem. With a schema registry the name of the
underlying schema becomes important and must remain consistent if the schema registry is
to perform its function.

You can change the default salting behaviour by specifying the named argument
``filename_salt_style`` in your Python proto class (message) declaration and assigning it
one of the enumerated values from the ``FilenameSaltStyle`` enum class.

The following styles are available:

``FilenameSaltStyle.RANDOM``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Default and fallback behavior. An 8 digit random hex sequence is added to the proto filename
for uniqueness causing non-deterministic proto schema names.

For example, given the following declaration in file path ``./path/to/proto/my_model.py``:

.. code-block:: python

    import proto

    class Composer(proto.Message, filename_salt_style=FilenameSaltStyle.RANDOM):
        given_name = proto.Field(proto.STRING, number=1)
        family_name = proto.Field(proto.STRING, number=2)

    class Song(proto.Message, filename_salt_style=FilenameSaltStyle.RANDOM):
        composer = proto.Field(Composer, number=1)
        title = proto.Field(proto.STRING, number=2)
        lyrics = proto.Field(proto.STRING, number=3)
        year = proto.Field(proto.INT32, number=4)

The following proto schemas are created:

.. code-block:: bash

    path/to/proto/my_model_1ac73890.proto # <-- Composer
    path/to/proto/my_model_3979fad7.proto # <-- Song

Where the salt appended to the end of ``my_model_`` is non-deterministic and changes on each
restart of your application.

``FilenameSaltStyle.CLASSNAME``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The name of the python class extending ``proto.Message`` is appended in place of the salt
causing deterministic schema names.

For example, given the following declaration in file path ``./path/to/proto/my_model.py``:

.. code-block:: python

    import proto

    class Composer(proto.Message, filename_salt_style=FilenameSaltStyle.CLASSNAME):
        given_name = proto.Field(proto.STRING, number=1)
        family_name = proto.Field(proto.STRING, number=2)

    class Song(proto.Message, filename_salt_style=FilenameSaltStyle.CLASSNAME):
        composer = proto.Field(Composer, number=1)
        title = proto.Field(proto.STRING, number=2)
        lyrics = proto.Field(proto.STRING, number=3)
        year = proto.Field(proto.INT32, number=4)

The following proto schemas are created:

.. code-block:: bash

    path/to/proto/my_model_composer.proto # <-- Composer
    path/to/proto/my_model_song.proto # <-- Song

Where the salt appended to the end of ``my_model_`` is deterministic and does not change on each
restart of your application.
.