import logging
import signal

log = logging.getLogger(APP_NAME)


def exec_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out, err, p.returncode


# noinspection PyUnusedLocal
class SignalHandler:

    def __init__(self):
        self.last_signal = 0
        signal.signal(signal.SIGTERM, self.terminate)
        signal.signal(signal.SIGHUP, self.hup)

    def hup(self, signum, frame):
        log.warning('Signal {} received.'.format(signum))
        self.last_signal = signum
        if log.getEffectiveLevel() == logging.INFO:
            log.setLevel(logging.DEBUG)
        elif log.getEffectiveLevel() == logging.DEBUG:
            log.setLevel(logging.INFO)

    def terminate(self, signum, frame):
        log.warning('Signal {} received.'.format(signum))
        self.last_signal = signum
        interruptable_sleep.set()