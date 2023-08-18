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
# FIXME: https://github.com/zeromq/pyzmq/issues/940
zmq_async_context = AsyncioContext.shadow(zmq_context.underlying)


def zmq_socket(socket_type: int, is_async: Optional[bool]=False):
    fi = inspect.stack()[-1]
    location = f'{fi.function} in {fi.filename} @ line {fi.lineno}'
    if is_async:
        socket = zmq_async_context.socket(socket_type)
    else:
        socket = zmq_context.socket(socket_type)
    zmq_sockets[socket] = location
    return socket


def zmq_term():
    log.info(f'Shutting down ZMQ context...')
    zmq_context.term()
    log.info(f'ZMQ shutdown complete.')


def try_close(socket):
    if socket is None:
        return
    try:
        try:
            location = zmq_sockets[socket]
            if location:
                log.info(f'Closing socket created at {location}...')
        except KeyError:
            pass
        socket.close()
    except ZMQError:
        log.warning(f'Ignoring socket error when closing socket.', exc_info=True)


class Closable(object):

    @property
    def is_async(self) -> bool:
        return self._is_async

    @property
    def socket_type(self) -> int:
        return self._socket_type

    @property
    def socket_url(self) -> str:
        return self._socket_url

    def __init__(self, connect_url=None, socket_type=zmq.PULL, is_async: Optional[bool]=False, do_connect: Optional[bool]=True):
        self.sockets = WeakSet()
        self.socket = None
        self._socket_url: str = connect_url
        self._socket_type: int = socket_type
        self._is_async: bool = is_async
        if connect_url and do_connect:
            self.socket = self.get_socket(socket_type, is_async=is_async)
            if socket_type in [zmq.PULL, zmq.PUB, zmq.REP]:
                self.socket.bind(connect_url)
            else:
                self.socket.connect(connect_url)

    def get_socket(self, socket_type: Optional[int]=None, is_async: Optional[bool]=False):
        if socket_type is None:
            socket_type = self._socket_type
        s = zmq_socket(socket_type=socket_type, is_async=is_async)
        self.sockets.add(s)
        return s

    def close(self):
        for socket in self.sockets:
            try_close(socket)