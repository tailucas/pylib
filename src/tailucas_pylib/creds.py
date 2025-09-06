import asyncio

from os import getenv, environ
from typing import List

from .config import (
    APP_NAME,
    log,
    creds_use_connect_client,
    creds_use_service_client
)


OP_VAULT = getenv("OP_VAULT")
OP_CONNECT_HOST = getenv("OP_CONNECT_HOST")
OP_CONNECT_TOKEN = getenv("OP_CONNECT_TOKEN")
environ["ENV_IS_ASYNC_CLIENT"] = "true"
OP_SERVICE_ACCOUNT_TOKEN = getenv("OP_SERVICE_ACCOUNT_TOKEN")


class Creds:
    def __init__(self):
        self.connect_client = None
        self.service_client = None # type: ignore
        if OP_VAULT is None:
            raise AssertionError(f'Environment variable OP_VAULT is unset.')
        if creds_use_connect_client and OP_CONNECT_TOKEN:
            from onepasswordconnectsdk.client import (
                new_client_from_environment,
            )
            self.connect_client = new_client_from_environment()
        if creds_use_service_client and OP_SERVICE_ACCOUNT_TOKEN:
            from onepassword import Client
            self.service_client: Client = asyncio.run(Client.authenticate(
                auth=OP_SERVICE_ACCOUNT_TOKEN,
                integration_name=APP_NAME,
                integration_version="v1.0.0",
            ))
        if not self.connect_client and not self.service_client:
            raise Exception('No 1Password client created. Set {OP_CONNECT_TOKEN} or {OP_SERVICE_ACCOUNT_TOKEN}.')

    def validate_creds(self):
        global OP_VAULT
        if self.connect_client:
            from onepasswordconnectsdk.models import Vault
            get_vaults_result = self.connect_client.get_vaults()
            if asyncio.iscoroutine(get_vaults_result):
                creds_vaults: List[Vault] = asyncio.run(get_vaults_result)
            else:
                creds_vaults: List[Vault] = get_vaults_result
            vault_found = False
            for vault in creds_vaults:
                log.info(
                    f"Credential vault on 1Password server {OP_CONNECT_HOST} {vault.name} ({vault.id}) contains {vault.items} credentials."
                )
                if OP_VAULT == vault.id:
                    vault_found = True
            if len(creds_vaults) == 1:
                OP_VAULT = creds_vaults[0].id
                vault_found = True
            if not vault_found:
                raise Exception(f"No vault matching ID {OP_VAULT} found on 1Password connect server {OP_CONNECT_HOST}. See https://github.com/1Password/connect-sdk-python/")
        if self.service_client:
            from onepassword.types import VaultOverview
            vault_found = False
            vaults: List[VaultOverview] = asyncio.run(self.service_client.vaults.list())
            for vault in vaults:
                log.info(
                    f"Credential vault on 1Password service {vault.title} ({vault.id})."
                )
                if OP_VAULT == vault.id:
                    vault_found = True
            if len(vaults) == 1:
                OP_VAULT = vaults[0].id
                vault_found = True
            if not vault_found:
                raise Exception(f"No vault matching ID {OP_VAULT} found in 1Password service. See https://github.com/1Password/onepassword-sdk-python/")

    def get_creds(self, creds_path):
        if self.connect_client and creds_use_connect_client:
            from onepasswordconnectsdk.models import Item, SummaryItem, Field, Section
            from onepasswordconnectsdk.errors import FailedToRetrieveItemException
            try:
                creds_path_parts = creds_path.split('/')
                get_item_result = self.connect_client.get_item(
                    creds_path_parts[0],
                    OP_VAULT # type: ignore
                )
                if asyncio.iscoroutine(get_item_result):
                    item: Item = asyncio.run(get_item_result)
                else:
                    item: Item = get_item_result
                if len(creds_path_parts) == 1:
                    item_fields: List[Field] = item.fields # type: ignore
                    if len(item_fields) == 1:
                        return item_fields[0].value
                    else:
                        field_titles = []
                        for item_field in item_fields:
                            field_titles.append(item_field.label)
                        raise AssertionError(f'Ambiguous field specification in {creds_path}. Available: {field_titles!s}')
                elif len(creds_path_parts) == 2:
                    field_labels = dict()
                    item_fields: List[Field] = item.fields # type: ignore
                    for item_field in item_fields:
                        if not item_field.label in field_labels:
                            field_labels[item_field.label] = 1
                        else:
                            field_labels[item_field.label] += 1
                        if item_field.label == creds_path_parts[1]:
                            return item_field.value
                    raise AssertionError(f'Ambiguous field specification in {creds_path}. Available: {field_labels!s}')
                elif len(creds_path_parts) == 3:
                    item_sections: List[Section] = item.sections # type: ignore
                    section_id = None
                    for item_section in item_sections:
                        if item_section.label == creds_path_parts[1]:
                            section_id = item_section.id
                            break
                    if section_id is None:
                        raise AssertionError(f'Section {creds_path_parts[1]} not found in item {creds_path} in vault {OP_VAULT} on 1Password connect server {OP_CONNECT_HOST}.')
                    item_fields: List[Field] = item.fields # type: ignore
                    field_labels = dict()
                    for item_field in item_fields:
                        if not item_field.label in field_labels:
                            field_labels[item_field.label] = 1
                        else:
                            field_labels[item_field.label] += 1
                        if item_field.section is None:
                            continue
                        if item_field.section.id == section_id and item_field.label == creds_path_parts[2]:
                            return item_field.value
                    raise AssertionError(f'Ambiguous field specification in {creds_path}. Available: {field_labels!s}')
            except FailedToRetrieveItemException as e:
                get_items_result = self.connect_client.get_items(OP_VAULT) # type: ignore
                if asyncio.iscoroutine(get_items_result):
                    items_summary: List[SummaryItem] = asyncio.run(get_items_result)
                else:
                    items_summary: List[SummaryItem] = get_items_result
                item_titles = []
                for item_summary in items_summary:
                    item_titles.append(item_summary.title)
                raise AssertionError(f"Failed to retrieve item {creds_path} from vault {OP_VAULT} on 1Password connect server {OP_CONNECT_HOST}: {e!s} (available: {item_titles!s})")
            if item.fields:
                return item.fields
        elif self.service_client and creds_use_service_client:
            value = self.service_client.secrets.resolve(f'op://{OP_VAULT}/{creds_path}')
            if asyncio.iscoroutine(value):
                return asyncio.run(value)
            return value
        else:
            raise AssertionError(f'No credential client available for {creds_path}.')
        raise AssertionError(f'No credential retrieved for {creds_path}')

    def get_fields_from_sections(self, item_title, section_names: List[str]):
        key_value_pairs = dict()
        if self.connect_client and creds_use_connect_client:
            from onepasswordconnectsdk.models import Item, Field, Section
            get_item_result = self.connect_client.get_item(
                item_title,
                OP_VAULT # type: ignore
            )
            if asyncio.iscoroutine(get_item_result):
                item: Item = asyncio.run(get_item_result) # type: ignore
            else:
                item: Item = get_item_result # type: ignore
            item_sections: List[Section] = item.sections # type: ignore
            if item_sections is None:
                raise AssertionError(f'No sections found in item {item_title} in vault {OP_VAULT} on 1Password connect server {OP_CONNECT_HOST}.')
            section_ids = []
            for item_section in item_sections:
                if item_section.label in section_names: # type: ignore
                    section_ids.append(item_section.id)
            item_fields: List[Field] = item.fields # type: ignore
            for item_field in item_fields: # type: ignore
                if item_field.section is None: # type: ignore
                    continue
                if item_field.section.id in section_ids: # type: ignore
                    key_value_pairs[item_field.label] = item_field.value # type: ignore
            return key_value_pairs
        elif self.service_client and creds_use_service_client:
            from onepassword.types import ItemOverview, Item, ItemSection, ItemField
            items_list_result = self.service_client.items.list(OP_VAULT) # type: ignore
            if asyncio.iscoroutine(items_list_result):
                creds_items: List[ItemOverview] = asyncio.run(items_list_result)
            else:
                creds_items = items_list_result
            for cred_item in creds_items:
                item_get_result = self.service_client.items.get(OP_VAULT, cred_item.id) # type: ignore
                if asyncio.iscoroutine(item_get_result):
                    item: Item = asyncio.run(item_get_result)
                else:
                    item = item_get_result
                if item.title != item_title:
                    continue
                op_sections = dict()
                if len(item.sections) > 0:
                    item_sections: List[ItemSection] = item.sections
                    for item_section in item_sections:
                        op_sections[item_section.id] = item_section.title
                item_field: ItemField = None # type: ignore
                for item_field in item.fields:
                    if item_field.section_id is None:
                        continue
                    op_section_title = op_sections[item_field.section_id]
                    if op_section_title in section_names:
                        if item_field.title in key_value_pairs:
                            raise AssertionError(f'{item_field.title} already present, check duplicates across sections in {item.title}.')
                        key_value_pairs[item_field.title] = item_field.value
            return key_value_pairs
        else:
            raise AssertionError(f'No credential client available for {item_title}.')
