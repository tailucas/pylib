import sys


def err(msg, code=1):
    print(msg, file=sys.stderr)
    exit(code)


def outl(msg, code=None):
    print(msg)
    if code:
        exit(int(code))


def out(msg, code=None):
    print(msg, end="")
    if code:
        exit(int(code))
