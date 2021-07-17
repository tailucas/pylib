import builtins
import logging

from weakref import WeakValueDictionary

from sentry_sdk import capture_exception
from time import sleep
from zmq.error import ZMQError, ContextTerminated, Again

from .zmq import Closable, zmq_socket, try_close

log = logging.getLogger(APP_NAME) # type: ignore


class exception_handler(object):

    def __init__(self, closable: Closable = None, with_socket_type=None, connect_url=None, and_raise=False):
        self._closable = closable
        self._socket_type = with_socket_type
        self._zmq_socket = None
        self._zmq_url = connect_url
        self._and_raise = and_raise

    def __enter__(self):
        if self._socket_type:
            self._zmq_socket = zmq_socket(self._socket_type)
        if self._zmq_url:
            self._zmq_socket.connect(self._zmq_url)
        return self._zmq_socket

    def __exit__(self, exc_type, exc_val, tb):
        if exc_type is None:
            return True
        log.debug(f'Handling {exc_type.__name__} with flags...')
        if exc_type is ContextTerminated:
            if self._closable:
                self._closable.close()
            else:
                log.warning(f'Received ZMQ {exc_type.__name__} but not closable. Propagating...', exc_info=True)
        elif issubclass(exc_type, ZMQError):
            log.exception()
        elif issubclass(exc_type, Exception):
            log.exception()
            capture_exception(error=(exc_type, exc_val, tb))
        if self._zmq_socket:
            try_close(self._zmq_socket)
        return self._and_raise