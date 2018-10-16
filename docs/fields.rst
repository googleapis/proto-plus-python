Fields
======

Fields are assigned using the :class:`~.Field` class, instantiated within a
:class:`~.Message` declaraction.

Fields always have a type (either a primitive, a message, or an enum) and a
``number``. Additionally, if the type is ``MESSAGE`` or ``ENUM``, then they
have an additional keyword argument declaring what the type is.

For messages and enums, assign the message or enum class directly (as shown
in the example above). For messages declared in the same module, it is also
possible to use a string with the message class' name, which allows for
declaring messages out of order or with circular references.

Repeated fields
---------------

Some fields are actually repeated fields. In protocol buffers, repeated fields
are generally equivalent to typed lists. In protocol buffers, these are
declared using the **repeated** keyword:

.. code-block:: protobuf

    message Album {
      repeated Song songs = 1;
      string publisher = 2;
    }

Declare them in Python using the :class:`~.RepeatedField` class:

.. code-block:: python

    class Album(proto.Message):
        songs = proto.RepeatedField(proto.MESSAGE, message=Song, number=1)
        publisher = proto.Field(proto.STRING, number=2)


Map fields
----------

Similarly, some fields are map fields. In protocol buffers, map fields are
equivalent to typed dictionaries, where the keys are either strings or
integers, and the values can be any type. In protocol buffers, these use
a special ``map`` syntax:

.. code-block:: protobuf

    message Album {
      map<uint32, Song> track_list = 1;
      string publisher = 2;
    }

Declare them in Python using the :class:`~.MapField` class:

.. code-block:: python

    class Album(proto.Message):
        track_list = proto.MapField(proto.INT32, proto.MESSAGE, number=1,
            message=Song,
        )
        publisher = proto.Field(proto.STRING, number=2)


Oneofs (mutually-exclusive fields)
----------------------------------

Protocol buffers allows certain fields to be declared as mutually exclusive.
This is done by wrapping fields in a ``oneof`` syntax:

.. code-block:: protobuf

    import "google/type/postal_address.proto";

    message AlbumPurchase {
      Album album = 1;
      oneof delivery {
        google.type.PostalAddress postal_address = 2;
        string download_uri = 3;
      }
    }

When using this syntax, protocol buffers will enforce that only one of the
given fields is set on the message, and setting a field within the oneof
will clear any others.

Declare this in Python using the ``oneof`` keyword-argument, which takes
a string (which should match for all fields within the oneof):

.. code-block:: python

    from google.type.postal_address import PostalAddress

    class AlbumPurchase(proto.Message):
        album = proto.Field(proto.MESSAGE, message=Album, number=1)
        postal_address = proto.Field(proto.MESSAGE, number=2,
            message=PostalAddress, oneof='delivery')
        download_uri = proto.Field(proto.STRING, number=3, oneof='delivery')
