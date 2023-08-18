import logging
import zmq

from sentry_sdk import capture_exception
from typing import ContextManager, Optional
from zmq.error import ZMQError, ContextTerminated

from . import threads

from .threads import die
from .zmq import Closable, zmq_socket, try_close


log = logging.getLogger(APP_NAME)  # type: ignore


class exception_handler(ContextManager):

    def __init__(
            self,
            closable: Optional[Closable] = None,
            connect_url: Optional[str]=None,
            socket_type: Optional[int]=None,
            and_raise: Optional[bool]=True,
            close_on_exit: Optional[bool]=True,
            shutdown_on_error: Optional[bool]=False):
        self._closable = closable
        self._zmq_socket = None
        self._zmq_url = connect_url
        self._socket_type = socket_type
        self._and_raise = and_raise
        self._close_on_exit = close_on_exit
        self._shutdown_on_error = shutdown_on_error

    def __enter__(self):
        if self._socket_type:
            if self._closable:
                self._zmq_socket = self._closable.get_socket()
            else:
                self._zmq_socket = zmq_socket(self._socket_type)
        if self._zmq_url:
            if self._socket_type in [zmq.PULL, zmq.PUB, zmq.REP]:
                self._zmq_socket.bind(self._zmq_url)
            else:
                self._zmq_socket.connect(self._zmq_url)
        return self._zmq_socket

    def __exit__(self, exc_type, exc_val, tb):
        if self._close_on_exit or (exc_type and issubclass(exc_type, ContextTerminated)):
            if self._closable:
                self._closable.close()
            elif self._zmq_socket:
                try_close(self._zmq_socket)
        if exc_type is None:
            return True
        log.debug(f'Handling {exc_type.__name__} with flags...')
        if issubclass(exc_type, ContextTerminated):
            log.debug(self.__class__.__name__, exc_info=True)
            # treat as non-critical
            return True
        elif issubclass(exc_type, ResourceWarning):
            # raised to indicate a fatal dependency error that
            # does not fill Sentry with exception regressions
            # or unhandled exceptions; used typically at startup
            log.warning(self.__class__.__name__, exc_info=True)
            if self._shutdown_on_error:
                die(exception=exc_type)
        elif issubclass(exc_type, Exception):
            if not threads.shutting_down:
                log.exception(self.__class__.__name__)
                capture_exception(error=(exc_type, exc_val, tb))
                if self._shutdown_on_error:
                    die(exception=exc_type)
            else:
                # log the exception as informational if in debug mode
                log.debug(self.__class__.__name__, exc_info=True)
        return not self._and_raise