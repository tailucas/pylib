import inspect
import logging
import zmq

from weakref import WeakKeyDictionary, WeakSet
from zmq.error import ZMQError


log = logging.getLogger(APP_NAME)  # type: ignore


zmq_sockets = WeakKeyDictionary()
zmq_context = zmq.Context()
zmq_context.setsockopt(zmq.LINGER, 0)


def zmq_socket(socket_type):
    fi = inspect.stack()[-1]
    location = f'{fi.function} in {fi.filename} @ line {fi.lineno}'
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
    def __init__(self, connect_url=None, socket_type=zmq.PULL):
        self.sockets = WeakSet()
        self.socket = None
        if connect_url:
            self.socket = self.get_socket(socket_type)
            if socket_type in [zmq.PULL, zmq.PUB]:
                self.socket.bind(connect_url)
            else:
                self.socket.connect(connect_url)

    def get_socket(self, socket_type):
        s = zmq_socket(socket_type)
        self.sockets.add(s)
        return s

    def close(self):
        for socket in self.sockets:
            try_close(socket)