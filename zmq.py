import logging
import zmq
from sentry_sdk import capture_exception
from threading import Thread


log = logging.getLogger(APP_NAME)


class Uploader(Thread):

    def __init__(self, zmq_context, zmq_ipc_url, pub_ip, pub_port):
        super(Uploader, self).__init__()
        self.daemon = True
        # Socket to talk to accept samples
        self.inproc_pull = zmq_context.socket(zmq.PULL)
        self._zmq_url = zmq_ipc_url
        self._pub_ip = pub_ip
        self._pub_port = pub_port

    def run(self):
        self.inproc_pull.bind(self._zmq_url)
        # Socket to talk to the outside world
        publisher = zmq_context.socket(zmq.PUB)
        try:
            publisher.bind('tcp://{ip}:{port}'.format(ip=self._pub_ip, port=self._pub_port))
        except ZMQError:
            log.exception(self.__class__.__name__)
            raise

        while True:
            try:
                publisher.send(make_payload(
                    timestamp=None,
                    data=self.inproc_pull.recv_pyobj()))
            except ContextTerminated:
                self.inproc_pull.close()
                publisher.close()
                break
            except Exception:
                log.exception(self.__class__.__name__)
                sentry.captureException()
                sleep(1)
                continue
