import logging
import signal
import subprocess

from . import log
from .threads import die


def exec_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out, err, p.returncode


def exec_cmd_log(cmd):
    o, e, c = exec_cmd(cmd)
    log.debug(
        "Command completed",
        extra={
            "cmd": cmd,
            "exit_code": c,
            "stdout": o.decode(errors="replace") if o else "",
            "stderr": e.decode(errors="replace") if e else "",
        },
    )


# noinspection PyUnusedLocal
class SignalHandler:
    def __init__(self):
        self.last_signal = 0
        signal.signal(signal.SIGTERM, self.terminate)
        signal.signal(signal.SIGHUP, self.hup)

    def hup(self, signum, frame):
        log.debug("Signal received", extra={"signal": signum})
        self.last_signal = signum
        if log.getEffectiveLevel() == logging.INFO:
            log.setLevel(logging.DEBUG)
        elif log.getEffectiveLevel() == logging.DEBUG:
            log.setLevel(logging.INFO)

    def terminate(self, signum, frame):
        log.debug("Signal received", extra={"signal": signum})
        self.last_signal = signum
        die()
