from threading import Thread

import zmq

from . import log
from .data import make_payload
from .handler import exception_handler
from .threads import shutting_down, threads_tracked
from .zmq import Closable


class AppThread(Thread):
    def __init__(self, name):
        Thread.__init__(self, name=name)
        self.daemon = True
        threads_tracked.add(self.name)

    def untrack(self):
        threads_tracked.remove(self.name)


class ZmqRelay(AppThread, Closable):
    def __init__(self, name, source_zmq_url, sink_zmq_url):
        AppThread.__init__(self, name=name)
        Closable.__init__(self, connect_url=source_zmq_url)
        self._sink_zmq_url = sink_zmq_url

    def process_message(self, sink_socket):
        data = self.socket.recv_pyobj()  # type: ignore
        payload = make_payload(data=data)
        # do not info on heartbeats
        if "device_info" not in data:  # type: ignore
            log.debug(
                "Relaying message",
                extra={
                    "message_bytes": len(data),  # type: ignore
                    "source_url": self.socket_url,
                    "sink_url": self._sink_zmq_url,
                    "payload_bytes": len(payload),
                },
            )
        sink_socket.send(payload)

    def startup(self):
        pass

    def run(self):
        self.startup()
        self.get_socket()
        with exception_handler(
            connect_url=self._sink_zmq_url, and_raise=False, shutdown_on_error=True
        ) as socket:
            while not shutting_down:
                self.process_message(sink_socket=socket)
        self.close()


class ZmqWorker(AppThread):
    def __init__(self, name: str, worker_zmq_url: str):
        AppThread.__init__(self, name=name)
        self._worker_zmq_url = worker_zmq_url

    def process_message(self, message: dict[str, object]) -> dict[str, object]:
        raise NotImplementedError()

    def startup(self):
        pass

    def run(self):
        self.startup()
        with exception_handler(
            connect_url=self._worker_zmq_url,
            socket_type=zmq.REP,
            and_raise=False,
            shutdown_on_error=True,
        ) as zmq_socket:
            while not shutting_down:
                message = zmq_socket.recv_pyobj()
                response = self.process_message(message=message)  # type: ignore
                zmq_socket.send_pyobj(response)
