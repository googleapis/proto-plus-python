Proto Plus for Python
=====================

    Beautiful, Pythonic protocol buffers.

This library provides a clean, readable, straightforward pattern for
declaraing messages in `protocol buffers`_. It provides a wrapper around
the official implementation, so that using messages feels natural while
retaining the power and flexibility of protocol buffers.

.. warning::

  This tool is a proof of concept and is being iterated on rapidly.
  Feedback is welcome, but please do not try to use this in some kind of
  system where stability is an expectation.

.. _protocol buffers: https://developers.google.com/protocol-buffers/


Installing
----------

Install this library using ``pip``:

.. code-block:: shell

    $ pip install proto-plus

This library carries a dependency on the official implementation
(``protobuf``), which may install a C component.


Table of Contents
-----------------

.. toctree::
  :maxdepth: 2

  messages
  fields
  marshal
  status
  reference/index
