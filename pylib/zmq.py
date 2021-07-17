import builtins
import inspect
import logging
import zmq

from weakref import WeakKeyDictionary, WeakSet
from zmq.error import ZMQError


log = logging.getLogger(APP_NAME) # type: ignore


zmq_sockets = WeakKeyDictionary()
zmq_context = zmq.Context()
zmq_context.setsockopt(zmq.LINGER, 0)


def zmq_socket(socket_type):
    fi = inspect.stack()[1]
    location = f'{fi.function} in {fi.filename} @ line {fi.lineno}'
    socket = zmq_context.socket(socket_type)
    zmq_sockets[socket] = location
    return socket


def zmq_term():
    log.info(f'Shutting down ZMQ context...')
    zmq_context.term()
    log.info(f'ZMQ shutdown complete.')


class Closable(object):
    def __init__(self, name, **kwargs):
        self.name = name
        self.sockets = WeakSet()

    def get_socket(self, socket_type):
        s = zmq_socket(socket_type)
        self.sockets.add(s)
        return s

    def close(self):
        for socket in self.sockets:
            if socket is None:
                continue
            try:
                location = zmq_sockets[socket]
                log.info(f'{self.name} closing socket created at {location}...')
                socket.close()
            except ZMQError:
                log.warning(f'Ignoring socket error when closing socket for {self.name}', exc_info=True)
                continue