import builtins
import logging

from sentry_sdk import capture_exception
from time import sleep
from zmq.error import ZMQError, ContextTerminated, Again


log = logging.getLogger(APP_NAME) # type: ignore


class exception_handler(object):

    def __init__(self, name='foo'):
        self.name = name

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, tb):
        if exc_type is None:
            return True

        log.debug(f'Handling {exc_type} with flags...')
        print(f'{exc_type=}, {exc_val=}, {tb=}')
        #import pdb; pdb.set_trace()

        if issubclass(exc_type, Exception):
            log.exception(self.name)
            capture_exception(error=(exc_type, exc_val, tb))
            sleep(1)
            return True

        #except ContextTerminated:
        #    log.warning('ZMQ terminate: {}'.format(self.__class__.__name__))
        #    self.socket.close()
        #    self._mqtt_client.disconnect()
        #    self.processor.close()
        #    log.warning('ZMQ terminated: {}'.format(self.__class__.__name__))
        #    break
        #except ZMQError:
        #    log.exception(self.name)
        #    break
        #except Exception:
        #    # consider mqttc.reinitialise()
        #    log.exception(self.name)
        #    capture_exception()
        #    sleep(1)
        #    continue

        return True