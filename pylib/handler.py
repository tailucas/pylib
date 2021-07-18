import builtins
import logging
from sys import exc_info

from weakref import WeakValueDictionary

from sentry_sdk import capture_exception
from time import sleep
from zmq.error import ZMQError, ContextTerminated, Again

from .zmq import Closable, zmq_socket, try_close

log = logging.getLogger(APP_NAME) # type: ignore


class exception_handler(object):

    def __init__(self, closable: Closable = None, connect_url=None, with_socket_type=None, and_raise=True, close_on_exit=True):
        self._closable = closable
        self._zmq_socket = None
        self._zmq_url = connect_url
        self._socket_type = with_socket_type
        self._and_raise = and_raise
        self._close_on_exit = close_on_exit

    def __enter__(self):
        if self._socket_type:
            self._zmq_socket = zmq_socket(self._socket_type)
        if self._zmq_url:
            self._zmq_socket.connect(self._zmq_url)
        return self._zmq_socket

    def __exit__(self, exc_type, exc_val, tb):
        if self._close_on_exit or issubclass(exc_type, ContextTerminated):
            if self._closable:
                self._closable.close()
            if self._zmq_socket:
                try_close(self._zmq_socket)
        if exc_type is None:
            return True
        log.debug(f'Handling {exc_type.__name__} with flags...')
        if issubclass(exc_type, ContextTerminated):
            log.warning(self.__class__.__name__)
        elif issubclass(exc_type, ZMQError):
            log.exception(self.__class__.__name__)
        elif issubclass(exc_type, Exception):
            log.exception(self.__class__.__name__)
            capture_exception(error=(exc_type, exc_val, tb))
        return not self._and_raise