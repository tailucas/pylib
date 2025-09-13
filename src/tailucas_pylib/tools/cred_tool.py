#!/usr/bin/env python
import json
import sys

from .. import creds


def out(msg, code=None):
    sys.stdout.write(msg)
    if code:
        exit(int(code))


def err(msg, code=1):
    sys.stderr.write(msg + "\n")
    exit(code)


def main():
    argc = len(sys.argv)
    cred_path = None
    item_name = None
    section_names = None
    if argc == 1:
        cred_path = sys.stdin.readline().rstrip()
        if len(cred_path) == 0:
            err("No credential path specified.")
    elif argc >= 3:
        item_name = sys.argv[1]
        section_names = sys.argv[2:]
    else:
        err(f"Unexpected arguments in {sys.argv[1:]}")
    if item_name is None:
        cred = creds.get_creds(cred_path)  # type: ignore
        out(msg=str(cred), code=0)
    else:
        cred = creds.get_fields_from_sections(item_name, section_names)  # type: ignore
        out(json.dumps(cred))


if __name__ == "__main__":
    main()
