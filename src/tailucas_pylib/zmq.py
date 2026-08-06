import inspect
from weakref import WeakKeyDictionary

import zmq
from zmq.asyncio import Context as AsyncioContext
from zmq.error import ZMQError

from . import log

zmq_sockets: WeakKeyDictionary = WeakKeyDictionary()  # type: ignore[type-arg]
zmq_context = zmq.Context()
zmq_context.setsockopt(zmq.LINGER, 0)
# asyncio capabilities

zmq_async_context = None


URL_WORKER_APP = "inproc://app"
URL_WORKER_PUBLISHER = "inproc://publisher"
URL_WORKER_RELAY = "inproc://app-relay"


def zmq_socket(socket_type: int, is_async: bool | None = False):
    call_stack = inspect.stack()
    locations = []
    for fi in call_stack:
        locations.append(f"{fi.function} in {fi.filename} @ line {fi.lineno}")
    location = ", ".join(locations)
    log.debug(
        "Creating ZMQ socket",
        extra={
            "is_async": is_async,
            "socket_type": socket_type,
            "socket_types": {"push": zmq.PUSH, "pull": zmq.PULL, "req": zmq.REQ, "rep": zmq.REP},
            "location": location,
        },
    )
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
    log.debug("Shutting down ZMQ context...")
    zmq_context.term()
    global zmq_async_context
    if zmq_async_context:
        log.debug("Shutting down async ZMQ context...")
        try:
            zmq_async_context.term()
        except Exception:
            log.debug("Error closing async ZMQ context.", exc_info=True)
    log.debug("ZMQ shutdown complete.")


def try_close(socket):
    if socket is None:
        return
    try:
        try:
            location = zmq_sockets[socket]
            if location:
                log.debug("Closing socket", extra={"socket": repr(socket), "created_at": location})
        except KeyError:
            log.debug("Closing socket", extra={"socket": repr(socket)})
        socket.close()
    except ZMQError:
        log.debug("Ignoring socket error when closing socket.", exc_info=True)


class Closable:
    @property
    def socket(self):
        return self._socket

    @property
    def socket_type(self):
        return self._socket_type

    @property
    def socket_url(self):
        return self._socket_url

    def __init__(self, connect_url: str, socket_type=zmq.PULL, is_async: bool | None = False):
        self._socket = None
        self._socket_url: str = connect_url
        self._socket_type: int = socket_type
        self._is_async: bool | None = is_async

    def get_socket(self):
        if self._socket is None:
            self._socket = zmq_socket(socket_type=self._socket_type, is_async=self._is_async)
            assert self._socket is not None
            if self._socket_type in [zmq.PULL, zmq.PUB, zmq.REP]:
                log.debug(
                    "Binding ZMQ socket",
                    extra={
                        "socket_type": self._socket_type,
                        "socket_url": self._socket_url,
                        "socket_types": {"pull": zmq.PULL, "pub": zmq.PUB, "rep": zmq.REP},
                    },
                )
                self._socket.bind(self._socket_url)
            else:
                log.debug(
                    "Connecting ZMQ socket",
                    extra={
                        "socket_type": self._socket_type,
                        "socket_url": self._socket_url,
                        "socket_types": {
                            "push": zmq.PUSH,
                            "pull": zmq.PULL,
                            "req": zmq.REQ,
                            "rep": zmq.REP,
                        },
                    },
                )
                self._socket.connect(self._socket_url)
        return self._socket

    def close(self):
        try_close(self._socket)
