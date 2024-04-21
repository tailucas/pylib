import inspect
import logging
import zmq

from typing import Optional

from weakref import WeakKeyDictionary, WeakSet
from zmq.error import ZMQError

log = logging.getLogger(APP_NAME)  # type: ignore

zmq_sockets = WeakKeyDictionary()
zmq_context = zmq.Context()
zmq_context.setsockopt(zmq.LINGER, 0)
# asyncio capabilities
from zmq.asyncio import Context as AsyncioContext
zmq_async_context = None


def zmq_socket(socket_type: int, is_async: Optional[bool]=False):
    call_stack = inspect.stack()
    locations = []
    for fi in call_stack:
        locations.append(f'{fi.function} in {fi.filename} @ line {fi.lineno}')
    location = ', '.join(locations)
    log.debug(f'Creating {is_async=} {socket_type} ({zmq.PUSH=}, {zmq.PULL=}, {zmq.REQ=}, {zmq.REP=}) socket for location {location}...')
    if is_async:
        global zmq_async_context
        if zmq_async_context is None:
            # FIXME: https://github.com/zeromq/pyzmq/issues/940
            # FIXME: Exception in callback Socket._init_io_state.<locals>.<lambda>() on Context.term() within asyncio
            zmq_async_context = AsyncioContext.shadow(zmq_context.underlying)
            zmq_async_context.setsockopt(zmq.LINGER, 0)
        socket = zmq_async_context.socket(socket_type)
    else:
        socket = zmq_context.socket(socket_type)
    zmq_sockets[socket] = location
    return socket


def zmq_term():
    log.info(f'Shutting down ZMQ context...')
    zmq_context.term()
    global zmq_async_context
    if zmq_async_context:
        log.info(f'Shutting down async ZMQ context...')
        try:
            zmq_async_context.term()
        except Exception:
            log.debug('Error closing async ZMQ context.', exc_info=True)
    log.info(f'ZMQ shutdown complete.')


def try_close(socket):
    if socket is None:
        return
    try:
        try:
            location = zmq_sockets[socket]
            if location:
                log.debug(f'Closing {socket!r} created at {location}...')
        except KeyError:
            log.debug(f'Closing {socket!r}...')
        socket.close()
    except ZMQError:
        log.warning(f'Ignoring socket error when closing socket.', exc_info=True)


class Closable(object):

    @property
    def socket(self):
        return self._socket

    @property
    def socket_type(self):
        return self._socket_type

    @property
    def socket_url(self):
        return self._socket_url

    def __init__(self, connect_url: str, socket_type=zmq.PULL, is_async: Optional[bool]=False):
        self._socket = None
        self._socket_url: str = connect_url
        self._socket_type: int = socket_type
        self._is_async: Optional[bool] = is_async

    def get_socket(self):
        if self._socket is None:
            self._socket = zmq_socket(socket_type=self._socket_type, is_async=self._is_async)
            if self._socket_type in [zmq.PULL, zmq.PUB, zmq.REP]:
                log.debug(f'Binding {self._socket_type} ({zmq.PULL=}, {zmq.PUB=}, {zmq.REP=}) ZMQ socket to {self._socket_url}.')
                self._socket.bind(self._socket_url)
            else:
                log.debug(f'Connecting {self._socket_type} ({zmq.PUSH=}, {zmq.PULL=}, {zmq.REQ=}, {zmq.REP=}) ZMQ socket to {self._socket_url}')
                self._socket.connect(self._socket_url)
        return self._socket

    def close(self):
        try_close(self._socket)
