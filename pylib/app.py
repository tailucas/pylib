import logging

from threading import Thread
from zmq import PUSH, PULL, PUB

from . import APP_NAME
from .data import make_payload
from .handler import exception_handler
from .threads import shutting_down, threads_tracked
from .zmq import Closable

log = logging.getLogger(APP_NAME)

class AppThread(Thread):

    def __init__(self, name):
        Thread.__init__(self, name=name)
        self.daemon = True
        threads_tracked.add(self.name)

    def untrack(self):
        threads_tracked.remove(self.name)


class ZmqRelay(AppThread, Closable):

    def __init__(self, name, source_zmq_url, source_socket_type, sink_zmq_url, sink_socket_type):
        AppThread.__init__(self, name=name)
        self._sink_zmq_url = sink_zmq_url
        Closable.__init__(self, connect_url=sink_zmq_url, socket_type=sink_socket_type)
        self._source_zmq_url = source_zmq_url
        self._source_socket_type = source_socket_type

    def process_message(self, zmq_socket):
        data = zmq_socket.recv_pyobj()
        payload = make_payload(data=data)
        # do not info on heartbeats
        if 'device_info' not in data:
            log.debug(f'Relaying {len(data)} bytes from {self._source_zmq_url} to {self._sink_zmq_url} ({len(payload)} bytes)')
        self.socket.send(payload)

    def startup(self):
        pass

    def run(self):
        self.startup()
        with exception_handler(closable=self, connect_url=self._source_zmq_url, socket_type=self._source_socket_type) as zmq_socket:
            while not shutting_down:
                self.process_message(zmq_socket=zmq_socket)
