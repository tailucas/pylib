import logging
import zmq

from sentry_sdk import capture_exception
from zmq.error import ZMQError, ContextTerminated

from .zmq import Closable, zmq_socket, try_close


log = logging.getLogger(APP_NAME) # type: ignore


class exception_handler(object):

    def __init__(self, closable: Closable = None, connect_url=None, socket_type=None, and_raise=True, close_on_exit=True):
        self._closable = closable
        self._zmq_socket = None
        self._zmq_url = connect_url
        self._socket_type = socket_type
        self._and_raise = and_raise
        self._close_on_exit = close_on_exit

    def __enter__(self):
        if self._socket_type:
            if self._closable:
                self._zmq_socket = self._closable.get_socket(self._socket_type)
            else:
                self._zmq_socket = zmq_socket(self._socket_type)
        if self._zmq_url:
            if self._socket_type in [zmq.PULL, zmq.PUB]:
                self._zmq_socket.bind(self._zmq_url)
            else:
                self._zmq_socket.connect(self._zmq_url)
        return self._zmq_socket

    def __exit__(self, exc_type, exc_val, tb):
        if self._close_on_exit or (exc_type and issubclass(exc_type, ContextTerminated)):
            if self._closable:
                self._closable.close()
            if self._zmq_socket:
                try_close(self._zmq_socket)
        if exc_type is None:
            return True
        log.debug(f'Handling {exc_type.__name__} with flags...')
        if issubclass(exc_type, ContextTerminated):
            log.debug(self.__class__.__name__, exc_info=True)
            # treat as non-critical
            return True
        elif issubclass(exc_type, ZMQError):
            log.exception(self.__class__.__name__)
        elif issubclass(exc_type, Exception):
            log.exception(self.__class__.__name__)
            capture_exception(error=(exc_type, exc_val, tb))
        return not self._and_raise