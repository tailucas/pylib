import logging
import signal
import subprocess

from pathlib import Path

from . import threads

log = logging.getLogger(Path(__file__).stem)


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
        global shutting_down
        log.warning('Signal {} received.'.format(signum))
        self.last_signal = signum
        threads.shutting_down = True
        threads.interruptable_sleep.set()