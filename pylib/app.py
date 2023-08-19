import asyncio
import logging

from threading import Thread
from typing import Dict
from zmq import PUSH, PULL, PUB, REP
from zmq.asyncio import Socket as AsyncSocket

from .data import make_payload
from .handler import exception_handler
from .threads import shutting_down, threads_tracked
from .zmq import Closable


log = logging.getLogger(APP_NAME)  # type: ignore


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


class ZmqWorker(AppThread, Closable):

    def __init__(self, name: str, worker_zmq_url: str):
        AppThread.__init__(self, name=name)
        Closable.__init__(self, connect_url=worker_zmq_url, socket_type=REP, is_async=True, do_connect=False)

    async def process_message(self, message: Dict) -> Dict:
        raise NotImplementedError()

    def startup(self):
        pass

    async def async_run(self):
        with exception_handler(closable=self) as zmq_socket:
            while not shutting_down:
                message = await zmq_socket.recv_pyobj()
                response = await self.process_message(message=message)
                await zmq_socket.send_pyobj(response)

    def run(self):
        self.startup()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_run())
        finally:
            loop.close()
