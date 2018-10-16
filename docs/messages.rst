Messages
========

The fundamental building block in protocol buffers are `messages`_.
Messages are essentially permissive, strongly-typed structs (dictionaries),
which have zero or more fields that may themselves contain primitives or
other messages.

.. code-block:: protobuf

  syntax = "proto3";

  message Song {
    Composer composer = 1;
    string title = 2;
    string lyrics = 3;
    int32 year = 4;
  }

  message Composer {
    string given_name = 1;
    string family_name = 2;
  }

The most common use case for protocol buffers is to write a ``.proto`` file,
and then use the protocol buffer compiler to generate code for it.
However, it is possible to declare messages directly.

This is the equivalent message declaration in Python, using this library:

.. code-block:: python

    import proto

    class Composer(proto.Message):
        given_name = proto.Field(proto.STRING, number=1)
        family_name = proto.Field(proto.STRING, number=2)

    class Song(proto.Message):
        composer = proto.Field(proto.MESSAGE, message=Composer, number=1)
        title = proto.Field(proto.STRING, number=2)
        lyrics = proto.Field(proto.STRING, number=3)
        year = proto.Field(proto.INT32, number=4)

A few things to note:

* This library only handles proto3.
* The ``number`` is really a field ID. It is *not* a value of any kind.
* All fields are optional (as is always the case in proto3). As a general
  rule, there is no distinction between setting the type's falsy value and
  not setting it at all (although there are exceptions to this in some cases).

.. _messages: https://developers.google.com/protocol-buffers/docs/proto3#simple

Messages are fundamentally made up of :doc:`fields`. Most messages are nothing
more than a name and their set of fields.
