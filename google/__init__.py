# Force native protocol buffers into the Python (not C) implementation.
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# Declare the usual Python namespace packaging jig.
if __name__ != '__main__':
    try:
        __import__('pkg_resources').declare_namespace(__name__)
    except ImportError:
        __path__ = __import__('pkgutil').extend_path(__path__, __name__)
