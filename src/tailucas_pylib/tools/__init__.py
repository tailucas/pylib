from os import linesep
import sys


def err(msg, code=1):
    sys.stderr.write(f"{msg}{linesep}")
    exit(code)


def outl(msg, code=None):
    out(msg=f"{msg}{linesep}", code=code)


def out(msg, code=None):
    sys.stdout.write(msg)
    if code:
        exit(int(code))
