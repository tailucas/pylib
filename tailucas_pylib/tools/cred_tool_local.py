#!/usr/bin/env python
import json
import os
import sys

import onepasswordconnectsdk as OP
from onepasswordconnectsdk.config import ConfigurationError
from onepasswordconnectsdk.client import (
    Client,
    new_client_from_environment,
    FailedToRetrieveItemException
)


def out(msg, code=None):
    sys.stdout.write(msg)
    if code:
        exit(int(code))


def err(msg, code=1):
    sys.stderr.write(msg + '\n')
    exit(code)


creds_client: Client = new_client_from_environment()
creds_vaults = creds_client.get_vaults()
vault_id = os.environ['OP_VAULT']
vault_match = False
for creds_vault in creds_vaults:
    if creds_vault.id == vault_id:
        vault_match = True
if not vault_match:
    err(f'No vault found matching ID {vault_id}')


if __name__ == "__main__":
    argc = len(sys.argv)
    item_name = None
    if argc >= 3:
        item_name = sys.argv[1]
        section_names = sys.argv[2:]
    elif argc == 1:
        cred_schema = sys.stdin.readline().rstrip().split('/')
    else:
        err(f'Unexpected arguments in {sys.argv[1:]}')
    if item_name is None:
        key_item = cred_schema[0]
        if len(cred_schema) == 2:
            value_item = f'.{cred_schema[1]}'
        elif len(cred_schema) > 2:
            value_item = '.'.join(cred_schema[1:])
        try:
            creds = OP.load_dict(client=creds_client, config={"s": {"opitem": key_item, "opfield": value_item}})
        except ConfigurationError as e:
            err(f'{e!s}')
        out(msg=creds["s"], code=0)
    else:
        key_value_pairs = dict()
        for section_name in section_names:
            try:
                item_summary = creds_client.get_item_by_title(item_name, vault_id)
            except FailedToRetrieveItemException as e:
                err(f'{e!s}')
            item = creds_client.get_item(item_summary.id, vault_id)
            section_id = None
            for section in item.sections:
                if section.label == section_name:
                    section_id = section.id
                    break
            if section_id is None:
                err(f'No section {section_name} found.')
            for field in item.fields:
                if field.purpose:
                    # skip default fields
                    continue
                if field.section and field.section.id != section_id:
                    # only include fields from this section
                    continue
                if field.label in key_value_pairs:
                    err(f'{field.label} ({field.value}) already present from another section.')
                key_value_pairs[field.label] = field.value
        out(json.dumps(key_value_pairs))
