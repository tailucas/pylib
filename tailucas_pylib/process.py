import logging
import signal
import subprocess

from .threads import die


log = logging.getLogger(APP_NAME)  # type: ignore


def exec_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out, err, p.returncode


def exec_cmd_log(cmd):
    o,e,c = exec_cmd(cmd)
    log.info(f'{cmd} (exit {c}): {o}{e}')


# noinspection PyUnusedLocal
class SignalHandler:

    def __init__(self):
        self.last_signal = 0
        signal.signal(signal.SIGTERM, self.terminate)
        signal.signal(signal.SIGHUP, self.hup)

    def hup(self, signum, frame):
        log.warning(f'Signal {signum} received.')
        self.last_signal = signum
        if log.getEffectiveLevel() == logging.INFO:
            log.setLevel(logging.DEBUG)
        elif log.getEffectiveLevel() == logging.DEBUG:
            log.setLevel(logging.INFO)

    def terminate(self, signum, frame):
        log.warning(f'Signal {signum} received.')
        self.last_signal = signum
        die()
