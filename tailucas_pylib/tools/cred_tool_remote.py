#!/usr/bin/env python
import asyncio
import json
import os
import sys

from typing import List

from onepassword import Client
from onepassword.types import ItemOverview, VaultOverview, Item, ItemSection, ItemField


def out(msg, code=None):
    sys.stdout.write(msg)
    if code:
        exit(int(code))


def err(msg, code=1):
    sys.stderr.write(msg + '\n')
    exit(code)


async def main():
    # first validate inputs
    argc = len(sys.argv)
    item_path = None
    item_name = None
    section_names = None
    if argc == 1:
        item_path = sys.stdin.readline().rstrip()
        if len(item_path) == 0:
            err(f'No credential path provided to STDIN.')
    if argc >= 2:
        item_name = sys.argv[1]
    if argc >= 3:
        section_names = set(sys.argv[2:])
    if item_name is not None and item_path is not None:
        err(f'Only a single credential specification supported.')
    # next, validate credential context
    token = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")
    creds_client: Client = await Client.authenticate(
        auth=token,
        # Set the following to your own integration name and version.
        integration_name="1Password Integration",
        integration_version="v1.0.0",
    )
    # determine the correct vault
    vault_id = None
    vaults: List[VaultOverview] = await creds_client.vaults.list()
    if len(vaults) == 0:
        err(f'No vaults found.')
    elif len(vaults) == 1:
        vault_id = vaults[0].id
    elif len(vaults) > 1:
        vault_id = os.getenv("OP_VAULT")
        if vault_id is None:
            vault_ids = []
            for vault in vaults:
                vault_ids.append(vault.id)
            err(f'Set OP_VAULT environment variable to disambiguate available vaults: f{vault_ids!s}')
        vault_match = False
        for creds_vault in vaults:
            if creds_vault.id == vault_id:
                vault_match = True
        if not vault_match:
            err(f'No vault found matching ID {vault_id}')
    if item_path:
        value = None
        try:
            value = await creds_client.secrets.resolve(f'op://{vault_id}/{item_path}')
        except Exception as e:
            err(f'{e!s}')
        out(msg=value, code=0)
    else:
        key_value_pairs = dict()
        creds_items: List[ItemOverview] = await creds_client.items.list(vault_id)
        for cred_item in creds_items:
            item: Item = await creds_client.items.get(vault_id, cred_item.id)
            if item.title != item_name:
                continue
            op_sections = dict()
            if len(item.sections) > 0:
                item_sections: List[ItemSection] = item.sections
                for item_section in item_sections:
                    op_sections[item_section.id] = item_section.title
            item_field: ItemField = None
            for item_field in item.fields:
                if section_names:
                    op_section_title = None
                    if item_field.section_id:
                        op_section_title = op_sections[item_field.section_id]
                        if op_section_title not in section_names:
                            continue
                if item_field.title in key_value_pairs:
                    err(f'{item_field.title} already present, check duplicates across sections in {item.title}.')
                key_value_pairs[item_field.title] = item_field.value
        out(json.dumps(key_value_pairs))


if __name__ == "__main__":
    asyncio.run(main())